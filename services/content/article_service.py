"""일반 웹 아티클 추출 서비스."""
from __future__ import annotations

import logging
import http.client
import re
import socket
import ssl
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from services.core import content_service
from utils.url_safety import (
    ResolvedPublicURL,
    UnsafeURLError,
    is_safe_public_url,
    resolve_public_url,
)

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
        title, text = _extract_article(html, final_url)
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
            "extraction": "article_or_largest_p_cluster",
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


def _connect_to_ip(target: ResolvedPublicURL, timeout: float) -> socket.socket:
    """검증된 IP에 직접 연결해 URL 검사 후 DNS 재해석을 막습니다."""
    family = socket.AF_INET6 if ':' in target.ip else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    destination = (
        (target.ip, target.port, 0, 0)
        if family == socket.AF_INET6
        else (target.ip, target.port)
    )
    try:
        sock.connect(destination)
        return sock
    except Exception:
        sock.close()
        raise


def _get_from_resolved_url(
    target: ResolvedPublicURL,
    headers: dict[str, str],
    timeout: tuple[int, int],
) -> requests.Response:
    """고정 IP로 GET하되 원래 Host/SNI/인증서 검증을 유지합니다."""
    connect_timeout, read_timeout = timeout
    sock = _connect_to_ip(target, connect_timeout)
    connection = http.client.HTTPConnection(
        target.hostname,
        target.port,
        timeout=read_timeout,
    )
    try:
        if target.scheme == 'https':
            context = ssl.create_default_context(cafile=requests.certs.where())
            sock = context.wrap_socket(sock, server_hostname=target.hostname)
        sock.settimeout(read_timeout)
        connection.sock = sock
        connection.request(
            'GET',
            target.request_target,
            headers={
                **headers,
                'Host': target.host_header,
                'Connection': 'close',
            },
        )
        raw_response = connection.getresponse()
        response = requests.Response()
        response.status_code = raw_response.status
        response.reason = raw_response.reason
        response.url = (
            f'{target.scheme}://{target.host_header}{target.request_target}'
        )
        response.headers = requests.structures.CaseInsensitiveDict(
            raw_response.getheaders()
        )
        content_length = response.headers.get('Content-Length')
        is_redirect = 300 <= response.status_code < 400
        if is_redirect or (
            content_length
            and content_length.isdigit()
            and int(content_length) > MAX_ARTICLE_BYTES
        ):
            response._content = b''
        else:
            # 상한보다 한 바이트 더 읽어 스트리밍 길이 초과도 탐지합니다.
            response._content = raw_response.read(MAX_ARTICLE_BYTES + 1)
        # raw가 없는 합성 requests.Response이므로 이미 본문을 모두 읽었다고
        # 표시해야 iter_content()가 raw.stream을 호출하지 않습니다.
        response._content_consumed = True
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        return response
    finally:
        connection.close()
        sock.close()


def _fetch_html(url: str) -> tuple[bytes, str]:
    """리다이렉트마다 URL 안전성과 최종 HTML 타입을 검증해 바이트 본문을 반환합니다."""
    current_url = url
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    for _ in range(_MAX_REDIRECTS + 1):
        try:
            target = resolve_public_url(current_url)
        except UnsafeURLError as exc:
            raise ValueError(
                "[아티클 추출 실패] 안전하지 않은 URL은 가져올 수 없습니다."
            ) from exc
        try:
            response = _get_from_resolved_url(target, headers, REQUEST_TIMEOUT)
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise requests.RequestException('article request failed') from exc
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
            declared_length = int(content_length)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "[아티클 추출 실패] Content-Length가 올바르지 않습니다."
            ) from exc
        if declared_length < 0:
            raise ValueError(
                "[아티클 추출 실패] Content-Length가 올바르지 않습니다."
            )
        if declared_length > MAX_ARTICLE_BYTES:
            raise ValueError("[아티클 추출 실패] 페이지가 너무 큽니다.")

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


def _extract_article(html: bytes, url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)

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

    return title or url, text


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
