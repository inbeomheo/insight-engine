"""하이브리드 과금 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestHybridBillingRoutes(unittest.TestCase):
    """하이브리드 과금 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_setup(self, mock_svc, _mock_sb):
        """과금 계정 설정 성공."""
        mock_svc.setup_account.return_value = {
            'base_credits': 100,
            'used': 0,
            'overage_rate': 500.0,
            'overage_charges': 0.0,
        }
        resp = self.client.post('/api/billing/setup',
                                json={'base_credits': 100, 'overage_rate': 500},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['base_credits'], 100)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_billing_setup_missing_params(self, _mock_sb):
        """필수 파라미터 누락 시 400."""
        resp = self.client.post('/api/billing/setup',
                                json={'base_credits': 100},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_consume(self, mock_svc, _mock_sb):
        """크레딧 사용 성공."""
        mock_svc.consume.return_value = {
            'used': 1,
            'base_remaining': 99,
            'overage_count': 0,
            'overage_charges': 0.0,
        }
        resp = self.client.post('/api/billing/consume',
                                json={'amount': 1},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['base_remaining'], 99)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_consume_no_account(self, mock_svc, _mock_sb):
        """계정 미설정 시 400."""
        mock_svc.consume.return_value = {'error': '과금 계정이 설정되지 않았습니다.'}
        resp = self.client.post('/api/billing/consume',
                                json={'amount': 1},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_summary(self, mock_svc, _mock_sb):
        """과금 요약 조회."""
        mock_svc.get_billing_summary.return_value = {
            'base_credits': 100,
            'used': 10,
            'base_remaining': 90,
            'overage_count': 0,
            'overage_rate': 500.0,
            'overage_charges': 0.0,
        }
        resp = self.client.get('/api/billing/summary', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['base_remaining'], 90)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_reset_monthly(self, mock_svc, _mock_sb):
        """월간 초기화."""
        mock_svc.reset_monthly.return_value = {
            'base_credits': 100,
            'used': 0,
            'overage_charges': 0.0,
        }
        resp = self.client.post('/api/billing/reset-monthly',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['used'], 0)


if __name__ == '__main__':
    unittest.main()
