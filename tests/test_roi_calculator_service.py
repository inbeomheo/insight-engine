"""
ROICalculatorService 단위 테스트 (F6-08)
"""
import unittest
from services.analytics.roi_calculator_service import ROICalculatorService


class TestROICalculatorService(unittest.TestCase):

    def setUp(self):
        self.svc = ROICalculatorService(value_per_visitor=0.05, cpc_usd=1.5)

    def test_basic_roi(self):
        result = self.svc.calculate_roi(
            generation_cost_usd=1.0,
            views=100,
            clicks=10,
        )
        # 트래픽 가치: 100 * 0.05 = 5.0
        # SEO 클릭 가치: 10 * 1.5 = 15.0
        # 총 가치: 20.0, 비용: 1.0 → ROI = 1900%
        self.assertAlmostEqual(result['traffic_value_usd'], 5.0)
        self.assertAlmostEqual(result['seo_value_usd'], 15.0)
        self.assertAlmostEqual(result['total_value_usd'], 20.0)
        self.assertGreater(result['roi_pct'], 0)

    def test_zero_cost_roi(self):
        result = self.svc.calculate_roi(generation_cost_usd=0, views=100)
        self.assertEqual(result['roi_pct'], 0.0)

    def test_negative_roi(self):
        result = self.svc.calculate_roi(generation_cost_usd=100.0, views=1)
        self.assertLess(result['roi_pct'], 0)

    def test_with_conversions(self):
        result = self.svc.calculate_roi(
            generation_cost_usd=5.0,
            views=0,
            conversions=10,
            revenue_per_conversion_usd=10.0,
        )
        self.assertAlmostEqual(result['conversion_revenue_usd'], 100.0)
        self.assertAlmostEqual(result['total_value_usd'], 100.0)

    def test_breakeven_views(self):
        result = self.svc.calculate_roi(generation_cost_usd=5.0, views=0)
        # 손익분기 = 5.0 / 0.05 = 100
        self.assertEqual(result['breakeven_views'], 100)

    def test_batch_roi(self):
        items = [
            {'content_id': 'a', 'generation_cost_usd': 1.0, 'views': 1000, 'clicks': 0},
            {'content_id': 'b', 'generation_cost_usd': 1.0, 'views': 10, 'clicks': 0},
        ]
        results = self.svc.batch_roi(items)
        self.assertEqual(len(results), 2)
        # 내림차순 정렬 확인
        self.assertGreater(results[0]['roi_pct'], results[1]['roi_pct'])
        self.assertEqual(results[0]['content_id'], 'a')


if __name__ == '__main__':
    unittest.main()
