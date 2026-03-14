"""
웹페이지 스크래핑 서비스

1차: trafilatura (빠르고 정확, 정적 HTML)
2차: Scrapling Fetcher (JS 렌더링 필요 시 폴백)
"""
import logging
import re
from typing import Dict

import trafilatura

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # 초

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

    1차: trafilatura로 빠른 본문 추출 시도
    2차: 실패 시 Scrapling Fetcher로 JS 렌더링 후 재시도

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

    # 2차: Scrapling (JS 렌더링 폴백)
    logger.info("trafilatura 추출 실패, Scrapling 폴백: %s", url)
    title, content = _extract_with_scrapling(url)
    if content and len(content.strip()) > 50:
        if is_wikipedia and title:
            title = _clean_wikipedia_title(title)
        return {"title": title or url, "content": content, "url": url, "source_type": "webpage"}

    raise ValueError(f"웹페이지에서 본문을 추출할 수 없습니다: {url}")


def _extract_with_trafilatura(url: str) -> tuple:
    """trafilatura로 본문 + 제목 추출."""
    try:
        html = trafilatura.fetch_url(url)
        if not html:
            return "", ""

        content = trafilatura.extract(html, include_tables=True, include_links=False) or ""

        # 메타데이터에서 제목 추출
        meta = trafilatura.metadata.extract_metadata(html, default_url=url)
        title = meta.title if meta and meta.title else ""

        return title, content
    except Exception as e:
        logger.warning("trafilatura 실패: %s — %s", url, e)
        return "", ""


def _extract_with_scrapling(url: str) -> tuple:
    """Scrapling Fetcher로 HTML 가져온 뒤 trafilatura로 본문 추출."""
    try:
        from scrapling.fetchers import Fetcher

        page = Fetcher.get(url, timeout=_REQUEST_TIMEOUT)

        # 제목 추출
        title = ""
        og = page.css('meta[property="og:title"]')
        if og:
            title = og.attrib.get("content", "")
        if not title:
            t = page.css("title")
            if t:
                title = t.text or ""

        # 본문 추출: trafilatura에 HTML을 넘겨서 정확도 유지
        html_text = page.html_content if hasattr(page, "html_content") else str(page)
        content = trafilatura.extract(html_text, include_tables=True, include_links=False) or ""

        # trafilatura도 실패하면 직접 텍스트 추출
        if not content or len(content.strip()) < 50:
            for selector in ["article", "main", "[role='main']", ".content", "#content"]:
                el = page.css(selector)
                if el and len(el.text.strip()) > 100:
                    content = el.text.strip()
                    break
            else:
                body = page.css("body")
                content = body.text.strip() if body else ""

        return title, content
    except Exception as e:
        logger.warning("Scrapling 폴백 실패: %s — %s", url, e)
        return "", ""
