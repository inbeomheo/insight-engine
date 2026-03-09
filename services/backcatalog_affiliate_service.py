"""
백카탈로그 제휴 매칭 서비스
기존 콘텐츠 아카이브를 스캔하여 제휴 마케팅 기회를 키워드 기반으로 역매칭.
순수 파이썬, 규칙 기반 — 외부 API 호출 없음.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# 카테고리별 매칭 키워드 (소문자)
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "tech": [
        "기술", "앱", "소프트웨어", "프로그래밍", "코딩", "개발", "AI", "인공지능",
        "머신러닝", "딥러닝", "클라우드", "서버", "데이터", "API", "자동화",
        "tool", "software", "app", "tech", "developer",
    ],
    "education": [
        "강의", "학습", "교육", "튜토리얼", "온라인강의", "수업", "커리큘럼",
        "스터디", "자격증", "시험", "입문", "기초", "고급", "강좌",
        "course", "tutorial", "learning", "education",
    ],
    "lifestyle": [
        "건강", "운동", "다이어트", "피트니스", "요가", "명상", "웰빙",
        "여행", "맛집", "요리", "레시피", "취미", "생활",
        "health", "fitness", "lifestyle", "wellness",
    ],
    "finance": [
        "투자", "저축", "주식", "부동산", "재테크", "경제", "금융",
        "펀드", "ETF", "보험", "연금", "세금", "가계부", "자산",
        "finance", "investment", "stock", "crypto",
    ],
}

# 카테고리별 기본 배치 제안
_DEFAULT_PLACEMENTS: Dict[str, str] = {
    "tech": "inline_link",
    "education": "end_of_article",
    "lifestyle": "sidebar",
    "finance": "comparison_table",
}

# 모든 배치 옵션
VALID_PLACEMENTS = ["inline_link", "end_of_article", "sidebar", "comparison_table"]


@dataclass
class AffiliateMatch:
    """제휴 매칭 결과"""
    content_id: str
    content_title: str
    matched_keywords: List[str]
    affiliate_category: str
    estimated_relevance: float
    suggested_placement: str


def _normalize_text(text: str) -> str:
    """텍스트를 정규화 (소문자, 공백 정리)."""
    return " ".join(text.lower().split())


def _find_matching_keywords(text: str, category: str) -> List[str]:
    """텍스트에서 특정 카테고리의 키워드를 찾아 반환."""
    normalized = _normalize_text(text)
    keywords = CATEGORY_KEYWORDS.get(category, [])
    matched: List[str] = []

    for kw in keywords:
        if kw.lower() in normalized:
            matched.append(kw)

    return matched


def _calculate_relevance(matched_count: int, content_length: int) -> float:
    """키워드 매칭 수 / 콘텐츠 길이 비율 (0~1.0).

    콘텐츠 길이는 글자 수 기준. 최소 1로 나눔.
    """
    if matched_count <= 0:
        return 0.0
    # 비율 계산 후 0~1.0 범위로 클램핑
    # 길이가 짧을수록 매칭 밀도가 높아짐
    ratio = matched_count / max(content_length, 1)
    # 스케일링: 비율이 매우 작으므로 100을 곱하여 의미 있는 범위로 변환
    scaled = min(1.0, ratio * 100)
    return round(scaled, 4)


def scan_affiliate_opportunities(
    content_archive: List[Dict],
) -> List[AffiliateMatch]:
    """콘텐츠 아카이브에서 제휴 오퍼 매칭 기회를 스캔합니다.

    Args:
        content_archive: 콘텐츠 목록. 각 항목은 최소한 다음 필드 포함:
            - id (str): 콘텐츠 고유 ID
            - title (str): 콘텐츠 제목
            - content (str, 선택): 본문 텍스트

    Returns:
        매칭된 AffiliateMatch 목록 (매칭 없는 콘텐츠는 제외)
    """
    if not content_archive:
        return []

    matches: List[AffiliateMatch] = []

    for item in content_archive:
        content_id = str(item.get("id", ""))
        content_title = str(item.get("title", ""))
        content_body = str(item.get("content", ""))

        # 검색 대상 텍스트: 제목 + 본문
        search_text = f"{content_title} {content_body}"
        content_length = len(search_text.strip())

        if content_length == 0:
            continue

        # 모든 카테고리에 대해 키워드 매칭
        for category, _ in CATEGORY_KEYWORDS.items():
            matched_keywords = _find_matching_keywords(search_text, category)

            if not matched_keywords:
                continue

            relevance = _calculate_relevance(len(matched_keywords), content_length)
            placement = _DEFAULT_PLACEMENTS.get(category, "end_of_article")

            matches.append(
                AffiliateMatch(
                    content_id=content_id,
                    content_title=content_title,
                    matched_keywords=matched_keywords,
                    affiliate_category=category,
                    estimated_relevance=relevance,
                    suggested_placement=placement,
                )
            )

    return matches


def rank_opportunities(
    matches: List[AffiliateMatch],
) -> List[AffiliateMatch]:
    """매칭 결과를 수익 가능성(estimated_relevance) 내림차순으로 정렬합니다.

    동일 relevance인 경우 매칭 키워드 수가 많은 순서.

    Args:
        matches: AffiliateMatch 목록

    Returns:
        정렬된 AffiliateMatch 목록 (새 리스트)
    """
    if not matches:
        return []

    return sorted(
        matches,
        key=lambda m: (m.estimated_relevance, len(m.matched_keywords)),
        reverse=True,
    )
