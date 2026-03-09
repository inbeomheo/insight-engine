"""
LLM 점유율 보드 서비스

AI 검색(LLM) 응답에서 브랜드 언급 빈도를 분석하여
경쟁사 대비 점유율을 비교합니다.
AI API 호출 없이 순수 규칙 기반으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 언급 매칭: 대소문자 무시, 한국어 조사 허용
# 한국어는 '삼성전자는/가/을' 등 조사가 바로 붙으므로 뒤쪽 경계를 넓게 허용
# 영어도 'Tesla가/의' 처럼 한국어 조사가 붙을 수 있음


@dataclass
class ShareBoard:
    """AI 검색 언급 비교 결과"""
    brand: str
    brand_score: float                  # 0~100
    competitors: dict                   # {name: score}
    total_responses: int
    analysis_summary: str


def _build_mention_pattern(name: str) -> re.Pattern:
    """브랜드/경쟁사 이름에 대한 언급 탐지 정규식을 생성합니다.

    대소문자 무시, 한국어/영어 모두 지원.
    한국어 조사('은/는/이/가/을/를/의/와/과' 등)가 바로 붙어도 매칭.
    """
    escaped = re.escape(name)
    # 이름 자체만 매칭 (뒤에 무엇이 오든 허용)
    return re.compile(escaped, re.IGNORECASE)


def _count_mentions(name: str, responses: list[str]) -> int:
    """응답 목록에서 특정 이름의 총 언급 횟수를 셉니다."""
    pattern = _build_mention_pattern(name)
    total = 0
    for resp in responses:
        total += len(pattern.findall(resp))
    return total


def _count_responses_with_mention(name: str, responses: list[str]) -> int:
    """해당 이름이 1회 이상 언급된 응답 개수를 셉니다."""
    pattern = _build_mention_pattern(name)
    count = 0
    for resp in responses:
        if pattern.search(resp):
            count += 1
    return count


def _calculate_score(mention_count: int, response_count: int, total_responses: int) -> float:
    """언급 점수를 계산합니다 (0~100).

    공식: (언급된 응답 비율 × 60) + (평균 언급 밀도 × 40)
    - 응답 비율: 언급이 있는 응답 / 전체 응답
    - 언급 밀도: min(총 언급수 / 전체 응답, 3) / 3  (응답당 최대 3회까지 인정)
    """
    if total_responses == 0:
        return 0.0

    # 응답 비율 (0~1)
    response_ratio = response_count / total_responses

    # 언급 밀도 (응답당 평균, 최대 3으로 캡)
    avg_mentions = mention_count / total_responses
    density = min(avg_mentions, 3.0) / 3.0

    score = (response_ratio * 60) + (density * 40)
    return round(min(score, 100.0), 1)


def _generate_summary(
    brand: str,
    brand_score: float,
    competitors: dict[str, float],
) -> str:
    """분석 요약 메시지를 생성합니다."""
    if not competitors:
        if brand_score >= 50:
            return f"'{brand}'은(는) AI 응답에서 높은 언급률을 보입니다."
        elif brand_score > 0:
            return f"'{brand}'은(는) AI 응답에서 일부 언급되고 있습니다."
        else:
            return f"'{brand}'은(는) AI 응답에서 언급되지 않았습니다."

    # 경쟁사 중 최고 점수
    max_competitor_name = max(competitors, key=competitors.get)
    max_competitor_score = competitors[max_competitor_name]

    if brand_score >= max_competitor_score and brand_score > 0:
        gap = brand_score - max_competitor_score
        return (
            f"'{brand}'이(가) 경쟁사 대비 우위에 있습니다. "
            f"최고 경쟁사 '{max_competitor_name}'보다 {gap:.1f}점 앞서 있습니다."
        )
    elif brand_score > 0 and max_competitor_score > 0:
        gap = max_competitor_score - brand_score
        return (
            f"'{brand}'이(가) '{max_competitor_name}'에 {gap:.1f}점 뒤처져 있습니다. "
            f"AI 응답 내 언급 빈도를 높일 전략이 필요합니다."
        )
    elif brand_score == 0 and max_competitor_score > 0:
        return (
            f"'{brand}'은(는) AI 응답에서 언급되지 않았으나 "
            f"'{max_competitor_name}'은(는) {max_competitor_score:.1f}점입니다. "
            f"AI 가시성 확보가 시급합니다."
        )
    else:
        return (
            f"'{brand}'과(와) 경쟁사 모두 AI 응답에서 언급되지 않았습니다. "
            f"콘텐츠 전략을 재검토하세요."
        )


def compare_llm_share(
    brand: str,
    competitors: list[str],
    responses: list[str] | None = None,
) -> ShareBoard:
    """AI 검색 언급 비교 (규칙 기반).

    Args:
        brand: 우리 브랜드명
        competitors: 경쟁사 이름 목록
        responses: AI 검색 응답 텍스트 목록. None이면 빈 결과 반환.

    Returns:
        ShareBoard 데이터클래스
    """
    if not brand or not brand.strip():
        return ShareBoard(
            brand='',
            brand_score=0.0,
            competitors={},
            total_responses=0,
            analysis_summary='브랜드명이 입력되지 않았습니다.',
        )

    brand = brand.strip()
    safe_responses = responses or []
    # 빈 문자열 필터링
    safe_responses = [r for r in safe_responses if r and r.strip()]
    total = len(safe_responses)

    # 브랜드 점수 계산
    brand_mentions = _count_mentions(brand, safe_responses)
    brand_resp_count = _count_responses_with_mention(brand, safe_responses)
    brand_score = _calculate_score(brand_mentions, brand_resp_count, total)

    # 경쟁사 점수 계산
    comp_scores: dict[str, float] = {}
    for comp in competitors:
        comp = comp.strip()
        if not comp:
            continue
        comp_mentions = _count_mentions(comp, safe_responses)
        comp_resp_count = _count_responses_with_mention(comp, safe_responses)
        comp_scores[comp] = _calculate_score(comp_mentions, comp_resp_count, total)

    # 요약 생성
    summary = _generate_summary(brand, brand_score, comp_scores)

    return ShareBoard(
        brand=brand,
        brand_score=brand_score,
        competitors=comp_scores,
        total_responses=total,
        analysis_summary=summary,
    )
