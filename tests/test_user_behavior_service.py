"""
UserBehaviorService 단위 테스트 (F6-11)
"""
import unittest
from services.analytics.user_behavior_service import UserBehaviorService


class TestUserBehaviorService(unittest.TestCase):

    def setUp(self):
        self.svc = UserBehaviorService()

    def test_record_and_feature_frequency(self):
        self.svc.record('generate', 'click', user_id='u1', session_id='s1')
        self.svc.record('generate', 'click', user_id='u2', session_id='s2')
        self.svc.record('export', 'click', user_id='u1', session_id='s1')
        freq = self.svc.get_feature_frequency(365)
        feature_map = {f['feature']: f['count'] for f in freq}
        self.assertEqual(feature_map['generate'], 2)
        self.assertEqual(feature_map['export'], 1)

    def test_sorted_by_frequency(self):
        for _ in range(5):
            self.svc.record('popular', 'click')
        self.svc.record('rare', 'click')
        freq = self.svc.get_feature_frequency(365)
        self.assertEqual(freq[0]['feature'], 'popular')

    def test_action_breakdown(self):
        self.svc.record('generate', 'start')
        self.svc.record('generate', 'start')
        self.svc.record('generate', 'complete')
        breakdown = self.svc.get_action_breakdown('generate', 365)
        self.assertEqual(breakdown['total'], 3)
        self.assertEqual(breakdown['actions']['start'], 2)
        self.assertEqual(breakdown['actions']['complete'], 1)

    def test_session_stats(self):
        self.svc.record('f', 'a', session_id='s1', timestamp='2026-01-01T10:00:00+00:00')
        self.svc.record('f', 'b', session_id='s1', timestamp='2026-01-01T10:05:00+00:00')
        stats = self.svc.get_session_stats()
        self.assertEqual(stats['total_sessions'], 1)
        self.assertAlmostEqual(stats['avg_duration_sec'], 300.0, delta=1.0)

    def test_user_activity(self):
        self.svc.record('generate', 'click', user_id='alice')
        self.svc.record('export', 'click', user_id='alice')
        self.svc.record('generate', 'click', user_id='bob')
        activity = self.svc.get_user_activity('alice', 365)
        self.assertEqual(activity['total_events'], 2)
        self.assertEqual(activity['features_used']['generate'], 1)
        self.assertEqual(activity['features_used']['export'], 1)

    def test_empty_feature_frequency(self):
        result = self.svc.get_feature_frequency(30)
        self.assertEqual(result, [])

    def test_empty_session_stats(self):
        stats = self.svc.get_session_stats()
        self.assertEqual(stats['total_sessions'], 0)


if __name__ == '__main__':
    unittest.main()
