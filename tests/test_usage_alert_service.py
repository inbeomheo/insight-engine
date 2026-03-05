"""
UsageAlertService 단위 테스트 (F4-09)
"""
import unittest
from services.usage.usage_alert_service import UsageAlertService


class TestUsageAlertService(unittest.TestCase):

    def setUp(self):
        self.svc = UsageAlertService(thresholds=[80, 100])

    def test_no_alert_below_threshold(self):
        alerts = self.svc.check_usage('user-1', 7, 10)
        self.assertEqual(len(alerts), 0)

    def test_alert_at_80_percent(self):
        alerts = self.svc.check_usage('user-1', 8, 10)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['threshold'], 80)

    def test_alert_at_100_percent(self):
        alerts = self.svc.check_usage('user-1', 10, 10)
        # 80%와 100% 둘 다 알림
        self.assertEqual(len(alerts), 2)

    def test_no_duplicate_alerts(self):
        self.svc.check_usage('user-1', 8, 10)
        alerts = self.svc.check_usage('user-1', 9, 10)
        self.assertEqual(len(alerts), 0)  # 이미 알림 보냄

    def test_get_alerts(self):
        self.svc.check_usage('user-1', 8, 10)
        alerts = self.svc.get_alerts('user-1')
        self.assertEqual(len(alerts), 1)

    def test_reset_alerts(self):
        self.svc.check_usage('user-1', 8, 10)
        self.svc.reset_alerts('user-1')
        # 리셋 후 다시 알림 발생 가능
        alerts = self.svc.check_usage('user-1', 8, 10)
        self.assertEqual(len(alerts), 1)

    def test_zero_total_no_error(self):
        alerts = self.svc.check_usage('user-1', 0, 0)
        self.assertEqual(len(alerts), 0)


if __name__ == '__main__':
    unittest.main()
