"""사용량 알림 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestUsageAlertRoutes(unittest.TestCase):
    """사용량 알림 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_alert_service.usage_alert_service')
    def test_get_alerts(self, mock_svc, _mock_sb):
        """알림 목록 조회 성공."""
        mock_svc.get_alerts.return_value = [
            {'user_id': 'u1', 'threshold': 80, 'message': '80% 도달'}
        ]
        resp = self.client.get('/api/user/usage-alerts', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['alerts']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_alert_service.usage_alert_service')
    def test_check_alerts_returns_new(self, mock_svc, _mock_sb):
        """사용량 체크 시 새 알림 반환."""
        mock_svc.check_usage.return_value = [
            {'threshold': 80, 'percentage': 85.0}
        ]
        resp = self.client.post('/api/user/usage-alerts/check',
                                json={'used': 17, 'total': 20},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['new_alerts']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_check_alerts_missing_params(self, _mock_sb):
        """필수 파라미터 누락 시 400."""
        resp = self.client.post('/api/user/usage-alerts/check',
                                json={'used': 5},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_alert_service.usage_alert_service')
    def test_reset_alerts(self, mock_svc, _mock_sb):
        """알림 초기화 성공."""
        resp = self.client.post('/api/user/usage-alerts/reset',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        mock_svc.reset_alerts.assert_called_once()


if __name__ == '__main__':
    unittest.main()
