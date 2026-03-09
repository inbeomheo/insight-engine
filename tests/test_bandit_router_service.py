"""bandit_router_service 단위 테스트"""
import unittest

from services.bandit_router_service import (
    route_content,
    RoutingPlan,
    RoutedVariant,
    _compute_reward,
    _calculate_epsilon,
    _allocate_epsilon_greedy,
)


class TestComputeReward(unittest.TestCase):

    def test_direct_reward(self):
        self.assertAlmostEqual(_compute_reward({'reward': 0.8}), 0.8)

    def test_expected_reward(self):
        self.assertAlmostEqual(_compute_reward({'expected_reward': 0.6}), 0.6)

    def test_success_trial_ratio(self):
        variant = {'successes': 30, 'trials': 100}
        self.assertAlmostEqual(_compute_reward(variant), 0.3)

    def test_conversions_impressions(self):
        variant = {'conversions': 50, 'impressions': 200}
        self.assertAlmostEqual(_compute_reward(variant), 0.25)

    def test_zero_trials(self):
        variant = {'successes': 10, 'trials': 0}
        # fallback to metric_value
        self.assertAlmostEqual(_compute_reward(variant), 0.0)

    def test_negative_clamped(self):
        self.assertAlmostEqual(_compute_reward({'reward': -1}), 0.0)


class TestCalculateEpsilon(unittest.TestCase):

    def test_no_data_high_epsilon(self):
        variants = [{'id': 'a'}, {'id': 'b'}]
        epsilon = _calculate_epsilon(variants)
        self.assertEqual(epsilon, 0.5)

    def test_low_data_high_epsilon(self):
        variants = [
            {'trials': 5},
            {'trials': 5},
        ]
        epsilon = _calculate_epsilon(variants)
        self.assertGreaterEqual(epsilon, 0.2)

    def test_high_data_low_epsilon(self):
        variants = [
            {'trials': 10000},
            {'trials': 10000},
        ]
        epsilon = _calculate_epsilon(variants)
        self.assertLessEqual(epsilon, 0.1)


class TestAllocateEpsilonGreedy(unittest.TestCase):

    def test_basic_allocation(self):
        variants = [
            {'reward': 0.8},
            {'reward': 0.2},
        ]
        alloc = _allocate_epsilon_greedy(variants, 100, 0.1)
        self.assertEqual(sum(alloc), 100)
        # 높은 보상 변형에 더 많은 트래픽
        self.assertGreater(alloc[0], alloc[1])

    def test_total_matches_traffic(self):
        variants = [{'reward': 0.5}, {'reward': 0.3}, {'reward': 0.7}]
        alloc = _allocate_epsilon_greedy(variants, 1000, 0.1)
        self.assertEqual(sum(alloc), 1000)

    def test_all_variants_get_traffic(self):
        """탐색 때문에 모든 변형이 최소 트래픽 받아야 함"""
        variants = [{'reward': 0.9}, {'reward': 0.01}]
        alloc = _allocate_epsilon_greedy(variants, 100, 0.2)
        self.assertTrue(all(a > 0 for a in alloc))

    def test_empty_variants(self):
        alloc = _allocate_epsilon_greedy([], 100, 0.1)
        self.assertEqual(alloc, [])


class TestRouteContent(unittest.TestCase):

    def test_empty_variants(self):
        result = route_content([], 100)
        self.assertIsInstance(result, RoutingPlan)
        self.assertEqual(len(result.variants), 0)

    def test_zero_traffic(self):
        result = route_content([{'id': 'a', 'reward': 0.5}], 0)
        self.assertEqual(len(result.variants), 0)

    def test_single_variant_gets_all_traffic(self):
        result = route_content([{'id': 'v1', 'reward': 0.5}], 100)
        self.assertEqual(len(result.variants), 1)
        self.assertEqual(result.variants[0].allocated_traffic, 100)
        self.assertEqual(result.variants[0].variant_id, 'v1')

    def test_multiple_variants_traffic_sum(self):
        variants = [
            {'id': 'a', 'reward': 0.8},
            {'id': 'b', 'reward': 0.2},
            {'id': 'c', 'reward': 0.5},
        ]
        result = route_content(variants, 1000)
        total = sum(v.allocated_traffic for v in result.variants)
        self.assertEqual(total, 1000)

    def test_best_variant_gets_most_traffic(self):
        variants = [
            {'id': 'low', 'reward': 0.1},
            {'id': 'high', 'reward': 0.9},
        ]
        result = route_content(variants, 1000)
        high_var = next(v for v in result.variants if v.variant_id == 'high')
        low_var = next(v for v in result.variants if v.variant_id == 'low')
        self.assertGreater(high_var.allocated_traffic, low_var.allocated_traffic)

    def test_algorithm_name(self):
        result = route_content([{'id': 'x', 'reward': 0.5}], 100)
        self.assertEqual(result.algorithm, 'epsilon-greedy')

    def test_exploration_rate_range(self):
        variants = [{'id': 'a', 'trials': 500}, {'id': 'b', 'trials': 500}]
        result = route_content(variants, 100)
        self.assertGreaterEqual(result.exploration_rate, 0.01)
        self.assertLessEqual(result.exploration_rate, 0.5)

    def test_variant_id_fallback(self):
        variants = [{'variant_id': 'test_v', 'reward': 0.5}]
        result = route_content(variants, 50)
        self.assertEqual(result.variants[0].variant_id, 'test_v')

    def test_expected_reward_in_result(self):
        variants = [{'id': 'x', 'reward': 0.75}]
        result = route_content(variants, 50)
        self.assertAlmostEqual(result.variants[0].expected_reward, 0.75)

    def test_sorted_by_traffic_desc(self):
        variants = [
            {'id': 'a', 'reward': 0.1},
            {'id': 'b', 'reward': 0.9},
            {'id': 'c', 'reward': 0.5},
        ]
        result = route_content(variants, 1000)
        traffics = [v.allocated_traffic for v in result.variants]
        self.assertEqual(traffics, sorted(traffics, reverse=True))


if __name__ == '__main__':
    unittest.main()
