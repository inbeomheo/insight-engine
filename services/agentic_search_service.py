"""에이전트형 검색 서비스

질의를 분해하고 다단계 검색을 시뮬레이션합니다.
의도 분류, 쿼리 분해, 결과 랭킹, 병합 기능을 제공합니다.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    """검색 질의"""
    query_id: str                       # 질의 고유 ID
    original_query: str                 # 원본 질의
    sub_queries: list[str] = field(default_factory=list)  # 분해된 하위 질의
    intent: str = 'factual'             # factual / exploratory / comparative


@dataclass
class SearchResult:
    """검색 결과"""
    result_id: str                      # 결과 고유 ID
    query_id: str                       # 연관 질의 ID
    title: str                          # 결과 제목
    snippet: str                        # 결과 스니펫
    relevance: float = 0.0             # 관련성 점수 (0~1)
    source: str = ''                    # 출처


# ── 의도 분류 키워드 패턴 ────────────────────────────────────
_COMPARATIVE_KEYWORDS = [
    '비교', '차이', '대비', 'vs', 'versus', '어느', '뭐가 더', '어떤 것이',
    '보다', '장단점', '비해', '대조',
]

_FACTUAL_KEYWORDS = [
    '무엇', '뭐', '어떻게', '얼마', '언제', '어디', '누구',
    'what', 'how', 'when', 'where', 'who', 'which',
    '정의', '의미', '방법', '개념',
]

_EXPLORATORY_KEYWORDS = [
    '왜', 'why', '이유', '원인', '배경', '영향', '전망', '미래',
    '가능성', '추세', '경향', '의견',
]

# ── 쿼리 분해용 접속사/구분자 ────────────────────────────────
_SPLIT_PATTERN = re.compile(r'[,，]|\s+(?:그리고|및|또는|and|or|와|과)\s+')


def classify_intent(query: str) -> str:
    """질의 의도 분류

    Args:
        query: 검색 질의 문자열

    Returns:
        'factual' | 'exploratory' | 'comparative'
    """
    if not query or not query.strip():
        return 'factual'

    q_lower = query.lower().strip()

    # 비교 키워드 우선 (가장 구체적)
    for kw in _COMPARATIVE_KEYWORDS:
        if kw in q_lower:
            return 'comparative'

    # 탐색형 키워드
    for kw in _EXPLORATORY_KEYWORDS:
        if kw in q_lower:
            return 'exploratory'

    # 사실형 키워드 (또는 기본값)
    return 'factual'


def decompose_query(query: str) -> SearchQuery:
    """질의 분해

    접속사/쉼표 기준으로 하위 질의를 분해하고 의도를 분류합니다.

    Args:
        query: 원본 질의

    Returns:
        분해된 SearchQuery
    """
    query_id = uuid.uuid4().hex[:8]

    if not query or not query.strip():
        return SearchQuery(
            query_id=query_id,
            original_query=query or '',
            sub_queries=[],
            intent='factual',
        )

    intent = classify_intent(query)

    # 접속사/쉼표 기준 분해
    parts = _SPLIT_PATTERN.split(query.strip())
    sub_queries = [p.strip() for p in parts if p.strip()]

    # 분해 결과가 원본과 동일하면 핵심 키워드 추출
    if len(sub_queries) <= 1:
        sub_queries = _extract_key_phrases(query.strip())

    return SearchQuery(
        query_id=query_id,
        original_query=query.strip(),
        sub_queries=sub_queries,
        intent=intent,
    )


def _extract_key_phrases(query: str) -> list[str]:
    """핵심 키워드 추출 (질의를 구문으로 분리)"""
    # 조사/접속사 제거 후 의미 단위 추출
    # 물음표/마침표 제거
    cleaned = re.sub(r'[?？.。!！]', '', query).strip()
    if not cleaned:
        return [query]

    # 공백으로 분리된 토큰 중 2자 이상인 것
    tokens = cleaned.split()
    phrases = [t for t in tokens if len(t) >= 2]

    # 너무 적으면 원본 반환
    if len(phrases) < 1:
        return [query]

    return phrases


def rank_results(results: list[SearchResult]) -> list[SearchResult]:
    """검색 결과를 관련성 기반으로 정렬

    Args:
        results: 검색 결과 목록

    Returns:
        관련성 내림차순 정렬된 결과
    """
    return sorted(results, key=lambda r: r.relevance, reverse=True)


def merge_results(
    result_groups: list[list[SearchResult]],
) -> list[SearchResult]:
    """다중 검색 결과 병합

    중복 제거 (title 기준) 후 관련성 순 정렬합니다.

    Args:
        result_groups: 검색 결과 그룹 목록

    Returns:
        병합된 검색 결과 (중복 제거, 관련성 순)
    """
    seen_titles: set[str] = set()
    merged: list[SearchResult] = []

    for group in result_groups:
        for result in group:
            # 제목 기준 중복 제거 (소문자 정규화)
            title_key = result.title.strip().lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            merged.append(result)

    return rank_results(merged)
