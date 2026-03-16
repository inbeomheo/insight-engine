"""Paddle 결제 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestPaddleRoutes(unittest.TestCase):
    """Paddle 결제 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_status(self, mock_svc, _mock_sb):
        """Paddle 상태 조회."""
        mock_svc.is_configured = True
        resp = self.client.get('/api/paddle/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['configured'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_webhook_invalid_signature(self, mock_svc, _mock_sb):
        """Paddle 웹훅 서명 실패 시 400."""
        mock_svc.verify_webhook.return_value = False
        resp = self.client.post('/api/paddle/webhook',
                                data=b'{}',
                                content_type='application/json',
                                headers={**_HEADERS, 'Paddle-Signature': 'bad'})
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_webhook_success(self, mock_svc, _mock_sb):
        """Paddle 웹훅 성공 처리."""
        mock_svc.verify_webhook.return_value = True
        mock_svc.handle_webhook.return_value = {'status': 'created', 'subscription_id': 'sub_1'}
        resp = self.client.post('/api/paddle/webhook',
                                json={'event_type': 'subscription.created', 'data': {'subscription_id': 'sub_1'}},
                                headers={**_HEADERS, 'Paddle-Signature': 'valid'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'created')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_get_subscription_not_found(self, mock_svc, _mock_sb):
        """구독 미발견 시 404."""
        mock_svc.get_subscription.return_value = None
        resp = self.client.get('/api/paddle/subscription/sub_999', headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
