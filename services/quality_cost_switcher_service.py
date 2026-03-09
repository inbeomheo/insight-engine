"""
품질-비용 스위처 서비스.

품질과 비용 간 트레이드오프를 분석하고 최적 티어를 추천한다.
"""

from dataclasses import dataclass, field


@dataclass
class QualityTier:
    """품질 티어"""
    tier_name: str = ""
    model: str = ""
    max_tokens: int = 1000
    cost_per_1k: float = 0.0  # 1K 토큰당 비용 ($)
    quality_score: float = 0.0  # 0.0 ~ 1.0


@dataclass
class SwitchDecision:
    """전환 결정"""
    recommended_tier: str = ""
    reason: str = ""
    estimated_cost: float = 0.0
    estimated_quality: float = 0.0


def define_tiers(tier_configs: list) -> list:
    """티어 정의"""
    tiers = []
    for cfg in tier_configs:
        tier = QualityTier(
            tier_name=cfg.get("tier_name", ""),
            model=cfg.get("model", ""),
            max_tokens=cfg.get("max_tokens", 1000),
            cost_per_1k=cfg.get("cost_per_1k", 0.0),
            quality_score=cfg.get("quality_score", 0.0),
        )
        tiers.append(tier)
    return tiers


def recommend_tier(
    budget: float,
    min_quality: float,
    tiers: list
) -> SwitchDecision:
    """
    예산 내 최고 품질 추천.

    예산과 최소 품질 요건을 모두 만족하는 티어 중
    품질이 가장 높은 것을 추천한다.
    """
    if not tiers:
        return SwitchDecision(
            recommended_tier="none",
            reason="사용 가능한 티어가 없습니다",
        )

    # 1K 토큰 기준 예산 내 + 최소 품질 충족 필터
    eligible = [
        t for t in tiers
        if t.cost_per_1k <= budget and t.quality_score >= min_quality
    ]

    if not eligible:
        # 예산 내 최저 품질이라도 추천
        budget_ok = [t for t in tiers if t.cost_per_1k <= budget]
        if budget_ok:
            best = max(budget_ok, key=lambda t: t.quality_score)
            return SwitchDecision(
                recommended_tier=best.tier_name,
                reason=f"최소 품질({min_quality}) 미충족이지만 예산 내 최선",
                estimated_cost=best.cost_per_1k,
                estimated_quality=best.quality_score,
            )
        return SwitchDecision(
            recommended_tier="none",
            reason=f"예산(${budget})으로 사용 가능한 티어가 없습니다",
        )

    # 품질 최고 티어 선택
    best = max(eligible, key=lambda t: t.quality_score)
    return SwitchDecision(
        recommended_tier=best.tier_name,
        reason=f"예산 ${budget} 내 최고 품질 티어",
        estimated_cost=best.cost_per_1k,
        estimated_quality=best.quality_score,
    )


def calculate_cost(tier: QualityTier, token_count: int) -> float:
    """비용 계산"""
    if token_count <= 0:
        return 0.0
    return round(tier.cost_per_1k * (token_count / 1000), 6)


def compare_tiers(tiers: list) -> list:
    """티어 비교 매트릭스"""
    result = []
    for tier in tiers:
        # 가성비 = 품질 / 비용 (비용이 0이면 최대 가성비)
        value_ratio = (
            tier.quality_score / tier.cost_per_1k
            if tier.cost_per_1k > 0
            else float("inf")
        )

        result.append({
            "tier_name": tier.tier_name,
            "model": tier.model,
            "cost_per_1k": tier.cost_per_1k,
            "quality_score": tier.quality_score,
            "max_tokens": tier.max_tokens,
            "value_ratio": round(value_ratio, 4) if value_ratio != float("inf") else "inf",
        })

    # 가성비 내림차순 정렬
    result.sort(
        key=lambda x: x["value_ratio"] if isinstance(x["value_ratio"], (int, float)) else float("inf"),
        reverse=True,
    )
    return result
