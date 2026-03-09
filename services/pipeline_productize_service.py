"""
파이프라인 상품화 서비스 — 커스텀 파이프라인을 상품으로 패키징
"""

import uuid
from dataclasses import dataclass, field

VALID_TIERS = ("basic", "pro", "enterprise")
# 티어별 초과 사용 단가 배율
OVERAGE_MULTIPLIER = {
    "basic": 1.0,
    "pro": 0.8,
    "enterprise": 0.5,
}


@dataclass
class PipelineProduct:
    """파이프라인 상품"""
    product_id: str
    name: str
    description: str
    steps: list  # ["자막 추출", "AI 생성", "SEO 최적화"]
    price: float
    tier: str  # basic / pro / enterprise
    usage_limit: int  # 월간 사용 횟수


@dataclass
class ProductCatalog:
    """상품 카탈로그"""
    catalog_id: str
    products: list  # list[PipelineProduct]


def create_product(name: str, steps: list, price: float, tier: str,
                   description: str = "", usage_limit: int = 100) -> PipelineProduct:
    """파이프라인 상품 생성"""
    if tier not in VALID_TIERS:
        raise ValueError(f"유효하지 않은 티어: {tier}. 허용: {VALID_TIERS}")
    if price < 0:
        raise ValueError("가격은 0 이상이어야 합니다")
    if not steps:
        raise ValueError("파이프라인 단계는 최소 1개 필요합니다")

    return PipelineProduct(
        product_id=str(uuid.uuid4()),
        name=name,
        description=description or f"{name} 파이프라인 ({tier})",
        steps=steps,
        price=price,
        tier=tier,
        usage_limit=usage_limit,
    )


def list_by_tier(catalog: ProductCatalog, tier: str) -> list:
    """티어별 상품 목록"""
    return [p for p in catalog.products if p.tier == tier]


def calculate_usage_cost(product: PipelineProduct, usage_count: int) -> float:
    """초과 사용 비용 계산"""
    if usage_count <= product.usage_limit:
        return 0.0

    overage = usage_count - product.usage_limit
    # 초과 1건당 기본 가격의 1/usage_limit × 배율
    unit_price = product.price / max(product.usage_limit, 1)
    multiplier = OVERAGE_MULTIPLIER.get(product.tier, 1.0)

    return round(overage * unit_price * multiplier, 2)


def compare_products(products: list) -> dict:
    """상품 비교 매트릭스"""
    if not products:
        return {"count": 0, "products": [], "best_value": None}

    matrix = []
    for p in products:
        matrix.append({
            "name": p.name,
            "tier": p.tier,
            "price": p.price,
            "steps_count": len(p.steps),
            "usage_limit": p.usage_limit,
            "cost_per_use": round(p.price / max(p.usage_limit, 1), 2),
        })

    # 단위 사용 비용 기준 가성비 정렬
    matrix.sort(key=lambda x: x["cost_per_use"])

    return {
        "count": len(products),
        "products": matrix,
        "best_value": matrix[0]["name"] if matrix else None,
    }
