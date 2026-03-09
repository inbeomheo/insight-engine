"""adaptive_test_service 단위 테스트"""
import unittest

from services.adaptive_test_service import (
    run_adaptive_test,
    AdaptiveResult,
    VariantResult,
    _safe_float,
    _safe_int,
    _extract_metric,
    _extract_sample_size,
    _compute_confidence,
)


class TestSafeConversions(unittest.TestCase):

    def test_safe_float(self):
        self.assertEqual(_safe_float(3.14), 3.14)
        self.assertEqual(_safe_float('2.5'), 2.5)
        self.assertEqual(_safe_float(None), 0.0)
        self.assertEqual(_safe_float('abc', 1.0), 1.0)

    def test_safe_int(self):
        self.assertEqual(_safe_int(42), 42)
        self.assertEqual(_safe_int('10'), 10)
        self.assertEqual(_safe_int(None), 0)
        self.assertEqual(_safe_int('abc', 5), 5)


class TestExtractMetric(unittest.TestCase):

    def test_named_metric(self):
        variant = {'engagement': 0.85, 'ctr': 0.12}
        self.assertAlmostEqual(_extract_metric(variant, 'engagement'), 0.85)
        self.assertAlmostEqual(_extract_metric(variant, 'ctr'), 0.12)

    def test_fallback_to_metric_value(self):
        variant = {'metric_value': 0.6}
        self.assertAlmostEqual(_extract_metric(variant, 'unknown'), 0.6)

    def test_missing_returns_zero(self):
        self.assertAlmostEqual(_extract_metric({}, 'engagement'), 0.0)


class TestExtractSampleSize(unittest.TestCase):

    def test_sample_size_key(self):
        self.assertEqual(_extract_sample_size({'sample_size': 100}), 100)

    def test_impressions_key(self):
        self.assertEqual(_extract_sample_size({'impressions': 500}), 500)

    def test_missing_returns_zero(self):
        self.assertEqual(_extract_sample_size({}), 0)


class TestComputeConfidence(unittest.TestCase):

    def test_low_sample_low_confidence(self):
        best = {'engagement': 0.8, 'sample_size': 3}
        second = {'engagement': 0.7, 'sample_size': 3}
        conf = _compute_confidence(best, second, 'engagement')
        self.assertLess(conf, 0.6)

    def test_high_sample_high_confidence(self):
        best = {'engagement': 0.8, 'sample_size': 10000}
        second = {'engagement': 0.3, 'sample_size': 10000}
        conf = _compute_confidence(best, second, 'engagement')
        self.assertGreater(conf, 0.8)

    def test_equal_values_moderate_confidence(self):
        best = {'engagement': 0.5, 'sample_size': 100}
        second = {'engagement': 0.5, 'sample_size': 100}
        conf = _compute_confidence(best, second, 'engagement')
        self.assertLessEqual(conf, 0.6)


class TestRunAdaptiveTest(unittest.TestCase):

    def test_empty_variants(self):
        result = run_adaptive_test([])
        self.assertIsInstance(result, AdaptiveResult)
        self.assertEqual(result.winner_id, '')
        self.assertEqual(result.variants_tested, 0)
        self.assertEqual(result.confidence, 0.0)

    def test_single_variant(self):
        variants = [{'id': 'v1', 'engagement': 0.8, 'sample_size': 100}]
        result = run_adaptive_test(variants)
        self.assertEqual(result.winner_id, 'v1')
        self.assertEqual(result.variants_tested, 1)
        self.assertEqual(result.confidence, 1.0)

    def test_winner_has_highest_metric(self):
        variants = [
            {'id': 'low', 'engagement': 0.3, 'sample_size': 100},
            {'id': 'high', 'engagement': 0.9, 'sample_size': 100},
            {'id': 'mid', 'engagement': 0.6, 'sample_size': 100},
        ]
        result = run_adaptive_test(variants)
        self.assertEqual(result.winner_id, 'high')
        self.assertEqual(result.variants_tested, 3)

    def test_winner_is_winner_flag(self):
        variants = [
            {'id': 'a', 'engagement': 0.5, 'sample_size': 50},
            {'id': 'b', 'engagement': 0.8, 'sample_size': 50},
        ]
        result = run_adaptive_test(variants)
        winner_results = [r for r in result.results if r.is_winner]
        self.assertEqual(len(winner_results), 1)
        self.assertEqual(winner_results[0].variant_id, 'b')

    def test_results_sorted_desc(self):
        variants = [
            {'id': 'c', 'engagement': 0.1, 'sample_size': 50},
            {'id': 'a', 'engagement': 0.9, 'sample_size': 50},
            {'id': 'b', 'engagement': 0.5, 'sample_size': 50},
        ]
        result = run_adaptive_test(variants)
        values = [r.metric_value for r in result.results]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_custom_metric(self):
        variants = [
            {'id': 'a', 'ctr': 0.15, 'sample_size': 100},
            {'id': 'b', 'ctr': 0.05, 'sample_size': 100},
        ]
        result = run_adaptive_test(variants, metric='ctr')
        self.assertEqual(result.winner_id, 'a')

    def test_variant_id_fallback(self):
        """variant_id 키도 지원"""
        variants = [{'variant_id': 'test_v', 'engagement': 0.7, 'sample_size': 50}]
        result = run_adaptive_test(variants)
        self.assertEqual(result.winner_id, 'test_v')

    def test_confidence_range(self):
        variants = [
            {'id': 'a', 'engagement': 0.8, 'sample_size': 200},
            {'id': 'b', 'engagement': 0.6, 'sample_size': 200},
        ]
        result = run_adaptive_test(variants)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_variant_result_dataclass(self):
        variants = [{'id': 'x', 'engagement': 0.5, 'sample_size': 30}]
        result = run_adaptive_test(variants)
        vr = result.results[0]
        self.assertIsInstance(vr, VariantResult)
        self.assertEqual(vr.variant_id, 'x')
        self.assertEqual(vr.sample_size, 30)


if __name__ == '__main__':
    unittest.main()
