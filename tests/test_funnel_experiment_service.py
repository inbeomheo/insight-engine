"""퍼널 실험 서비스 테스트"""
import unittest
from services.funnel_experiment_service import (
    create_funnel, compare_funnels, find_bottleneck, calculate_lift,
    FunnelStep, FunnelExperiment
)


class TestFunnelExperimentService(unittest.TestCase):

    def setUp(self):
        self.control_config = [
            {'name': '방문', 'visitors': 1000, 'conversions': 500},
            {'name': '가입', 'visitors': 500, 'conversions': 200},
            {'name': '구매', 'visitors': 200, 'conversions': 50},
        ]
        self.control = create_funnel(self.control_config)

    def test_create_funnel(self):
        self.assertEqual(len(self.control), 3)
        self.assertIsInstance(self.control[0], FunnelStep)

    def test_create_funnel_auto_rate(self):
        self.assertAlmostEqual(self.control[0].conversion_rate, 0.5)
        self.assertAlmostEqual(self.control[1].conversion_rate, 0.4)

    def test_create_funnel_zero_visitors(self):
        funnel = create_funnel([{'name': 'x', 'visitors': 0, 'conversions': 0}])
        self.assertEqual(funnel[0].conversion_rate, 0.0)

    def test_compare_funnels_variant_wins(self):
        variant_config = [
            {'name': '방문', 'visitors': 1000, 'conversions': 600},
            {'name': '가입', 'visitors': 600, 'conversions': 400},
            {'name': '구매', 'visitors': 400, 'conversions': 200},
        ]
        variant = create_funnel(variant_config)
        exp = compare_funnels(self.control, variant)
        self.assertIsInstance(exp, FunnelExperiment)
        self.assertEqual(exp.winner, 'variant')

    def test_compare_funnels_control_wins(self):
        bad_variant = create_funnel([
            {'name': '방문', 'visitors': 1000, 'conversions': 100},
            {'name': '가입', 'visitors': 100, 'conversions': 10},
            {'name': '구매', 'visitors': 10, 'conversions': 1},
        ])
        exp = compare_funnels(self.control, bad_variant)
        self.assertEqual(exp.winner, 'control')

    def test_compare_funnels_tie(self):
        exp = compare_funnels(self.control, self.control)
        self.assertIsNone(exp.winner)

    def test_find_bottleneck(self):
        bottleneck = find_bottleneck(self.control)
        self.assertEqual(bottleneck.name, '구매')  # 0.25 최저

    def test_find_bottleneck_empty(self):
        with self.assertRaises(ValueError):
            find_bottleneck([])

    def test_calculate_lift_positive(self):
        lift = calculate_lift(0.1, 0.15)
        self.assertAlmostEqual(lift, 50.0)

    def test_calculate_lift_negative(self):
        lift = calculate_lift(0.2, 0.1)
        self.assertAlmostEqual(lift, -50.0)

    def test_calculate_lift_zero_base(self):
        lift = calculate_lift(0, 0.1)
        self.assertEqual(lift, 0.0)


if __name__ == '__main__':
    unittest.main()
