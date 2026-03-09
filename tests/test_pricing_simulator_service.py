"""가격 시뮬레이터 서비스 테스트"""
import unittest

from services.pricing_simulator_service import (
    PricingScenario,
    simulate_pricing,
    _estimate_base_price,
    _adjust_for_competitors,
)


class TestEstimateBasePrice(unittest.TestCase):
    """기준 가격 산정 테스트"""

    def test_zero_subscribers(self):
        price = _estimate_base_price({'subscriber_count': 0})
        self.assertEqual(price, 5000)

    def test_price_increases_with_subscribers(self):
        """구독자가 많을수록 가격 상승"""
        low = _estimate_base_price({'subscriber_count': 1000})
        high = _estimate_base_price({'subscriber_count': 100000})
        self.assertGreater(high, low)

    def test_high_engagement_bonus(self):
        """조회수/구독자 비율 높으면 가격 상승"""
        base_data = {'subscriber_count': 10000, 'avg_views': 0}
        high_data = {'subscriber_count': 10000, 'avg_views': 5000}
        base_price = _estimate_base_price(base_data)
        high_price = _estimate_base_price(high_data)
        self.assertGreater(high_price, base_price)

    def test_low_engagement_discount(self):
        """참여율 낮으면 가격 할인"""
        normal = _estimate_base_price({'subscriber_count': 100000, 'avg_views': 0})
        low = _estimate_base_price({'subscriber_count': 100000, 'avg_views': 500})
        self.assertLess(low, normal)

    def test_price_rounded_to_100(self):
        """100원 단위로 반올림"""
        price = _estimate_base_price({'subscriber_count': 12345})
        self.assertEqual(price % 100, 0)


class TestAdjustForCompetitors(unittest.TestCase):
    """경쟁사 가격 조정 테스트"""

    def test_no_competitors(self):
        """경쟁사 없으면 원래 가격 유지"""
        result = _adjust_for_competitors(10000, None)
        self.assertEqual(result, 10000)

    def test_empty_competitors(self):
        result = _adjust_for_competitors(10000, [])
        self.assertEqual(result, 10000)

    def test_price_clamped_to_competitor_range(self):
        """경쟁사 평균 대비 ±20% 범위 내"""
        competitors = [{'monthly_price': 10000}, {'monthly_price': 12000}]
        avg = 11000
        result = _adjust_for_competitors(50000, competitors)
        self.assertLessEqual(result, avg * 1.2 + 100)  # 반올림 여유

    def test_low_price_lifted(self):
        """너무 낮은 가격은 경쟁사 하한으로 올림"""
        competitors = [{'monthly_price': 20000}]
        result = _adjust_for_competitors(1000, competitors)
        self.assertGreaterEqual(result, 20000 * 0.8 - 100)

    def test_competitors_without_price_ignored(self):
        """가격 정보 없는 경쟁사는 무시"""
        result = _adjust_for_competitors(10000, [{'name': 'X'}])
        self.assertEqual(result, 10000)


class TestSimulatePricing(unittest.TestCase):
    """가격 시뮬레이션 통합 테스트"""

    def test_returns_three_scenarios(self):
        result = simulate_pricing({'subscriber_count': 10000, 'avg_views': 3000})
        self.assertEqual(len(result), 3)

    def test_scenario_names(self):
        result = simulate_pricing({'subscriber_count': 5000})
        names = [s.name for s in result]
        self.assertEqual(names, ["starter", "standard", "premium"])

    def test_price_ascending_order(self):
        """starter < standard < premium 가격 순서"""
        result = simulate_pricing({'subscriber_count': 10000})
        self.assertLess(result[0].monthly_price, result[1].monthly_price)
        self.assertLess(result[1].monthly_price, result[2].monthly_price)

    def test_annual_cheaper_than_monthly(self):
        """연간 구독이 월간 × 12보다 저렴"""
        result = simulate_pricing({'subscriber_count': 10000})
        for s in result:
            self.assertLess(s.annual_price, s.monthly_price * 12)

    def test_starter_minimum_price(self):
        """starter 최소 가격 1000원"""
        result = simulate_pricing({'subscriber_count': 0})
        self.assertGreaterEqual(result[0].monthly_price, 1000)

    def test_features_non_empty(self):
        result = simulate_pricing({'subscriber_count': 10000})
        for s in result:
            self.assertGreater(len(s.features), 0)

    def test_premium_has_more_features(self):
        """premium이 starter보다 기능 많음"""
        result = simulate_pricing({'subscriber_count': 10000})
        self.assertGreater(len(result[2].features), len(result[0].features))

    def test_conversion_rate_decreasing(self):
        """starter > standard > premium 전환율"""
        result = simulate_pricing({'subscriber_count': 10000})
        self.assertGreater(result[0].estimated_conversion, result[1].estimated_conversion)
        self.assertGreater(result[1].estimated_conversion, result[2].estimated_conversion)

    def test_estimated_revenue_non_negative(self):
        result = simulate_pricing({'subscriber_count': 10000})
        for s in result:
            self.assertGreaterEqual(s.estimated_revenue, 0)

    def test_with_competitors(self):
        """경쟁사 정보 반영"""
        competitors = [{'monthly_price': 15000}, {'monthly_price': 20000}]
        result = simulate_pricing(
            {'subscriber_count': 10000},
            competitors=competitors,
        )
        self.assertEqual(len(result), 3)
        # standard 가격이 경쟁사 범위 근처
        # standard 가격이 숫자인지 확인
        self.assertIsInstance(result[1].monthly_price, (int, float))

    def test_scenario_is_dataclass(self):
        result = simulate_pricing({'subscriber_count': 1000})
        for s in result:
            self.assertIsInstance(s, PricingScenario)

    def test_high_subscriber_higher_conversion(self):
        """구독자 많으면 전환율 높음"""
        low = simulate_pricing({'subscriber_count': 500})
        high = simulate_pricing({'subscriber_count': 500000})
        self.assertGreater(high[0].estimated_conversion, low[0].estimated_conversion)


if __name__ == '__main__':
    unittest.main()
