"""
가격 시뮬레이터 서비스

채널 데이터와 경쟁사 정보를 기반으로 3가지 가격 시나리오를 생성합니다.
순수 규칙 기반, 외부 API 호출 없음.
"""
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PricingScenario:
    """가격 시나리오"""
    name: str  # 시나리오 이름 (starter / standard / premium)
    monthly_price: float  # 월 구독료
    annual_price: float  # 연 구독료 (할인 적용)
    features: list[str]  # 포함 기능 목록
    estimated_conversion: float  # 예상 전환율 (0.0 ~ 1.0)
    estimated_revenue: float  # 예상 월 매출


# 기본 기능 세트
_STARTER_FEATURES = [
    "기본 콘텐츠 접근",
    "월 1회 뉴스레터",
    "커뮤니티 읽기 전용",
]

_STANDARD_FEATURES = [
    "모든 콘텐츠 접근",
    "주 1회 뉴스레터",
    "커뮤니티 참여",
    "월 1회 라이브 Q&A",
    "자료 다운로드",
]

_PREMIUM_FEATURES = [
    "모든 콘텐츠 우선 접근",
    "주 2회 뉴스레터",
    "프라이빗 커뮤니티",
    "주 1회 라이브 Q&A",
    "자료 다운로드",
    "1:1 피드백",
    "얼리 액세스",
]


def _estimate_base_price(channel_data: dict) -> float:
    """채널 데이터에서 기준 월 가격을 산정합니다.

    구독자 수와 평균 조회수를 기반으로 규칙 적용.
    """
    subscribers = channel_data.get('subscriber_count', 0)
    avg_views = channel_data.get('avg_views', 0)

    # 구독자 기반 기본 가격 (로그 스케일)
    if subscribers <= 0:
        base = 5000  # 최소 기본가
    else:
        # 구독자 1000명 = 5000원, 10만명 = 15000원, 100만명 = 25000원
        base = 5000 + 5000 * math.log10(max(subscribers, 1)) / math.log10(1_000_000)

    # 조회수 기반 보정 (높은 참여 → 가격 상승 가능)
    if avg_views > 0 and subscribers > 0:
        engagement_ratio = avg_views / subscribers
        if engagement_ratio > 0.1:
            base *= 1.2  # 참여율 높으면 20% 상승
        elif engagement_ratio < 0.01:
            base *= 0.85  # 참여율 낮으면 15% 할인

    # 100원 단위 반올림
    return round(base / 100) * 100


def _adjust_for_competitors(
    base_price: float,
    competitors: Optional[list[dict]],
) -> float:
    """경쟁사 가격 대비 포지셔닝 조정.

    경쟁사 평균 대비 ±20% 범위 내로 조정합니다.
    """
    if not competitors:
        return base_price

    comp_prices = [c.get('monthly_price', 0) for c in competitors if c.get('monthly_price', 0) > 0]
    if not comp_prices:
        return base_price

    avg_comp = sum(comp_prices) / len(comp_prices)

    # 경쟁사 평균 대비 80~120% 범위로 클램핑
    lower = avg_comp * 0.8
    upper = avg_comp * 1.2
    adjusted = max(lower, min(base_price, upper))

    return round(adjusted / 100) * 100


def simulate_pricing(
    channel_data: dict,
    competitors: Optional[list[dict]] = None,
) -> list[PricingScenario]:
    """3개 가격 시나리오를 생성합니다.

    Args:
        channel_data: 채널 정보 (subscriber_count, avg_views)
        competitors: 경쟁사 정보 리스트 (monthly_price 포함)

    Returns:
        [starter, standard, premium] 3개 PricingScenario 리스트
    """
    base = _estimate_base_price(channel_data)
    base = _adjust_for_competitors(base, competitors)

    subscribers = channel_data.get('subscriber_count', 0)

    # 3단계 가격 배수
    starter_price = max(base * 0.5, 1000)  # 최소 1000원
    standard_price = base
    premium_price = base * 2.5

    # 100원 단위 정리
    starter_price = round(starter_price / 100) * 100
    standard_price = round(standard_price / 100) * 100
    premium_price = round(premium_price / 100) * 100

    # 연간 가격 (20% 할인)
    annual_discount = 0.8

    # 전환율 추정 (구독자 기반)
    if subscribers >= 100_000:
        conv_starter, conv_standard, conv_premium = 0.05, 0.02, 0.005
    elif subscribers >= 10_000:
        conv_starter, conv_standard, conv_premium = 0.04, 0.015, 0.003
    elif subscribers >= 1_000:
        conv_starter, conv_standard, conv_premium = 0.03, 0.01, 0.002
    else:
        conv_starter, conv_standard, conv_premium = 0.02, 0.008, 0.001

    scenarios = [
        PricingScenario(
            name="starter",
            monthly_price=starter_price,
            annual_price=round(starter_price * 12 * annual_discount / 100) * 100,
            features=list(_STARTER_FEATURES),
            estimated_conversion=conv_starter,
            estimated_revenue=round(subscribers * conv_starter * starter_price),
        ),
        PricingScenario(
            name="standard",
            monthly_price=standard_price,
            annual_price=round(standard_price * 12 * annual_discount / 100) * 100,
            features=list(_STANDARD_FEATURES),
            estimated_conversion=conv_standard,
            estimated_revenue=round(subscribers * conv_standard * standard_price),
        ),
        PricingScenario(
            name="premium",
            monthly_price=premium_price,
            annual_price=round(premium_price * 12 * annual_discount / 100) * 100,
            features=list(_PREMIUM_FEATURES),
            estimated_conversion=conv_premium,
            estimated_revenue=round(subscribers * conv_premium * premium_price),
        ),
    ]

    return scenarios
