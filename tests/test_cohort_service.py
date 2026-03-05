"""
CohortService 단위 테스트 (F4-13)
"""
import unittest
from services.analytics.cohort_service import CohortService


class TestCohortService(unittest.TestCase):

    def setUp(self):
        self.svc = CohortService()

    def test_record_and_retention(self):
        self.svc.record_event('u1', 'signup', '2026-01-01')
        self.svc.record_event('u1', 'active', '2026-01-03')
        self.svc.record_event('u1', 'active', '2026-01-10')
        result = self.svc.get_retention('week')
        self.assertTrue(len(result) > 0)

    def test_ltv_calculation(self):
        self.svc.record_event('u1', 'purchase', revenue=29000)
        self.svc.record_event('u1', 'purchase', revenue=29000)
        self.svc.record_event('u2', 'purchase', revenue=10000)
        ltv = self.svc.get_ltv()
        self.assertEqual(ltv['total_users'], 2)
        self.assertEqual(ltv['total_revenue'], 68000)
        self.assertEqual(ltv['average_ltv'], 34000)

    def test_empty_ltv(self):
        ltv = self.svc.get_ltv()
        self.assertEqual(ltv['average_ltv'], 0)

    def test_period_key_month(self):
        key = CohortService._get_period_key('2026-03-15', 'month')
        self.assertEqual(key, '2026-03')

    def test_period_key_week(self):
        key = CohortService._get_period_key('2026-01-01', 'week')
        self.assertTrue(key.startswith('2026-W') or key.startswith('2025-W'))


if __name__ == '__main__':
    unittest.main()
