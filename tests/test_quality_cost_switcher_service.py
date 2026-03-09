"""품질-비용 스위처 서비스 테스트"""

import unittest

from services.quality_cost_switcher_service import (
    QualityTier,
    SwitchDecision,
    define_tiers,
    recommend_tier,
    calculate_cost,
    compare_tiers,
)


class TestDefineTiers(unittest.TestCase):
    """define_tiers 함수 테스트"""

    def test_티어_정의(self):
        configs = [
            {"tier_name": "basic", "model": "gpt-3.5", "cost_per_1k": 0.001, "quality_score": 0.6},
            {"tier_name": "premium", "model": "gpt-4", "cost_per_1k": 0.03, "quality_score": 0.95},
        ]
        tiers = define_tiers(configs)
        self.assertEqual(len(tiers), 2)
        self.assertEqual(tiers[0].tier_name, "basic")

    def test_빈_설정(self):
        tiers = define_tiers([])
        self.assertEqual(len(tiers), 0)


class TestRecommendTier(unittest.TestCase):
    """recommend_tier 함수 테스트"""

    def setUp(self):
        self.tiers = [
            QualityTier(tier_name="economy", model="small", cost_per_1k=0.001, quality_score=0.5),
            QualityTier(tier_name="standard", model="medium", cost_per_1k=0.01, quality_score=0.7),
            QualityTier(tier_name="premium", model="large", cost_per_1k=0.05, quality_score=0.95),
        ]

    def test_예산_내_최고_품질(self):
        decision = recommend_tier(0.05, 0.5, self.tiers)
        self.assertEqual(decision.recommended_tier, "premium")

    def test_낮은_예산(self):
        decision = recommend_tier(0.001, 0.3, self.tiers)
        self.assertEqual(decision.recommended_tier, "economy")

    def test_높은_최소_품질_필터(self):
        decision = recommend_tier(0.05, 0.9, self.tiers)
        self.assertEqual(decision.recommended_tier, "premium")

    def test_예산_부족(self):
        decision = recommend_tier(0.0001, 0.5, self.tiers)
        self.assertEqual(decision.recommended_tier, "none")

    def test_품질_미충족_예산_내_최선(self):
        decision = recommend_tier(0.001, 0.9, self.tiers)
        self.assertEqual(decision.recommended_tier, "economy")
        self.assertIn("미충족", decision.reason)

    def test_빈_티어(self):
        decision = recommend_tier(1.0, 0.5, [])
        self.assertEqual(decision.recommended_tier, "none")

    def test_여러_적격_티어_중_최고(self):
        decision = recommend_tier(0.01, 0.3, self.tiers)
        self.assertEqual(decision.recommended_tier, "standard")  # 0.01 예산 내 최고 품질


class TestCalculateCost(unittest.TestCase):
    """calculate_cost 함수 테스트"""

    def test_정상_비용_계산(self):
        tier = QualityTier(cost_per_1k=0.01)
        cost = calculate_cost(tier, 5000)
        self.assertAlmostEqual(cost, 0.05)

    def test_0_토큰(self):
        tier = QualityTier(cost_per_1k=0.01)
        cost = calculate_cost(tier, 0)
        self.assertEqual(cost, 0.0)

    def test_음수_토큰(self):
        tier = QualityTier(cost_per_1k=0.01)
        cost = calculate_cost(tier, -100)
        self.assertEqual(cost, 0.0)


class TestCompareTiers(unittest.TestCase):
    """compare_tiers 함수 테스트"""

    def test_가성비_정렬(self):
        tiers = [
            QualityTier(tier_name="expensive", cost_per_1k=0.1, quality_score=0.5),
            QualityTier(tier_name="cheap", cost_per_1k=0.001, quality_score=0.6),
        ]
        result = compare_tiers(tiers)
        self.assertEqual(result[0]["tier_name"], "cheap")  # 가성비 높은 순

    def test_빈_티어(self):
        result = compare_tiers([])
        self.assertEqual(len(result), 0)

    def test_모든_필드_포함(self):
        tiers = [QualityTier(tier_name="test", model="m", cost_per_1k=0.01, quality_score=0.8)]
        result = compare_tiers(tiers)
        self.assertIn("tier_name", result[0])
        self.assertIn("value_ratio", result[0])
        self.assertIn("cost_per_1k", result[0])


if __name__ == "__main__":
    unittest.main()
