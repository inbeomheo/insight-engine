"""암호화폐 결제 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestCryptoRoutes(unittest.TestCase):
    """암호화폐 결제 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.crypto_service.COINBASE_API_KEY', '')
    def test_charge_not_configured_returns_503(self, _mock_sb):
        """Coinbase 미설정 시 503."""
        resp = self.client.post('/api/crypto/charge',
                                json={'amount': 10},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 503)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.crypto_service.COINBASE_API_KEY', 'test-key')
    def test_create_charge_success(self, _mock_sb):
        """결제 요청 생성 성공."""
        resp = self.client.post('/api/crypto/charge',
                                json={'amount': 9.99, 'currency': 'USD'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('id', data)
        self.assertEqual(data['status'], 'pending')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.crypto_service.COINBASE_API_KEY', 'test-key')
    def test_invalid_amount_returns_400(self, _mock_sb):
        """유효하지 않은 amount 시 400."""
        resp = self.client.post('/api/crypto/charge',
                                json={'amount': 0},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_charge_not_found(self, _mock_sb):
        """존재하지 않는 charge_id 시 404."""
        resp = self.client.get('/api/crypto/charge/NONEXIST',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
