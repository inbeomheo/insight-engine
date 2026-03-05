"""
SegmentService 단위 테스트 (F4-21)
"""
import unittest
from services.analytics.segment_service import SegmentService


class TestSegmentService(unittest.TestCase):

    def setUp(self):
        self.svc = SegmentService()

    def test_power_user(self):
        self.svc.update_stats('u1', {'monthly_uses': 60, 'days_since_last': 1})
        segments = self.svc.classify_user('u1')
        self.assertIn('power_user', segments)

    def test_dormant_user(self):
        self.svc.update_stats('u1', {'monthly_uses': 0, 'days_since_last': 45})
        segments = self.svc.classify_user('u1')
        self.assertIn('dormant', segments)

    def test_unknown_user(self):
        segments = self.svc.classify_user('nobody')
        self.assertEqual(segments, ['unknown'])

    def test_segment_counts(self):
        self.svc.update_stats('u1', {'monthly_uses': 60, 'days_since_last': 1})
        self.svc.update_stats('u2', {'monthly_uses': 5, 'days_since_last': 2})
        counts = self.svc.get_segment_counts()
        self.assertEqual(counts['power_user'], 1)
        self.assertEqual(counts['casual'], 1)

    def test_get_users_in_segment(self):
        self.svc.update_stats('u1', {'monthly_uses': 60, 'days_since_last': 1})
        self.svc.update_stats('u2', {'monthly_uses': 3, 'days_since_last': 1})
        users = self.svc.get_users_in_segment('power_user')
        self.assertIn('u1', users)
        self.assertNotIn('u2', users)


if __name__ == '__main__':
    unittest.main()
