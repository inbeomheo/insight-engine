"""repurpose_attribution_service 단위 테스트"""
import unittest

from services.repurpose_attribution_service import (
    RepurposeReport,
    DerivativePerf,
    attribute_repurpose,
)


class TestAttributeRepurpose(unittest.TestCase):
    """리퍼포즈 기여도 분석 테스트"""

    def test_empty_derivatives(self):
        result = attribute_repurpose("orig_1", [])
        self.assertIsInstance(result, RepurposeReport)
        self.assertEqual(result.original_id, "orig_1")
        self.assertEqual(result.derivatives, [])
        self.assertEqual(result.total_reach, 0)

    def test_single_derivative(self):
        derivatives = [
            {"derivative_id": "d1", "platform": "twitter", "reach": 1000, "engagement": 0.05},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(len(result.derivatives), 1)
        self.assertEqual(result.total_reach, 1000)
        self.assertAlmostEqual(result.derivatives[0].contribution_pct, 100.0)

    def test_multiple_derivatives(self):
        derivatives = [
            {"derivative_id": "d1", "platform": "twitter", "reach": 500, "engagement": 0.03},
            {"derivative_id": "d2", "platform": "linkedin", "reach": 300, "engagement": 0.08},
            {"derivative_id": "d3", "platform": "instagram", "reach": 200, "engagement": 0.12},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(result.total_reach, 1000)
        self.assertEqual(len(result.derivatives), 3)
        total_pct = sum(d.contribution_pct for d in result.derivatives)
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_sorted_by_contribution_desc(self):
        derivatives = [
            {"derivative_id": "small", "platform": "a", "reach": 100, "engagement": 0.1},
            {"derivative_id": "big", "platform": "b", "reach": 900, "engagement": 0.1},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(result.derivatives[0].derivative_id, "big")

    def test_multiplier_with_original_reach(self):
        derivatives = [
            {"derivative_id": "d1", "platform": "twitter", "reach": 500, "engagement": 0.05, "original_reach": 200},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(result.multiplier, 2.5)  # 500 / 200

    def test_multiplier_without_original_reach(self):
        derivatives = [
            {"derivative_id": "d1", "platform": "a", "reach": 100, "engagement": 0.1},
            {"derivative_id": "d2", "platform": "b", "reach": 100, "engagement": 0.1},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        # 원본 reach 없으면 파생 수와 같은 배수
        self.assertGreater(result.multiplier, 0)

    def test_zero_reach_derivatives(self):
        derivatives = [
            {"derivative_id": "d1", "platform": "a", "reach": 0, "engagement": 0},
        ]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(result.total_reach, 0)
        self.assertEqual(result.derivatives[0].contribution_pct, 0.0)

    def test_derivative_perf_dataclass(self):
        perf = DerivativePerf(
            derivative_id="d1", platform="twitter",
            reach=1000, engagement=0.05, contribution_pct=50.0,
        )
        self.assertEqual(perf.platform, "twitter")
        self.assertEqual(perf.contribution_pct, 50.0)

    def test_missing_fields_default(self):
        derivatives = [{"derivative_id": "d1"}]
        result = attribute_repurpose("orig_1", derivatives)
        self.assertEqual(result.derivatives[0].platform, "unknown")
        self.assertEqual(result.derivatives[0].reach, 0)


if __name__ == '__main__':
    unittest.main()
