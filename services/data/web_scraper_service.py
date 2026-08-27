"""
웹페이지 스크래핑 서비스

1차: 안전하게 pre-fetch한 HTML을 trafilatura로 추출
2차: 같은 방식으로 받은 정적 HTML을 DOM 선택자로 추출
"""
import logging
import re
from typing import Dict

import trafilatura
from bs4 import BeautifulSoup

from utils.url_safety import fetch_public_url

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # 초
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_FETCH_HEADERS = {
    "User-Agent": "InsightEngine/1.0 (web ingestion)",
    "Accept": "text/html,application/xhtml+xml",
}

# Wikipedia URL 패턴
_WIKIPEDIA_RE = re.compile(r"wikipedia\.org", re.IGNORECASE)
# Wikipedia 제목 접미사 정리 패턴
_WIKI_TITLE_SUFFIX_RE = re.compile(
    r"\s*[-–—]\s*(위키백과|Wikipedia|ウィキペディア|维基百科).*$",
    re.IGNORECASE,
)


def _clean_wikipedia_title(title: str) -> str:
    """Wikipedia 제목에서 불필요한 접미사를 제거합니다."""
    return _WIKI_TITLE_SUFFIX_RE.sub("", title).strip()


def scrape_webpage(url: str) -> Dict:
    """웹페이지를 스크래핑하여 본문 텍스트를 반환합니다.

    1차: 검증된 공인 IP에서 받은 HTML을 trafilatura로 추출
    2차: 실패 시 안전하게 받은 HTML을 DOM 선택자로 추출

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "webpage"}

    Raises:
        ValueError: 본문을 추출할 수 없는 경우
    """
    is_wikipedia = bool(_WIKIPEDIA_RE.search(url))

    # 1차: trafilatura
    title, content = _extract_with_trafilatura(url)
    if content and len(content.strip()) > 50:
        if is_wikipedia and title:
            title = _clean_wikipedia_title(title)
        return {"title": title or url, "content": content, "url": url, "source_type": "webpage"}

    # 2차: 별도 브라우저 fetch 없이 제한된 정적 HTML만 DOM 파싱
    logger.info("trafilatura 추출 실패, 정적 HTML 폴백")
    title, content = _extract_with_scrapling(url)
    if content and len(content.strip()) > 50:
        if is_wikipedia and title:
            title = _clean_wikipedia_title(title)
        return {"title": title or url, "content": content, "url": url, "source_type": "webpage"}

    raise ValueError("웹페이지에서 본문을 추출할 수 없습니다.")


def _safe_fetch_html(url: str) -> bytes:
    """URL을 공인 IP에 고정하고 제한된 크기의 HTML을 가져옵니다."""
    response = fetch_public_url(
        url,
        headers=_FETCH_HEADERS,
        timeout=_REQUEST_TIMEOUT,
        max_bytes=_MAX_RESPONSE_BYTES,
        max_redirects=3,
    )
    response.raise_for_status()
    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if media_type and media_type not in {"text/html", "application/xhtml+xml"}:
        raise ValueError("HTML 응답만 스크래핑할 수 있습니다.")
    return response.content


def _extract_with_trafilatura(url: str) -> tuple:
    """안전하게 받은 HTML에서 trafilatura로 본문 + 제목을 추출합니다."""
    try:
        html = _safe_fetch_html(url)
        if not html:
            return "", ""

        content = trafilatura.extract(html, include_tables=True, include_links=False) or ""

        # 메타데이터에서 제목 추출
        meta = trafilatura.metadata.extract_metadata(html, default_url=url)
        title = meta.title if meta and meta.title else ""

        return title, content
    except Exception as e:
        logger.warning("trafilatura 추출 실패: %s", e)
        return "", ""


def _extract_with_scrapling(url: str) -> tuple:
    """호환용 이름: 안전하게 pre-fetch한 HTML을 DOM 선택자로 추출합니다.

    Scrapling Fetcher는 연결 IP를 고정할 수 없어 사용하지 않습니다.
    """
    try:
        html = _safe_fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        # 제목 추출
        title = ""
        og = soup.select_one('meta[property="og:title"]')
        if og:
            title = og.get("content", "")
        if not title:
            t = soup.select_one("title")
            if t:
                title = t.get_text(" ", strip=True)

        # 본문 추출: trafilatura에 HTML을 넘겨서 정확도 유지
        content = trafilatura.extract(html, include_tables=True, include_links=False) or ""

        # trafilatura도 실패하면 직접 텍스트 추출
        if not content or len(content.strip()) < 50:
            for selector in ["article", "main", "[role='main']", ".content", "#content"]:
                el = soup.select_one(selector)
                text = el.get_text("\n", strip=True) if el else ""
                if len(text) > 100:
                    content = text
                    break
            else:
                body = soup.select_one("body")
                content = body.get_text("\n", strip=True) if body else ""

        return title, content
    except Exception as e:
        logger.warning("정적 HTML 폴백 실패: %s", e)
        return "", ""
