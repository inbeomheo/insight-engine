"""
CostTrackerService 단위 테스트 (F6-05)
"""
import unittest
from services.analytics.cost_tracker_service import CostTrackerService


class TestCostTrackerService(unittest.TestCase):

    def setUp(self):
        self.svc = CostTrackerService()

    def test_calculate_cost_known_model(self):
        cost = self.svc.calculate_cost('chatmock/gpt-5.4-mini', 1000, 500)
        self.assertEqual(cost, 0.0)

    def test_calculate_cost_default_model(self):
        cost = self.svc.calculate_cost('unknown/model', 1000, 1000)
        self.assertEqual(cost, 0.0)

    def test_record_returns_cost(self):
        cost = self.svc.record('chatmock/gpt-5.4-mini', 500, 300, user_id='user1')
        self.assertEqual(cost, 0.0)

    def test_total_cost(self):
        self.svc.record('unknown/model', 1000, 1000)
        self.svc.record('unknown/model', 1000, 1000)
        result = self.svc.get_total_cost()
        self.assertEqual(result['total_cost_usd'], 0.0)
        self.assertEqual(result['total_records'], 2)

    def test_cost_by_model(self):
        self.svc.record('model_a', 1000, 0, user_id='u1')
        self.svc.record('model_b', 0, 1000, user_id='u2')
        by_model = self.svc.get_cost_by_model()
        model_names = [m['model'] for m in by_model]
        self.assertIn('model_a', model_names)
        self.assertIn('model_b', model_names)

    def test_daily_cost(self):
        self.svc.record('model', 1000, 1000, timestamp='2026-01-01T00:00:00+00:00')
        self.svc.record('model', 1000, 1000, timestamp='2026-01-02T00:00:00+00:00')
        daily = self.svc.get_daily_cost(365)
        dates = [d['date'] for d in daily]
        self.assertIn('2026-01-01', dates)
        self.assertIn('2026-01-02', dates)

    def test_empty_total(self):
        result = self.svc.get_total_cost()
        self.assertEqual(result['total_cost_usd'], 0.0)
        self.assertEqual(result['total_records'], 0)


if __name__ == '__main__':
    unittest.main()
