"""
TeamBillingService 단위 테스트 (F4-08)
"""
import unittest
from services.payment.team_billing_service import TeamBillingService


class TestTeamBillingService(unittest.TestCase):

    def setUp(self):
        self.svc = TeamBillingService()

    def test_allocate_credits(self):
        result = self.svc.allocate_credits('team-1', 100, 'admin')
        self.assertEqual(result['total'], 100)
        self.assertEqual(result['used'], 0)

    def test_allocate_zero_credits_rejected(self):
        result = self.svc.allocate_credits('team-1', 0, 'admin')
        self.assertIn('error', result)

    def test_consume_credit(self):
        self.svc.allocate_credits('team-1', 10, 'admin')
        result = self.svc.consume_credit('team-1', 'user-a', 1)
        self.assertTrue(result['success'])
        self.assertEqual(result['remaining'], 9)

    def test_consume_over_limit(self):
        self.svc.allocate_credits('team-1', 1, 'admin')
        self.svc.consume_credit('team-1', 'user-a', 1)
        result = self.svc.consume_credit('team-1', 'user-b', 1)
        self.assertIn('error', result)

    def test_consume_no_team(self):
        result = self.svc.consume_credit('no-team', 'user-a')
        self.assertIn('error', result)

    def test_get_team_usage(self):
        self.svc.allocate_credits('team-1', 50, 'admin')
        self.svc.consume_credit('team-1', 'user-a', 3)
        usage = self.svc.get_team_usage('team-1')
        self.assertEqual(usage['total'], 50)
        self.assertEqual(usage['used'], 3)
        self.assertEqual(usage['remaining'], 47)

    def test_get_member_usage(self):
        self.svc.allocate_credits('team-1', 100, 'admin')
        self.svc.consume_credit('team-1', 'user-a', 2)
        self.svc.consume_credit('team-1', 'user-b', 3)
        self.svc.consume_credit('team-1', 'user-a', 1)
        members = self.svc.get_member_usage('team-1')
        usage_map = {m['user_id']: m['total_used'] for m in members}
        self.assertEqual(usage_map['user-a'], 3)
        self.assertEqual(usage_map['user-b'], 3)


if __name__ == '__main__':
    unittest.main()
