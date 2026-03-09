"""holdout_measurement_service 단위 테스트"""
import unittest

from services.holdout_measurement_service import (
    HoldoutResult,
    measure_holdout,
    _mean,
    _std,
)


class TestMean(unittest.TestCase):
    """평균 계산 테스트"""

    def test_normal_values(self):
        self.assertAlmostEqual(_mean([1.0, 2.0, 3.0]), 2.0)

    def test_empty_list(self):
        self.assertEqual(_mean([]), 0.0)

    def test_single_value(self):
        self.assertEqual(_mean([5.0]), 5.0)


class TestStd(unittest.TestCase):
    """표준편차 계산 테스트"""

    def test_zero_variance(self):
        self.assertEqual(_std([5.0, 5.0, 5.0], 5.0), 0.0)

    def test_single_value(self):
        self.assertEqual(_std([5.0], 5.0), 0.0)

    def test_known_values(self):
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        mean = _mean(values)
        std = _std(values, mean)
        # 표본 표준편차 (n-1): sqrt(32/7) ≈ 2.138
        self.assertAlmostEqual(std, 2.138, places=2)


class TestMeasureHoldout(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_experiment(self):
        result = measure_holdout({"experiment_id": "exp1", "treatment": [], "control": []})
        self.assertIsInstance(result, HoldoutResult)
        self.assertEqual(result.experiment_id, "exp1")
        self.assertEqual(result.treatment_effect, 0.0)
        self.assertFalse(result.significant)

    def test_significant_positive_effect(self):
        # 처리군이 대조군보다 명확히 높은 경우
        treatment = [10.0, 11.0, 12.0, 10.5, 11.5, 12.5, 10.0, 11.0]
        control = [5.0, 6.0, 5.5, 6.5, 5.0, 5.5, 6.0, 6.5]
        result = measure_holdout({
            "experiment_id": "sig_test",
            "treatment": treatment,
            "control": control,
        })
        self.assertGreater(result.treatment_effect, 0)
        self.assertTrue(result.significant)
        self.assertGreater(result.confidence_interval[0], 0)

    def test_not_significant_overlapping(self):
        # 처리군과 대조군이 거의 같은 경우
        treatment = [5.0, 5.1, 5.0, 4.9, 5.0, 5.1]
        control = [5.0, 4.9, 5.0, 5.1, 5.0, 4.9]
        result = measure_holdout({
            "experiment_id": "no_sig",
            "treatment": treatment,
            "control": control,
        })
        self.assertFalse(result.significant)

    def test_negative_treatment_effect(self):
        treatment = [3.0, 3.5, 3.0, 3.5]
        control = [8.0, 8.5, 8.0, 8.5]
        result = measure_holdout({
            "experiment_id": "neg",
            "treatment": treatment,
            "control": control,
        })
        self.assertLess(result.treatment_effect, 0)
        self.assertTrue(result.significant)

    def test_sample_sizes_recorded(self):
        result = measure_holdout({
            "experiment_id": "sizes",
            "treatment": [1.0, 2.0, 3.0],
            "control": [4.0, 5.0],
        })
        self.assertEqual(result.sample_sizes["treatment"], 3)
        self.assertEqual(result.sample_sizes["control"], 2)

    def test_default_experiment_id(self):
        result = measure_holdout({"treatment": [1.0], "control": [1.0]})
        self.assertEqual(result.experiment_id, "unknown")

    def test_confidence_interval_tuple(self):
        result = measure_holdout({
            "experiment_id": "ci",
            "treatment": [10.0, 12.0, 11.0],
            "control": [8.0, 9.0, 8.5],
        })
        ci = result.confidence_interval
        self.assertIsInstance(ci, tuple)
        self.assertEqual(len(ci), 2)
        self.assertLessEqual(ci[0], ci[1])

    def test_dataclass_fields(self):
        result = HoldoutResult(
            experiment_id="test",
            treatment_effect=1.5,
            confidence_interval=(0.5, 2.5),
            significant=True,
            sample_sizes={"treatment": 10, "control": 10},
        )
        self.assertEqual(result.experiment_id, "test")
        self.assertEqual(result.treatment_effect, 1.5)


if __name__ == '__main__':
    unittest.main()
