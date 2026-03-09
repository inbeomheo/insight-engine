"""ROI 플래너 서비스 테스트"""

import unittest
from services.roi_planner_service import (
    Investment, ROIProjection,
    calculate_roi, project_monthly, find_breakeven, compare_scenarios,
)


class TestROIPlannerService(unittest.TestCase):
    """ROI 플래너 서비스 테스트"""

    def test_calculate_roi_positive(self):
        """양의 ROI"""
        investments = [Investment("content", 1000, 6)]
        result = calculate_roi(investments, 2000)
        self.assertEqual(result.total_investment, 1000)
        self.assertEqual(result.projected_revenue, 2000)
        self.assertEqual(result.roi_pct, 100.0)

    def test_calculate_roi_negative(self):
        """음의 ROI"""
        investments = [Investment("ads", 5000, 3)]
        result = calculate_roi(investments, 2000)
        self.assertTrue(result.roi_pct < 0)

    def test_calculate_roi_zero_investment(self):
        """투자 없음"""
        result = calculate_roi([], 1000)
        self.assertEqual(result.total_investment, 0)

    def test_calculate_roi_multiple_investments(self):
        """다중 투자"""
        investments = [
            Investment("content", 500, 6),
            Investment("ads", 300, 6),
            Investment("tools", 200, 6),
        ]
        result = calculate_roi(investments, 2000)
        self.assertEqual(result.total_investment, 1000)
        self.assertEqual(result.roi_pct, 100.0)

    def test_calculate_roi_has_projections(self):
        """월별 예측 포함"""
        investments = [Investment("content", 1200, 12)]
        result = calculate_roi(investments, 2400)
        self.assertEqual(len(result.monthly_projections), 12)

    def test_project_monthly_growth(self):
        """성장률 적용 월별 예측"""
        projections = project_monthly(1200, 0.1, 12)
        self.assertEqual(len(projections), 12)
        # 후반 월 수익이 초반보다 높아야 함
        self.assertGreater(projections[-1]["revenue"], projections[0]["revenue"])

    def test_project_monthly_cumulative(self):
        """누적 수익 계산"""
        projections = project_monthly(120, 0.5, 3)
        # 누적 수익이 월별로 증가해야 함 (성장이 충분하면)
        self.assertEqual(len(projections), 3)
        for p in projections:
            self.assertIn("cumulative_profit", p)

    def test_find_breakeven_exists(self):
        """손익분기점 존재"""
        projections = [
            {"month": 1, "cumulative_profit": -100},
            {"month": 2, "cumulative_profit": -30},
            {"month": 3, "cumulative_profit": 50},
        ]
        self.assertEqual(find_breakeven(projections), 3)

    def test_find_breakeven_not_reached(self):
        """손익분기점 미달성"""
        projections = [
            {"month": 1, "cumulative_profit": -100},
            {"month": 2, "cumulative_profit": -50},
        ]
        self.assertEqual(find_breakeven(projections), 0)

    def test_find_breakeven_immediate(self):
        """즉시 손익분기 달성"""
        projections = [{"month": 1, "cumulative_profit": 100}]
        self.assertEqual(find_breakeven(projections), 1)

    def test_compare_scenarios(self):
        """시나리오 비교"""
        s1 = ROIProjection(1000, 2000, 100.0, 6, [])
        s2 = ROIProjection(1000, 3000, 200.0, 4, [])
        result = compare_scenarios([s1, s2])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["best_scenario"], 2)
        self.assertEqual(result["best_roi_pct"], 200.0)

    def test_compare_scenarios_empty(self):
        """빈 시나리오"""
        result = compare_scenarios([])
        self.assertEqual(result["count"], 0)

    def test_compare_scenarios_single(self):
        """단일 시나리오"""
        s = ROIProjection(1000, 1500, 50.0, 8, [])
        result = compare_scenarios([s])
        self.assertEqual(result["best_scenario"], 1)

    def test_find_breakeven_empty(self):
        """빈 예측 목록"""
        self.assertEqual(find_breakeven([]), 0)


if __name__ == "__main__":
    unittest.main()
