"""
유료벽 최적화 서비스

콘텐츠 분석을 통해 유료벽(paywall) 최적 배치 위치를 추천합니다.
문단 구조, 분석 데이터(이탈률/참여도)를 기반으로 규칙 기반 추천.
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PaywallRecommendation:
    """유료벽 추천 결과"""
    position: int  # 문자 단위 위치
    paragraph_index: int  # 유료벽이 들어갈 문단 인덱스
    free_ratio: float  # 무료 공개 비율 (0.0 ~ 1.0)
    reason: str  # 추천 이유
    hook_text: str  # 유료벽 직전 문장 (궁금증 유발)


def _split_paragraphs(content: str) -> list[str]:
    """콘텐츠를 문단 단위로 분리합니다."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
    return paragraphs


def _extract_hook_text(paragraph: str) -> str:
    """문단에서 훅 텍스트를 추출합니다. 질문형 문장 우선, 없으면 마지막 문장."""
    # 구두점 포함하여 문장 분리 (구두점을 보존)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', paragraph) if s.strip()]
    if not sentences:
        return paragraph[:100] if paragraph else ""

    # 질문형 문장 우선 탐색
    for s in reversed(sentences):
        if '?' in s or '?' in s:
            return s

    # 궁금증 유발 키워드가 포함된 문장
    hook_keywords = ['비밀', '방법', '핵심', '중요', '결과', '이유', '사실', '진짜']
    for s in reversed(sentences):
        if any(kw in s for kw in hook_keywords):
            return s

    # 기본: 마지막 문장
    return sentences[-1]


def _determine_target_ratio(analytics: Optional[dict]) -> tuple[float, str]:
    """분석 데이터에 따라 목표 무료 비율을 결정합니다.

    Returns:
        (target_ratio, reason) 튜플
    """
    if analytics is None:
        return 0.4, "기본 40% 무료 공개 (분석 데이터 없음)"

    bounce_rate = analytics.get('bounce_rate', 0)
    engagement = analytics.get('engagement', 0)

    # 이탈률 높으면 → 무료 비율 낮춤 (더 앞에서 잠금)
    if bounce_rate > 0.6:
        return 0.25, f"높은 이탈률({bounce_rate:.0%}) — 조기 유료벽 (25% 공개)"

    # 참여도 높으면 → 무료 비율 높임 (더 뒤에서 잠금)
    if engagement > 0.7:
        return 0.6, f"높은 참여도({engagement:.0%}) — 후반 유료벽 (60% 공개)"

    # 중간 이탈률
    if bounce_rate > 0.4:
        return 0.3, f"보통 이탈률({bounce_rate:.0%}) — 전반 유료벽 (30% 공개)"

    # 중간 참여도
    if engagement > 0.4:
        return 0.5, f"보통 참여도({engagement:.0%}) — 중반 유료벽 (50% 공개)"

    return 0.4, "기본 40% 무료 공개"


def calculate_free_ratio(content: str, position: int) -> float:
    """지정된 위치 기준 무료 비율을 계산합니다.

    Args:
        content: 전체 콘텐츠
        position: 유료벽 위치 (문자 인덱스)

    Returns:
        0.0 ~ 1.0 사이의 무료 비율
    """
    if not content:
        return 0.0

    total_len = len(content)
    if total_len == 0:
        return 0.0

    clamped = max(0, min(position, total_len))
    return clamped / total_len


def optimize_paywall_position(
    content: str,
    analytics: Optional[dict] = None,
) -> PaywallRecommendation:
    """유료벽 최적 위치를 추천합니다.

    Args:
        content: 콘텐츠 전문
        analytics: 분석 데이터 (bounce_rate, engagement 등)

    Returns:
        PaywallRecommendation — 추천 위치 및 이유
    """
    if not content or not content.strip():
        return PaywallRecommendation(
            position=0,
            paragraph_index=0,
            free_ratio=0.0,
            reason="콘텐츠가 비어 있음",
            hook_text="",
        )

    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return PaywallRecommendation(
            position=0,
            paragraph_index=0,
            free_ratio=0.0,
            reason="문단을 분리할 수 없음",
            hook_text="",
        )

    target_ratio, reason = _determine_target_ratio(analytics)

    # 목표 비율에 가장 가까운 문단 경계를 탐색
    total_len = len(content)
    target_pos = int(total_len * target_ratio)

    # 각 문단 끝 위치 계산
    cumulative = 0
    best_idx = 0
    best_pos = 0
    best_diff = float('inf')

    for idx, para in enumerate(paragraphs):
        # 문단 끝 위치 = 이전 누적 + 현재 문단 길이
        cumulative += len(para)
        diff = abs(cumulative - target_pos)
        if diff < best_diff:
            best_diff = diff
            best_idx = idx
            best_pos = cumulative

        # 문단 사이 간격 (개행 문자들)
        cumulative += 2  # \n\n 추정

    # 유료벽 직전 문단에서 훅 텍스트 추출
    hook_paragraph = paragraphs[best_idx]
    hook_text = _extract_hook_text(hook_paragraph)

    free_ratio = calculate_free_ratio(content, best_pos)

    return PaywallRecommendation(
        position=best_pos,
        paragraph_index=best_idx,
        free_ratio=free_ratio,
        reason=reason,
        hook_text=hook_text,
    )
