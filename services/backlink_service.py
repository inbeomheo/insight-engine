"""
백링크/내부링크 자동 삽입 서비스 (SEO)

- 내부링크: Supabase ie_histories 테이블에서 과거 생성 콘텐츠를 검색하여 연관 링크 제안
- 외부링크: web_search_service를 활용하여 권위 있는 외부 소스 선별 후 콘텐츠에 삽입
"""
import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 외부링크 선별 시 우선 도메인 (도메인 권위 휴리스틱)
_HIGH_AUTHORITY_TLDS = {'.edu', '.gov', '.org'}
_HIGH_AUTHORITY_DOMAINS = {
    'github.com', 'developer.mozilla.org', 'docs.python.org',
    'arxiv.org', 'wikipedia.org', 'naver.com', 'daum.net',
    'techcrunch.com', 'wired.com', 'mit.edu', 'stanford.edu',
    'google.com', 'microsoft.com', 'aws.amazon.com', 'cloud.google.com',
    'medium.com', 'stackoverflow.com', 'dev.to',
}

# 콘텐츠에 삽입할 최대 링크 수 (내부 + 외부 합산)
MAX_TOTAL_LINKS = 5
MAX_INTERNAL_LINKS = 2
MAX_EXTERNAL_LINKS = 3


# ====================
# 내부링크 함수 (P3-7A)
# ====================

def find_internal_links(content: str, user_id: str = None) -> List[Dict[str, Any]]:
    """과거 생성 콘텐츠에서 현재 콘텐츠와 연관된 내부링크를 찾습니다.

    Args:
        content: 현재 생성된 콘텐츠 텍스트
        user_id: Supabase 사용자 ID (None이면 빈 리스트 반환)

    Returns:
        [{"title": str, "url": str, "relevance": float}] 형태의 리스트.
        Supabase 비활성 또는 오류 시 빈 리스트 반환.
    """
    if not user_id:
        return []

    try:
        from services.supabase_service import get_supabase, is_supabase_enabled
        if not is_supabase_enabled():
            return []

        supabase = get_supabase()
        if not supabase:
            return []

        # 최근 히스토리 50건 조회 (url과 title만)
        result = supabase.table('ie_histories') \
            .select('report_id, title, url') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(50) \
            .execute()

        histories = result.data or []
        if not histories:
            return []

        # 현재 콘텐츠에서 키워드 추출 (공백 기준 분리 후 2자 이상 단어만)
        content_words = set(
            w.lower() for w in re.findall(r'[가-힣a-zA-Z]{2,}', content)
        )

        # 각 히스토리 아이템과 관련도 계산
        scored = []
        for h in histories:
            title = h.get('title', '')
            youtube_url = h.get('url', '')
            if not title or not youtube_url:
                continue

            title_words = set(
                w.lower() for w in re.findall(r'[가-힣a-zA-Z]{2,}', title)
            )
            if not title_words:
                continue

            # 자카드 유사도로 관련도 계산
            intersection = content_words & title_words
            union = content_words | title_words
            relevance = len(intersection) / len(union) if union else 0.0

            if relevance > 0.05:  # 최소 관련도 임계값
                scored.append({
                    'title': title,
                    'url': youtube_url,
                    'relevance': round(relevance, 3),
                })

        # 관련도 내림차순 정렬 후 상위 MAX_INTERNAL_LINKS개 반환
        scored.sort(key=lambda x: x['relevance'], reverse=True)
        return scored[:MAX_INTERNAL_LINKS]

    except Exception as e:
        logger.warning(f"내부링크 검색 실패 (무시): {e}")
        return []


def suggest_anchor_texts(content: str, links: List[Dict]) -> List[Dict]:
    """각 링크에 대해 콘텐츠 내 최적 앵커 텍스트를 제안합니다.

    Args:
        content: 콘텐츠 텍스트
        links: find_internal_links() 반환값 (title, url, relevance 포함)

    Returns:
        각 링크에 anchor_text, position 필드가 추가된 리스트.
        앵커 텍스트를 찾지 못한 링크는 제외됩니다.
    """
    result = []
    for link in links:
        title = link.get('title', '')
        # 제목의 핵심 단어 추출 (2자 이상)
        title_words = re.findall(r'[가-힣a-zA-Z]{2,}', title)
        if not title_words:
            continue

        # 가장 긴 단어를 우선 앵커 텍스트 후보로 사용
        title_words.sort(key=len, reverse=True)
        anchor_text = None
        position = -1

        for word in title_words[:3]:  # 상위 3개 단어만 시도
            idx = content.lower().find(word.lower())
            if idx != -1:
                # 실제 콘텐츠에서의 원본 단어 추출
                anchor_text = content[idx:idx + len(word)]
                position = idx
                break

        if anchor_text and position >= 0:
            result.append({
                **link,
                'anchor_text': anchor_text,
                'position': position,
            })

    return result


# ====================
# 외부링크 함수 (P3-7B)
# ====================

def _domain_authority_score(url: str) -> float:
    """URL의 도메인 권위 점수를 반환합니다. (0.0 ~ 1.0)"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ''

        # TLD 기반 점수
        for tld in _HIGH_AUTHORITY_TLDS:
            if hostname.endswith(tld):
                return 1.0

        # 알려진 도메인 점수
        for domain in _HIGH_AUTHORITY_DOMAINS:
            if hostname == domain or hostname.endswith('.' + domain):
                return 0.9

        return 0.5  # 기본 점수

    except Exception:
        return 0.0


def find_external_links(topic: str, max_results: int = MAX_EXTERNAL_LINKS) -> List[Dict[str, Any]]:
    """웹 검색으로 주제에 맞는 권위 있는 외부 소스를 찾습니다.

    Args:
        topic: 검색할 주제 (콘텐츠 제목 또는 핵심 키워드)
        max_results: 반환할 최대 링크 수

    Returns:
        [{"title": str, "url": str, "domain": str, "relevance": float}] 리스트.
        웹 검색 비활성 또는 오류 시 빈 리스트 반환.
    """
    try:
        from services import web_search_service

        raw_results = web_search_service.search(topic, max_results=max_results * 2)
        if not raw_results:
            return []

        scored = []
        for r in raw_results:
            url = r.get('url', '')
            if not url:
                continue

            parsed = urlparse(url)
            domain = parsed.hostname or url

            # 최종 점수 = 도메인 권위 * 0.6 + 검색 관련도 * 0.4
            authority = _domain_authority_score(url)
            search_score = float(r.get('score', 0.5))
            final_score = authority * 0.6 + search_score * 0.4

            scored.append({
                'title': r.get('title', ''),
                'url': url,
                'domain': domain,
                'relevance': round(final_score, 3),
            })

        # 관련도 내림차순 정렬 후 상위 max_results 반환
        scored.sort(key=lambda x: x['relevance'], reverse=True)
        return scored[:max_results]

    except Exception as e:
        logger.warning(f"외부링크 검색 실패 (무시): {e}")
        return []


def insert_links_into_content(
    content: str,
    internal_links: List[Dict],
    external_links: List[Dict],
    max_links: int = MAX_TOTAL_LINKS,
) -> str:
    """내부/외부 링크를 콘텐츠의 적절한 위치에 마크다운 링크로 삽입합니다.

    - 기존 마크다운 링크나 코드 블록은 건드리지 않습니다.
    - 내부링크 최대 2개, 외부링크 최대 3개 (합산 max_links 이하)
    - 콘텐츠 수정은 단어 경계에서만 수행합니다.

    Args:
        content: 원본 콘텐츠 텍스트 (마크다운)
        internal_links: find_internal_links() 반환값
        external_links: find_external_links() 반환값
        max_links: 삽입할 최대 링크 총 수

    Returns:
        링크가 삽입된 콘텐츠 문자열.
    """
    if not internal_links and not external_links:
        return content

    # 코드 블록 범위 추적 (코드 블록 내부는 수정하지 않음)
    code_block_ranges = _find_code_block_ranges(content)

    # 삽입할 링크 목록 구성 (내부 2개 + 외부 3개 순서로)
    links_to_insert = []
    for link in internal_links[:MAX_INTERNAL_LINKS]:
        links_to_insert.append({
            'url': link['url'],
            'anchor_hint': link.get('anchor_text') or _extract_key_phrase(link.get('title', '')),
            'type': 'internal',
        })

    remaining = max_links - len(links_to_insert)
    for link in external_links[:min(MAX_EXTERNAL_LINKS, remaining)]:
        links_to_insert.append({
            'url': link['url'],
            'anchor_hint': _extract_key_phrase(link.get('title', '')),
            'type': 'external',
        })

    if not links_to_insert:
        return content

    modified = content
    inserted_count = 0

    for link_info in links_to_insert:
        if inserted_count >= max_links:
            break

        anchor_hint = link_info.get('anchor_hint', '')
        url = link_info['url']

        if not anchor_hint or not url:
            continue

        # 콘텐츠에서 앵커 텍스트 위치 탐색
        pattern = re.escape(anchor_hint)
        match = re.search(pattern, modified, flags=re.IGNORECASE)
        if not match:
            continue

        start, end = match.start(), match.end()

        # 코드 블록 내부면 건너뜀
        if _is_in_code_block(start, code_block_ranges):
            continue

        # 이미 링크로 감싸진 위치면 건너뜀
        if _is_already_linked(modified, start, end):
            continue

        original_text = modified[start:end]
        markdown_link = f'[{original_text}]({url})'
        modified = modified[:start] + markdown_link + modified[end:]

        # 삽입 후 코드 블록 범위 오프셋 재계산
        offset_diff = len(markdown_link) - len(original_text)
        code_block_ranges = [
            (s + offset_diff if s > start else s, e + offset_diff if e > start else e)
            for s, e in code_block_ranges
        ]

        inserted_count += 1
        logger.debug(f"링크 삽입: [{original_text}]({url})")

    return modified


# ====================
# 유틸리티 함수
# ====================

def _find_code_block_ranges(content: str) -> List[tuple]:
    """마크다운 코드 블록(``` ... ```)의 시작/끝 위치를 반환합니다."""
    ranges = []
    for match in re.finditer(r'```[\s\S]*?```', content):
        ranges.append((match.start(), match.end()))
    return ranges


def _is_in_code_block(pos: int, ranges: List[tuple]) -> bool:
    """주어진 위치가 코드 블록 범위 안에 있는지 확인합니다."""
    return any(start <= pos < end for start, end in ranges)


def _is_already_linked(content: str, start: int, end: int) -> bool:
    """해당 위치의 텍스트가 이미 마크다운 링크로 감싸져 있는지 확인합니다.

    [text](url) 형식에서 text 위치인지 체크합니다.
    """
    # 텍스트 앞에 '[', 뒤에 '](' 패턴이 있으면 이미 링크
    if start > 0 and content[start - 1] == '[':
        after = content[end:end + 2]
        if after.startswith(']('):
            return True
    return False


def _extract_key_phrase(title: str) -> str:
    """제목에서 핵심 키워드 구(2단어 이하)를 추출합니다."""
    if not title:
        return ''

    # 괄호/특수문자 제거
    clean = re.sub(r'[^\w\s가-힣]', ' ', title).strip()
    words = [w for w in clean.split() if len(w) >= 2]

    if not words:
        return ''

    # 가장 긴 단어 반환 (핵심 용어일 가능성 높음)
    words.sort(key=len, reverse=True)
    return words[0]
