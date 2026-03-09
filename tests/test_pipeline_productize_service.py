"""파이프라인 상품화 서비스 테스트"""

import unittest
from services.pipeline_productize_service import (
    PipelineProduct, ProductCatalog,
    create_product, list_by_tier, calculate_usage_cost, compare_products,
)


class TestPipelineProductizeService(unittest.TestCase):
    """파이프라인 상품화 서비스 테스트"""

    def test_create_product_basic(self):
        """기본 상품 생성"""
        p = create_product("콘텐츠 파이프라인", ["자막추출", "AI생성"], 100.0, "basic")
        self.assertEqual(p.name, "콘텐츠 파이프라인")
        self.assertEqual(p.tier, "basic")
        self.assertEqual(p.price, 100.0)
        self.assertEqual(len(p.steps), 2)

    def test_create_product_invalid_tier(self):
        """유효하지 않은 티어 거부"""
        with self.assertRaises(ValueError):
            create_product("P", ["s1"], 100, "gold")

    def test_create_product_negative_price(self):
        """음수 가격 거부"""
        with self.assertRaises(ValueError):
            create_product("P", ["s1"], -10, "basic")

    def test_create_product_empty_steps(self):
        """빈 단계 거부"""
        with self.assertRaises(ValueError):
            create_product("P", [], 100, "basic")

    def test_create_product_custom_description(self):
        """커스텀 설명"""
        p = create_product("P", ["s1"], 100, "pro", description="커스텀 설명")
        self.assertEqual(p.description, "커스텀 설명")

    def test_list_by_tier(self):
        """티어별 필터링"""
        p1 = create_product("P1", ["s1"], 100, "basic")
        p2 = create_product("P2", ["s1"], 200, "pro")
        p3 = create_product("P3", ["s1"], 300, "basic")
        catalog = ProductCatalog(catalog_id="c1", products=[p1, p2, p3])
        basic = list_by_tier(catalog, "basic")
        self.assertEqual(len(basic), 2)

    def test_list_by_tier_empty(self):
        """결과 없음"""
        catalog = ProductCatalog(catalog_id="c1", products=[])
        self.assertEqual(list_by_tier(catalog, "basic"), [])

    def test_calculate_usage_cost_within_limit(self):
        """제한 이내"""
        p = create_product("P", ["s1"], 100, "basic", usage_limit=100)
        self.assertEqual(calculate_usage_cost(p, 50), 0.0)

    def test_calculate_usage_cost_exact_limit(self):
        """정확히 제한"""
        p = create_product("P", ["s1"], 100, "basic", usage_limit=100)
        self.assertEqual(calculate_usage_cost(p, 100), 0.0)

    def test_calculate_usage_cost_overage_basic(self):
        """초과 사용 — basic 배율 1.0"""
        p = create_product("P", ["s1"], 100, "basic", usage_limit=100)
        cost = calculate_usage_cost(p, 110)
        # 초과 10건 × (100/100) × 1.0 = 10.0
        self.assertEqual(cost, 10.0)

    def test_calculate_usage_cost_overage_pro(self):
        """초과 사용 — pro 배율 0.8"""
        p = create_product("P", ["s1"], 100, "pro", usage_limit=100)
        cost = calculate_usage_cost(p, 110)
        # 초과 10건 × (100/100) × 0.8 = 8.0
        self.assertEqual(cost, 8.0)

    def test_calculate_usage_cost_overage_enterprise(self):
        """초과 사용 — enterprise 배율 0.5"""
        p = create_product("P", ["s1"], 100, "enterprise", usage_limit=100)
        cost = calculate_usage_cost(p, 110)
        # 초과 10건 × 1.0 × 0.5 = 5.0
        self.assertEqual(cost, 5.0)

    def test_compare_products(self):
        """상품 비교"""
        p1 = create_product("기본", ["s1"], 100, "basic", usage_limit=100)
        p2 = create_product("프로", ["s1", "s2"], 200, "pro", usage_limit=500)
        result = compare_products([p1, p2])
        self.assertEqual(result["count"], 2)
        # 프로가 가성비 좋음 (200/500 = 0.4 < 100/100 = 1.0)
        self.assertEqual(result["best_value"], "프로")

    def test_compare_products_empty(self):
        """빈 비교"""
        result = compare_products([])
        self.assertEqual(result["count"], 0)
        self.assertIsNone(result["best_value"])

    def test_create_product_all_tiers(self):
        """모든 티어"""
        for tier in ("basic", "pro", "enterprise"):
            p = create_product("P", ["s1"], 100, tier)
            self.assertEqual(p.tier, tier)


if __name__ == "__main__":
    unittest.main()
