"""
사이트 크롤링 시뮬레이션 서비스.

주어진 base_url을 기준으로 동일 도메인 내 페이지를 BFS 방식으로
수집하는 기능을 제공한다. 실제 HTTP 호출 없이 규칙 기반으로 동작하며,
외부에서 HTML 콘텐츠를 주입하여 테스트할 수 있다.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse, urldefrag


@dataclass
class PageContent:
    """수집된 페이지 정보."""
    url: str
    title: str
    content: str
    links: list[str] = field(default_factory=list)
    depth: int = 0
    crawled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CrawlResult:
    """크롤링 결과 요약."""
    pages: list[PageContent] = field(default_factory=list)
    total_pages: int = 0
    max_depth_reached: int = 0
    errors: list[str] = field(default_factory=list)


# ── robots.txt 시뮬레이션 ─────────────────────────────────

# 일반적으로 차단되는 경로 패턴
_DEFAULT_DISALLOWED = [
    '/admin',
    '/login',
    '/logout',
    '/api/',
    '/private/',
    '/tmp/',
    '/.env',
    '/wp-admin',
    '/cgi-bin/',
]

_LINK_RE = re.compile(
    r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

_TITLE_RE = re.compile(
    r'<title[^>]*>\s*(.+?)\s*</title>',
    re.IGNORECASE | re.DOTALL,
)


def normalize_url(url: str) -> str:
    """URL 정규화: fragment 제거, trailing slash 통일."""
    url, _ = urldefrag(url)  # fragment 제거
    parsed = urlparse(url)
    # 경로가 비어있으면 / 추가
    path = parsed.path or '/'
    # trailing slash 제거 (루트 제외)
    if len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')
    normalized = parsed._replace(path=path, fragment='')
    return normalized.geturl()


def is_same_domain(url: str, base_url: str) -> bool:
    """두 URL이 같은 도메인인지 판별."""
    return urlparse(url).netloc == urlparse(base_url).netloc


def is_allowed_by_robots(url: str, disallowed_paths: Optional[list[str]] = None) -> bool:
    """
    robots.txt 규칙 시뮬레이션.

    disallowed_paths에 포함된 접두사로 시작하는 경로는 차단.
    """
    paths = disallowed_paths if disallowed_paths is not None else _DEFAULT_DISALLOWED
    parsed_path = urlparse(url).path.lower()
    for blocked in paths:
        if parsed_path.startswith(blocked.lower()):
            return False
    return True


def extract_links(html_content: str, base_url: str) -> list[str]:
    """
    HTML에서 <a href="..."> 링크를 추출하고 절대 URL로 변환한다.

    Args:
        html_content: HTML 문자열.
        base_url: 상대 경로 해석 기준 URL.

    Returns:
        정규화된 절대 URL 리스트 (중복 제거, 순서 보존).
    """
    if not html_content:
        return []

    raw_hrefs = _LINK_RE.findall(html_content)
    seen: set[str] = set()
    result: list[str] = []

    for href in raw_hrefs:
        href = href.strip()
        # javascript:, mailto:, tel: 등 무시
        if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue

        absolute = urljoin(base_url, href)
        normalized = normalize_url(absolute)

        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def _extract_title(html_content: str) -> str:
    """HTML에서 <title> 태그 내용 추출."""
    match = _TITLE_RE.search(html_content)
    return match.group(1).strip() if match else ''


def crawl_site(
    base_url: str,
    max_pages: int = 100,
    max_depth: int = 3,
    disallowed_paths: Optional[list[str]] = None,
    fetch_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> CrawlResult:
    """
    사이트를 BFS로 크롤링한다.

    Args:
        base_url: 시작 URL.
        max_pages: 최대 수집 페이지 수.
        max_depth: 최대 탐색 깊이.
        disallowed_paths: 차단할 경로 접두사 리스트 (None이면 기본값 사용).
        fetch_fn: URL → HTML 문자열을 반환하는 함수.
                  None이면 빈 HTML을 반환 (시뮬레이션 모드).

    Returns:
        CrawlResult — 수집 결과.
    """
    if not base_url or not base_url.strip():
        return CrawlResult(errors=['빈 URL이 전달되었습니다.'])

    base_url = normalize_url(base_url.strip())
    result = CrawlResult()

    visited: set[str] = set()
    # BFS 큐: (url, depth)
    queue: list[tuple[str, int]] = [(base_url, 0)]

    while queue and len(result.pages) < max_pages:
        current_url, depth = queue.pop(0)

        if current_url in visited:
            continue
        if depth > max_depth:
            continue
        if not is_same_domain(current_url, base_url):
            continue
        if not is_allowed_by_robots(current_url, disallowed_paths):
            result.errors.append(f'robots.txt 차단: {current_url}')
            visited.add(current_url)
            continue

        visited.add(current_url)

        # HTML 가져오기
        html = None
        if fetch_fn is not None:
            try:
                html = fetch_fn(current_url)
            except Exception as e:
                result.errors.append(f'페이지 수집 실패 ({current_url}): {str(e)}')
                continue

        if html is None:
            html = ''

        # 페이지 정보 추출
        title = _extract_title(html)
        links = extract_links(html, current_url)
        same_domain_links = [l for l in links if is_same_domain(l, base_url)]

        page = PageContent(
            url=current_url,
            title=title,
            content=html,
            links=same_domain_links,
            depth=depth,
        )
        result.pages.append(page)
        result.max_depth_reached = max(result.max_depth_reached, depth)

        # 자식 링크를 큐에 추가
        for link in same_domain_links:
            if link not in visited:
                queue.append((link, depth + 1))

    result.total_pages = len(result.pages)
    return result
