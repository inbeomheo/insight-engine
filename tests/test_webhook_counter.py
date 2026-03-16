"""R19: WebhookService failure_count 속성 및 health/detailed 노출 검증"""
import unittest
from unittest.mock import patch, MagicMock

from services.platform.webhook_service import WebhookService


class TestWebhookFailureCount(unittest.TestCase):
    """WebhookService.failure_count 동작 검증"""

    def test_failure_count_initialized_to_zero(self):
        """초기 failure_count는 0이어야 함"""
        ws = WebhookService(url='https://example.com/hook', enabled=True)
        self.assertEqual(ws.failure_count, 0)

    @patch('services.platform.webhook_service.requests.post')
    def test_failure_count_increments_on_network_error(self, mock_post):
        """네트워크 오류 시 failure_count 증가"""
        mock_post.side_effect = ConnectionError("Connection refused")
        ws = WebhookService(url='https://example.com/hook', enabled=True)

        # _send를 직접 호출 (동기, 2회 시도 후 실패)
        ws._send('test.event', {'key': 'value'})
        self.assertEqual(ws.failure_count, 1)

    @patch('services.platform.webhook_service.requests.post')
    def test_failure_count_increments_on_4xx(self, mock_post):
        """4xx 에러 시 failure_count 증가"""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_post.return_value = mock_resp

        ws = WebhookService(url='https://example.com/hook', enabled=True)
        ws._send('test.event', {'key': 'value'})
        self.assertEqual(ws.failure_count, 1)

    @patch('services.platform.webhook_service.requests.post')
    def test_failure_count_not_incremented_on_success(self, mock_post):
        """성공 시 failure_count 변동 없음"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        ws = WebhookService(url='https://example.com/hook', enabled=True)
        ws._send('test.event', {'key': 'value'})
        self.assertEqual(ws.failure_count, 0)

    @patch('services.platform.webhook_service.requests.post')
    def test_failure_count_accumulates(self, mock_post):
        """여러 번 실패하면 누적됨"""
        mock_post.side_effect = ConnectionError("fail")
        ws = WebhookService(url='https://example.com/hook', enabled=True)

        ws._send('event1', {})
        ws._send('event2', {})
        self.assertEqual(ws.failure_count, 2)


class TestHealthDetailedWebhook(unittest.TestCase):
    """GET /api/health/detailed 응답에 webhook.failure_count 포함 검증"""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def setUp(self, _mock_sb):
        import app as flask_app
        self.app = flask_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_webhook_failure_count_in_health(self, _mock_sb):
        """health/detailed 응답에 webhook.failure_count 필드 포함"""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()

        self.assertIn('checks', data)
        self.assertIn('webhook', data['checks'])
        self.assertIn('failure_count', data['checks']['webhook'])
        self.assertIsInstance(data['checks']['webhook']['failure_count'], int)


if __name__ == '__main__':
    unittest.main()
