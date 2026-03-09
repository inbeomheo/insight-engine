"""실험 캔버스 서비스 테스트"""
import unittest
from services.experiment_canvas_service import (
    design_experiment, calculate_sample_size, evaluate_results, is_significant,
    Experiment, ExperimentResult
)


class TestExperimentCanvasService(unittest.TestCase):

    def test_design_experiment(self):
        exp = design_experiment(
            'CTA 색상 테스트', '빨간 CTA가 더 높은 전환율',
            [{'name': 'red'}, {'name': 'blue'}], 'conversion_rate'
        )
        self.assertIsInstance(exp, Experiment)
        self.assertEqual(exp.status, 'draft')
        self.assertEqual(len(exp.variants), 2)

    def test_calculate_sample_size_positive(self):
        n = calculate_sample_size(0.1, 0.05, 0.95)
        self.assertGreater(n, 0)

    def test_calculate_sample_size_invalid_rate(self):
        self.assertEqual(calculate_sample_size(0, 0.05), 0)
        self.assertEqual(calculate_sample_size(1.0, 0.05), 0)

    def test_calculate_sample_size_zero_effect(self):
        self.assertEqual(calculate_sample_size(0.1, 0), 0)

    def test_evaluate_results_with_winner(self):
        exp = design_experiment('test', 'h', [{'name': 'A'}, {'name': 'B'}], 'rate')
        exp.sample_size = 100
        data = {
            'A': {'total': 100, 'conversions': 10},
            'B': {'total': 100, 'conversions': 30},
        }
        result = evaluate_results(exp, data)
        self.assertIsInstance(result, ExperimentResult)
        self.assertEqual(result.winner, 'B')

    def test_evaluate_results_no_winner(self):
        exp = design_experiment('test', 'h', [{'name': 'A'}, {'name': 'B'}], 'rate')
        exp.sample_size = 100
        data = {
            'A': {'total': 100, 'conversions': 50},
            'B': {'total': 100, 'conversions': 50},
        }
        result = evaluate_results(exp, data)
        self.assertIsNone(result.winner)

    def test_evaluate_results_empty_data(self):
        exp = design_experiment('test', 'h', [{'name': 'A'}], 'rate')
        exp.sample_size = 100
        result = evaluate_results(exp, {'A': {'total': 0, 'conversions': 0}})
        self.assertEqual(result.variant_metrics['A'], 0.0)

    def test_is_significant_true(self):
        result = ExperimentResult('e1', 'A', 0.96, {'A': 0.3, 'B': 0.1})
        self.assertTrue(is_significant(result, 0.95))

    def test_is_significant_false_low_confidence(self):
        result = ExperimentResult('e1', 'A', 0.5, {'A': 0.3, 'B': 0.1})
        self.assertFalse(is_significant(result, 0.95))

    def test_is_significant_false_no_winner(self):
        result = ExperimentResult('e1', None, 0.99, {'A': 0.3, 'B': 0.3})
        self.assertFalse(is_significant(result))

    def test_calculate_sample_size_different_confidence(self):
        n90 = calculate_sample_size(0.1, 0.05, 0.90)
        n99 = calculate_sample_size(0.1, 0.05, 0.99)
        self.assertLess(n90, n99)


if __name__ == '__main__':
    unittest.main()
