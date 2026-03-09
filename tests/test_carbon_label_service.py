"""탄소 라벨 서비스 테스트"""

import unittest

from services.carbon_label_service import (
    CarbonEstimate,
    CarbonLabel,
    estimate_inference,
    estimate_storage,
    calculate_label,
    suggest_offset,
)


class TestEstimateInference(unittest.TestCase):
    """estimate_inference 함수 테스트"""

    def test_정상_추론_추정(self):
        result = estimate_inference(1000, 7.0)
        self.assertEqual(result.process, "inference")
        self.assertGreater(result.energy_kwh, 0)
        self.assertGreater(result.carbon_g, 0)

    def test_큰_모델_더_높은_탄소(self):
        small = estimate_inference(1000, 7.0)
        large = estimate_inference(1000, 70.0)
        self.assertGreater(large.carbon_g, small.carbon_g)

    def test_더_많은_토큰_더_높은_탄소(self):
        few = estimate_inference(100, 7.0)
        many = estimate_inference(10000, 7.0)
        self.assertGreater(many.carbon_g, few.carbon_g)

    def test_지역별_차이(self):
        us = estimate_inference(1000, 7.0, region="us")
        cn = estimate_inference(1000, 7.0, region="cn")
        self.assertGreater(cn.carbon_g, us.carbon_g)

    def test_0_토큰(self):
        result = estimate_inference(0, 7.0)
        self.assertEqual(result.carbon_g, 0.0)

    def test_nordic_낮은_탄소(self):
        nordic = estimate_inference(1000, 7.0, region="nordic")
        global_ = estimate_inference(1000, 7.0, region="global")
        self.assertLess(nordic.carbon_g, global_.carbon_g)


class TestEstimateStorage(unittest.TestCase):
    """estimate_storage 함수 테스트"""

    def test_정상_저장소_추정(self):
        result = estimate_storage(100, 30)
        self.assertEqual(result.process, "storage")
        self.assertGreater(result.energy_kwh, 0)
        self.assertGreater(result.carbon_g, 0)

    def test_0_크기(self):
        result = estimate_storage(0, 30)
        self.assertEqual(result.carbon_g, 0.0)

    def test_0_기간(self):
        result = estimate_storage(100, 0)
        self.assertEqual(result.carbon_g, 0.0)

    def test_긴_기간_높은_탄소(self):
        short = estimate_storage(100, 30)
        long = estimate_storage(100, 365)
        self.assertGreater(long.carbon_g, short.carbon_g)


class TestCalculateLabel(unittest.TestCase):
    """calculate_label 함수 테스트"""

    def test_A_등급(self):
        estimates = [CarbonEstimate(process="test", carbon_g=5.0)]
        label = calculate_label(estimates)
        self.assertEqual(label.label_grade, "A")
        self.assertAlmostEqual(label.total_carbon_g, 5.0)

    def test_B_등급(self):
        estimates = [CarbonEstimate(process="test", carbon_g=30.0)]
        label = calculate_label(estimates)
        self.assertEqual(label.label_grade, "B")

    def test_C_등급(self):
        estimates = [CarbonEstimate(process="test", carbon_g=80.0)]
        label = calculate_label(estimates)
        self.assertEqual(label.label_grade, "C")

    def test_D_등급(self):
        estimates = [CarbonEstimate(process="test", carbon_g=300.0)]
        label = calculate_label(estimates)
        self.assertEqual(label.label_grade, "D")

    def test_E_등급(self):
        estimates = [CarbonEstimate(process="test", carbon_g=600.0)]
        label = calculate_label(estimates)
        self.assertEqual(label.label_grade, "E")

    def test_여러_추정_합산(self):
        estimates = [
            CarbonEstimate(process="inference", carbon_g=20.0),
            CarbonEstimate(process="storage", carbon_g=15.0),
        ]
        label = calculate_label(estimates)
        self.assertAlmostEqual(label.total_carbon_g, 35.0)
        self.assertEqual(label.label_grade, "B")

    def test_빈_추정(self):
        label = calculate_label([])
        self.assertEqual(label.label_grade, "A")
        self.assertEqual(label.total_carbon_g, 0.0)


class TestSuggestOffset(unittest.TestCase):
    """suggest_offset 함수 테스트"""

    def test_낮은_탄소_제안(self):
        label = CarbonLabel(total_carbon_g=3.0)
        suggestions = suggest_offset(label)
        self.assertGreater(len(suggestions), 0)

    def test_높은_탄소_다양한_제안(self):
        label = CarbonLabel(total_carbon_g=600.0)
        suggestions = suggest_offset(label)
        self.assertGreaterEqual(len(suggestions), 3)


if __name__ == "__main__":
    unittest.main()
