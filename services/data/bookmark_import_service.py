"""
북마크 HTML 파일 파싱 서비스

Chrome/Firefox에서 내보낸 북마크 HTML 파일을 파싱하여
URL + 제목 목록을 추출합니다.
"""
from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def parse_bookmarks(html_content: str) -> List[Dict]:
    """북마크 HTML 파일을 파싱하여 URL + 제목 리스트를 추출합니다.

    Chrome/Firefox의 북마크 내보내기 형식을 지원합니다.
    (Netscape Bookmark File Format)

    Args:
        html_content: 북마크 HTML 문자열

    Returns:
        [{"url": str, "title": str}, ...]

    Raises:
        ValueError: 파싱 실패 또는 북마크가 없는 경우
    """
    if not html_content or not html_content.strip():
        raise ValueError("빈 파일입니다.")

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a')
        if not links:
            raise ValueError("북마크를 찾을 수 없습니다. Chrome 또는 Firefox에서 내보낸 HTML 파일인지 확인해주세요.")

        bookmarks = _extract_bookmark_links(links)
        if not bookmarks:
            raise ValueError("유효한 북마크 URL을 찾을 수 없습니다.")

        return bookmarks
    except Exception as e:
        logger.error("parse_bookmarks 실패: %s", e, exc_info=True)
        return []


def _extract_bookmark_links(links) -> List[Dict]:
    """BS4 링크 요소에서 유효한 HTTP 북마크만 추출합니다."""
    bookmarks = []
    seen_urls: set = set()

    for link in links:
        url = (link.get('href') or '').strip()
        if not url or not url.startswith(('http://', 'https://')):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = (link.get_text() or '').strip()
        bookmarks.append({'url': url, 'title': title or url})

    return bookmarks
