"""experiment_accelerator_service 단위 테스트"""
import unittest
from datetime import datetime

from services.experiment_accelerator_service import (
    accelerate_experiment,
    AccelerationPlan,
    _calculate_progress,
    _estimate_completion,
    _generate_actions,
)


class TestCalculateProgress(unittest.TestCase):

    def test_direct_progress(self):
        self.assertAlmostEqual(_calculate_progress({'progress': 0.6}), 0.6)

    def test_progress_clamped(self):
        self.assertAlmostEqual(_calculate_progress({'progress': 1.5}), 1.0)
        self.assertAlmostEqual(_calculate_progress({'progress': -0.5}), 0.0)

    def test_sample_based(self):
        data = {'current_samples': 50, 'target_samples': 100}
        self.assertAlmostEqual(_calculate_progress(data), 0.5)

    def test_time_based(self):
        data = {'elapsed_days': 7, 'total_days': 14}
        self.assertAlmostEqual(_calculate_progress(data), 0.5)

    def test_no_data_returns_zero(self):
        self.assertAlmostEqual(_calculate_progress({}), 0.0)


class TestEstimateCompletion(unittest.TestCase):

    def test_completed_returns_today(self):
        result = _estimate_completion({}, 1.0)
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertEqual(result, today)

    def test_zero_progress_returns_future(self):
        result = _estimate_completion({}, 0.0)
        est_date = datetime.strptime(result, '%Y-%m-%d')
        self.assertGreater(est_date, datetime.now())

    def test_elapsed_days_based_estimation(self):
        data = {'elapsed_days': 5}
        result = _estimate_completion(data, 0.5)
        est_date = datetime.strptime(result, '%Y-%m-%d')
        self.assertGreater(est_date, datetime.now())

    def test_sample_rate_based(self):
        data = {
            'current_samples': 50,
            'target_samples': 100,
            'daily_sample_rate': 10,
        }
        result = _estimate_completion(data, 0.5)
        self.assertTrue(len(result) == 10)  # YYYY-MM-DD


class TestGenerateActions(unittest.TestCase):

    def test_early_stop_when_confident(self):
        data = {'confidence': 0.96, 'num_variants': 2}
        actions = _generate_actions(data, 0.6)
        self.assertTrue(any('조기 종료' in a for a in actions))

    def test_wait_when_samples_insufficient(self):
        data = {'current_samples': 10, 'target_samples': 100}
        actions = _generate_actions(data, 0.1)
        self.assertTrue(any('기다려' in a for a in actions))

    def test_increase_traffic_when_low_progress(self):
        data = {'num_variants': 2}
        actions = _generate_actions(data, 0.1)
        self.assertTrue(any('트래픽' in a for a in actions))

    def test_reduce_variants_suggestion(self):
        data = {'num_variants': 5, 'confidence': 0.5}
        actions = _generate_actions(data, 0.5)
        self.assertTrue(any('변형' in a and '제거' in a for a in actions))

    def test_default_message_when_normal(self):
        data = {'confidence': 0.7, 'num_variants': 2,
                'current_samples': 100, 'target_samples': 100}
        actions = _generate_actions(data, 0.8)
        # 조기 종료도 아니고 문제도 없으면 피크 시간 등 일반 권고
        self.assertTrue(len(actions) > 0)


class TestAccelerateExperiment(unittest.TestCase):

    def test_empty_data(self):
        result = accelerate_experiment({})
        self.assertIsInstance(result, AccelerationPlan)
        self.assertEqual(result.experiment_id, 'unknown')
        self.assertEqual(result.current_progress, 0.0)

    def test_none_data(self):
        result = accelerate_experiment(None)
        self.assertEqual(result.experiment_id, 'unknown')
        self.assertTrue(any('데이터가 없습니다' in a for a in result.recommended_actions))

    def test_basic_experiment(self):
        data = {
            'experiment_id': 'exp_001',
            'current_samples': 75,
            'target_samples': 100,
            'num_variants': 3,
            'elapsed_days': 5,
        }
        result = accelerate_experiment(data)
        self.assertEqual(result.experiment_id, 'exp_001')
        self.assertAlmostEqual(result.current_progress, 0.75)
        self.assertTrue(len(result.recommended_actions) > 0)
        self.assertTrue(len(result.estimated_completion) > 0)

    def test_completed_experiment(self):
        data = {
            'experiment_id': 'done',
            'progress': 1.0,
            'confidence': 0.99,
        }
        result = accelerate_experiment(data)
        self.assertAlmostEqual(result.current_progress, 1.0)

    def test_id_fallback(self):
        data = {'id': 'fallback_id', 'progress': 0.5}
        result = accelerate_experiment(data)
        self.assertEqual(result.experiment_id, 'fallback_id')

    def test_estimated_completion_is_date_format(self):
        data = {
            'experiment_id': 'test',
            'current_samples': 30,
            'target_samples': 100,
            'elapsed_days': 3,
        }
        result = accelerate_experiment(data)
        # YYYY-MM-DD 형식 확인
        try:
            datetime.strptime(result.estimated_completion, '%Y-%m-%d')
        except ValueError:
            self.fail("estimated_completion이 YYYY-MM-DD 형식이 아닙니다")

    def test_actions_contain_strings(self):
        data = {'experiment_id': 'a', 'progress': 0.2, 'num_variants': 5}
        result = accelerate_experiment(data)
        for action in result.recommended_actions:
            self.assertIsInstance(action, str)
            self.assertTrue(len(action) > 0)


if __name__ == '__main__':
    unittest.main()
