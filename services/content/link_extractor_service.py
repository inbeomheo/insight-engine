"""
링크 추출 서비스

콘텐츠에서 모든 URL과 링크를 추출하고
유형별로 분류합니다. 규칙 기반 즉시 처리.
"""
import logging
import re
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_MD_LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
_MD_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_BARE_URL = re.compile(r'(?<!\()(?<!")(https?://[^\s<>\[\]()]+)')
_ANCHOR = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE)


def extract_links(content: str) -> dict:
    """콘텐츠에서 모든 링크를 추출하고 분류합니다.

    Returns:
        {
            'links': [{'url': str, 'text': str, 'type': str, 'domain': str}],
            'total': int,
            'by_type': {'external': int, 'image': int, 'anchor': int, 'bare': int},
            'domains': {domain: count},
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()
    links: List[dict] = []
    seen_urls = set()

    # 1) 이미지 링크 (먼저 추출 — MD 링크와 구분)
    for alt, url in _MD_IMAGE.findall(text):
        url = url.strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            links.append(_make_link(url, alt or '(이미지)', 'image'))

    # 2) 마크다운 링크
    for link_text, url in _MD_LINK.findall(text):
        url = url.strip()
        if url and url not in seen_urls and not url.startswith('#'):
            seen_urls.add(url)
            links.append(_make_link(url, link_text, 'external'))

    # 3) HTML 앵커 태그
    for url, anchor_text in _ANCHOR.findall(text):
        url = url.strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            links.append(_make_link(url, anchor_text or url, 'anchor'))

    # 4) 베어 URL (마크다운/HTML로 감싸지 않은 URL)
    for url in _BARE_URL.findall(text):
        url = url.rstrip('.,;:!?)')
        if url and url not in seen_urls:
            seen_urls.add(url)
            links.append(_make_link(url, url, 'bare'))

    # 유형별 카운트
    by_type = {'external': 0, 'image': 0, 'anchor': 0, 'bare': 0}
    domains: dict = {}
    for link in links:
        link_type = link['type']
        by_type[link_type] = by_type.get(link_type, 0) + 1
        domain = link['domain']
        if domain:
            domains[domain] = domains.get(domain, 0) + 1

    return {
        'links': links,
        'total': len(links),
        'by_type': by_type,
        'domains': domains,
    }


def _make_link(url: str, text: str, link_type: str) -> dict:
    """링크 객체를 생성합니다."""
    domain = ''
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or ''
    except Exception:
        pass

    return {
        'url': url,
        'text': text.strip(),
        'type': link_type,
        'domain': domain,
    }


def _empty_result() -> dict:
    return {
        'links': [],
        'total': 0,
        'by_type': {'external': 0, 'image': 0, 'anchor': 0, 'bare': 0},
        'domains': {},
    }
