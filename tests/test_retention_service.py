"""
RetentionService 단위 테스트 (F4-22)
"""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from services.retention_service import RetentionService


class TestRetentionService(unittest.TestCase):

    def setUp(self):
        self.svc = RetentionService()

    def test_active_user(self):
        self.svc.record_activity('u1')
        status = self.svc.get_user_status('u1')
        self.assertEqual(status['status'], 'active')

    def test_warning_user(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self.svc._last_active['u1'] = old_time
        status = self.svc.get_user_status('u1')
        self.assertEqual(status['status'], 'warning')

    def test_at_risk_user(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=16)).isoformat()
        self.svc._last_active['u1'] = old_time
        status = self.svc.get_user_status('u1')
        self.assertEqual(status['status'], 'at_risk')

    def test_churned_user(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        self.svc._last_active['u1'] = old_time
        status = self.svc.get_user_status('u1')
        self.assertEqual(status['status'], 'churned')

    def test_unknown_user(self):
        status = self.svc.get_user_status('nobody')
        self.assertEqual(status['status'], 'unknown')

    def test_check_inactive_users(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        self.svc._last_active['u1'] = old_time
        self.svc.record_activity('u2')  # 활성
        alerts = self.svc.check_inactive_users()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['user_id'], 'u1')


if __name__ == '__main__':
    unittest.main()
