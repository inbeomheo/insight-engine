"""일반 웹 아티클 추출 서비스."""
from __future__ import annotations

import logging
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from services.core import content_service
from utils.url_safety import is_safe_public_url

logger = logging.getLogger(__name__)

MAX_ARTICLE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT = (5, 15)
USER_AGENT = (
    "InsightEngine/1.0 (+https://insight-engine.local; article ingestion)"
)
_CHUNK_SIZE = 64 * 1024
_MAX_REDIRECTS = 3
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_BLOCK_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "iframe",
    "svg",
)


def fetch_article(url: str) -> dict[str, Any]:
    """URL에서 제목과 본문을 추출합니다."""
    safe_url = _validate_article_url(url)

    try:
        html, final_url = _fetch_html(safe_url)
        title, text, extraction = _extract_article(html, final_url)
    except ValueError:
        raise
    except requests.RequestException as exc:
        logger.warning("아티클 요청 실패: %s", exc)
        raise ValueError("[아티클 추출 실패] 페이지를 가져올 수 없습니다.") from exc
    except Exception as exc:
        logger.warning("아티클 추출 실패: %s", exc, exc_info=True)
        raise ValueError("[아티클 추출 실패] 본문을 추출할 수 없습니다.") from exc

    if not text.strip():
        raise ValueError("[아티클 추출 실패] 본문을 찾을 수 없습니다.")

    return {
        "title": title or final_url,
        "text": text,
        "source_meta": {
            "source_type": "article",
            "url": final_url,
            "bytes": len(html),
            "extraction": extraction,
        },
    }


def _validate_article_url(url: str) -> str:
    """SSRF 방어 및 아티클 URL 형식 검증."""
    clean_url = (url or "").strip()
    parsed = urlparse(clean_url)
    hostname = (parsed.hostname or "").lower().rstrip(".")

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("[아티클 추출 실패] http 또는 https URL만 지원합니다.")
    if _is_youtube_host(hostname) or content_service.is_youtube_url(clean_url):
        raise ValueError("[아티클 추출 실패] YouTube URL은 영상 경로로 처리해주세요.")
    if not is_safe_public_url(clean_url):
        raise ValueError("[아티클 추출 실패] 안전하지 않은 URL은 가져올 수 없습니다.")

    return clean_url


def _is_youtube_host(hostname: str) -> bool:
    return hostname in _YOUTUBE_HOSTS or hostname.endswith(".youtube.com")


def _fetch_html(url: str) -> tuple[bytes, str]:
    """리다이렉트마다 URL 안전성과 최종 HTML 타입을 검증해 바이트 본문을 반환합니다."""
    current_url = url
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    for _ in range(_MAX_REDIRECTS + 1):
        response = requests.get(
            current_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=False,
        )
        try:
            status_code = getattr(response, "status_code", 200)
            if status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location:
                    break
                current_url = _validate_article_url(urljoin(current_url, location))
                continue

            response.raise_for_status()
            _validate_html_content_type(response.headers.get("Content-Type", ""))
            return _read_limited_response(response), current_url
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

    raise ValueError("[아티클 추출 실패] 리다이렉트가 너무 많습니다.")


def _validate_html_content_type(content_type: str) -> None:
    """최종 응답이 HTML 문서인지 검증합니다."""
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if not (
        media_type.startswith("text/html")
        or media_type.startswith("application/xhtml+xml")
    ):
        raise ValueError("[아티클 추출 실패] HTML 문서만 가져올 수 있습니다.")


def _read_limited_response(response) -> bytes:
    """응답 본문을 최대 2MB까지만 바이트로 읽습니다."""
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_ARTICLE_BYTES:
                raise ValueError("[아티클 추출 실패] 페이지가 너무 큽니다.")
        except (TypeError, ValueError) as exc:
            if str(exc).startswith("[아티클 추출 실패]"):
                raise

    chunks: list[bytes] = []
    total = 0
    iterator = response.iter_content(chunk_size=_CHUNK_SIZE)
    for chunk in iterator:
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_ARTICLE_BYTES:
            raise ValueError("[아티클 추출 실패] 페이지가 너무 큽니다.")
        chunks.append(chunk)

    return b"".join(chunks)


def _extract_article(html: bytes, url: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)

    structured_text = _extract_structured_item_list(soup)
    if structured_text:
        structured_title = title or url
        return structured_title, structured_text, "json_ld_item_list"

    for tag in soup(_BLOCK_TAGS):
        tag.decompose()

    article_nodes = soup.find_all("article")
    if article_nodes:
        node = max(article_nodes, key=lambda item: len(_node_text(item)))
        text = _node_text(node)
    else:
        text = _largest_paragraph_cluster(soup)

    text = _clean_text(text)
    if len(text) < 50:
        raise ValueError("[아티클 추출 실패] 본문을 충분히 추출하지 못했습니다.")

    return title or url, text, "article_or_largest_p_cluster"


def _json_type_matches(value: Any, expected: str) -> bool:
    raw_type = value.get("@type") if isinstance(value, dict) else None
    if isinstance(raw_type, list):
        return expected in raw_type
    return raw_type == expected


def _iter_json_ld_objects(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _iter_json_ld_objects(item)
        return

    if not isinstance(value, dict):
        return

    yield value
    graph = value.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            yield from _iter_json_ld_objects(item)


def _clean_json_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_clean_json_scalar(item) for item in value if _clean_json_scalar(item))
    if isinstance(value, dict):
        return _clean_json_scalar(value.get("name") or value.get("url") or value.get("@id"))
    return _clean_text(str(value))


def _extract_structured_item_list(soup: BeautifulSoup) -> str:
    """Extract useful lists from JSON-LD before falling back to paragraph text.

    Sites like Trendshift render the visible ranking from Next.js data and expose
    the same repository list as schema.org ItemList JSON-LD. Paragraph-only
    extraction sees just a marketing card, so preserve structured list entries
    for the LLM instead.
    """
    for script in soup.find_all("script"):
        script_type_value = script.get("type") or ""
        script_type = " ".join(script_type_value) if isinstance(script_type_value, list) else str(script_type_value)
        if "ld+json" not in script_type.lower():
            continue

        raw = script.string or script.get_text("", strip=False)
        if not raw or not raw.strip():
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for obj in _iter_json_ld_objects(parsed):
            if not _json_type_matches(obj, "ItemList"):
                continue
            text = _format_item_list(obj)
            if text:
                return text

    return ""


def _format_item_list(item_list: dict[str, Any]) -> str:
    elements = item_list.get("itemListElement")
    if not isinstance(elements, list) or not elements:
        return ""

    title = _clean_json_scalar(item_list.get("name"))
    description = _clean_json_scalar(item_list.get("description"))
    source_url = _clean_json_scalar(item_list.get("url"))

    lines: list[str] = []
    if title:
        lines.append(title)
    if description:
        lines.append(description)
    if source_url:
        lines.append(f"Source: {source_url}")
    if lines:
        lines.append("")

    item_count = 0
    for raw_entry in elements[:50]:
        if not isinstance(raw_entry, dict):
            continue
        item = raw_entry.get("item") if isinstance(raw_entry.get("item"), dict) else raw_entry
        if not isinstance(item, dict):
            continue

        name = _clean_json_scalar(item.get("name"))
        description = _clean_json_scalar(item.get("description"))
        if not name and not description:
            continue

        position = raw_entry.get("position") or item.get("position") or item_count + 1
        language = _clean_json_scalar(item.get("programmingLanguage"))
        repo_url = _clean_json_scalar(item.get("codeRepository") or item.get("url"))
        keywords = _clean_json_scalar(item.get("keywords"))

        detail_parts = []
        if language:
            detail_parts.append(f"language: {language}")
        if repo_url:
            detail_parts.append(f"repo: {repo_url}")
        if keywords:
            detail_parts.append(f"tags: {keywords}")

        line = f"{position}. {name}"
        if description:
            line += f" — {description}"
        if detail_parts:
            line += f" ({'; '.join(detail_parts)})"
        lines.append(line)
        item_count += 1

    if item_count < 2:
        return ""
    return "\n".join(lines).strip()


def _extract_title(soup: BeautifulSoup) -> str:
    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
    ):
        tag = soup.find("meta", attrs=attrs)
        content = tag.get("content") if tag else ""
        if content:
            return _clean_text(content)

    h1 = soup.find("h1")
    if h1:
        h1_text = _clean_text(h1.get_text(" ", strip=True))
        if h1_text:
            return h1_text

    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)
    return ""


def _largest_paragraph_cluster(soup: BeautifulSoup) -> str:
    clusters: dict[int, list[str]] = {}
    for paragraph in soup.find_all("p"):
        text = _clean_text(paragraph.get_text(" ", strip=True))
        if len(text) < 20:
            continue
        parent = paragraph.find_parent(["main", "section", "div", "body"])
        key = id(parent or paragraph.parent or paragraph)
        clusters.setdefault(key, []).append(text)

    if not clusters:
        body = soup.find("body") or soup
        return _node_text(body)

    best = max(clusters.values(), key=lambda parts: sum(len(part) for part in parts))
    return "\n\n".join(best)


def _node_text(node) -> str:
    paragraphs = []
    for paragraph in node.find_all("p"):
        text = _clean_text(paragraph.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)
    if paragraphs:
        return "\n\n".join(paragraphs)
    return _clean_text(node.get_text("\n", strip=True))


def _clean_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text or "")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
