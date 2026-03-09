"""
발행 속도 거버너 서비스

채널의 발행 속도, 구독자 증감, 참여율 등을 분석하여
최적의 발행 주기를 권장합니다.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 발행 속도 권장 범위 (주당 게시 수)
_MIN_RATE = 0.5   # 2주에 1회
_MAX_RATE = 14.0  # 하루 2회
_DEFAULT_RATE = 3.0  # 기본: 주 3회

# 구독자 규모별 권장 배수
_SUBSCRIBER_TIERS = [
    (100_000, 1.3),   # 10만+ → 더 자주
    (10_000, 1.1),    # 1만+ → 약간 더 자주
    (1_000, 1.0),     # 1천+ → 기본
    (0, 0.8),         # 소규모 → 덜 자주 (품질 집중)
]


@dataclass
class VelocityRecommendation:
    """발행 속도 권장 결과"""
    current_rate: float       # 현재 주당 발행 횟수
    recommended_rate: float   # 권장 주당 발행 횟수
    adjustment: str           # "increase" | "maintain" | "decrease"
    reason: str               # 한국어 설명


def _get_subscriber_multiplier(subscribers: int) -> float:
    """구독자 수에 따른 발행 속도 배수."""
    for threshold, multiplier in _SUBSCRIBER_TIERS:
        if subscribers >= threshold:
            return multiplier
    return 0.8


def _engagement_adjustment(engagement_rate: float) -> float:
    """참여율에 따른 속도 조정값.

    참여율이 높으면 현재 속도 유지/증가, 낮으면 감소 권장.
    반환값: -0.3 ~ +0.3 범위의 배수 조정값.
    """
    if engagement_rate >= 10.0:
        return 0.2   # 참여율 매우 높음 → 발행 늘려도 됨
    elif engagement_rate >= 5.0:
        return 0.1   # 양호
    elif engagement_rate >= 2.0:
        return 0.0   # 보통
    elif engagement_rate >= 1.0:
        return -0.1  # 다소 낮음
    else:
        return -0.2  # 낮음 → 줄이고 품질에 집중


def _growth_adjustment(growth_rate: float) -> float:
    """구독자 증감률에 따른 속도 조정값.

    growth_rate: 주간 구독자 증감률 (%, 양수=증가, 음수=감소)
    반환값: -0.2 ~ +0.2 범위.
    """
    if growth_rate >= 5.0:
        return 0.2   # 빠른 성장 → 모멘텀 유지
    elif growth_rate >= 1.0:
        return 0.1   # 완만한 성장
    elif growth_rate >= -1.0:
        return 0.0   # 정체
    elif growth_rate >= -5.0:
        return -0.1  # 완만한 감소
    else:
        return -0.2  # 급감 → 콘텐츠 전략 재검토


def _clamp(value: float, lo: float, hi: float) -> float:
    """값을 [lo, hi] 범위로 제한."""
    return max(lo, min(hi, value))


def _determine_adjustment(current: float, recommended: float) -> tuple[str, str]:
    """현재 vs 권장 비교하여 조정 방향과 이유 결정."""
    diff = recommended - current
    ratio = abs(diff) / max(current, 0.1)

    if ratio < 0.15:
        return "maintain", "현재 발행 속도가 적절합니다. 현재 페이스를 유지하세요."
    elif diff > 0:
        if ratio >= 0.5:
            return "increase", f"발행 빈도를 주 {recommended:.1f}회로 늘리는 것을 권장합니다. 현재 속도가 채널 규모 대비 부족합니다."
        else:
            return "increase", f"발행 빈도를 주 {recommended:.1f}회로 소폭 늘리면 도달률이 개선될 수 있습니다."
    else:
        if ratio >= 0.5:
            return "decrease", f"발행 빈도를 주 {recommended:.1f}회로 줄이고 콘텐츠 품질에 집중하세요. 현재 속도가 과도합니다."
        else:
            return "decrease", f"발행 빈도를 주 {recommended:.1f}회로 소폭 줄이면 게시물당 참여율이 개선될 수 있습니다."


def calculate_velocity(channel_stats: dict) -> VelocityRecommendation:
    """채널 발행 속도 권장값 계산.

    Args:
        channel_stats: 채널 통계 딕셔너리
            - current_rate (float): 현재 주당 발행 수 (필수)
            - subscribers (int): 구독자 수 (기본 0)
            - engagement_rate (float): 참여율 % (기본 3.0)
            - growth_rate (float): 주간 구독자 증감률 % (기본 0.0)

    Returns:
        VelocityRecommendation: 권장 발행 속도
    """
    current_rate = float(channel_stats.get("current_rate", _DEFAULT_RATE))
    subscribers = int(channel_stats.get("subscribers", 0))
    engagement_rate = float(channel_stats.get("engagement_rate", 3.0))
    growth_rate = float(channel_stats.get("growth_rate", 0.0))

    # 기본 권장값 = 현재 속도 기준
    base = current_rate if current_rate > 0 else _DEFAULT_RATE

    # 구독자 규모 배수
    sub_mult = _get_subscriber_multiplier(subscribers)

    # 참여율/성장률 조정
    eng_adj = _engagement_adjustment(engagement_rate)
    growth_adj = _growth_adjustment(growth_rate)

    # 최종 권장값
    recommended = base * sub_mult * (1 + eng_adj + growth_adj)
    recommended = round(_clamp(recommended, _MIN_RATE, _MAX_RATE), 1)

    adjustment, reason = _determine_adjustment(current_rate, recommended)

    logger.info(
        "속도 거버너: current=%.1f → recommended=%.1f (%s)",
        current_rate, recommended, adjustment,
    )

    return VelocityRecommendation(
        current_rate=round(current_rate, 1),
        recommended_rate=recommended,
        adjustment=adjustment,
        reason=reason,
    )
