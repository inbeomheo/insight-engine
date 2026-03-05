"""
CryptoService 단위 테스트 (F4-17)
"""
import unittest
from unittest.mock import patch
from services.payment.crypto_service import CryptoService


class TestCryptoService(unittest.TestCase):

    @patch('services.payment.crypto_service.COINBASE_API_KEY', 'test-key')
    def test_create_charge(self):
        svc = CryptoService()
        result = svc.create_charge('u1', 29.99, 'USD', 'Pro 플랜')
        self.assertIn('id', result)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['amount'], 29.99)

    def test_create_charge_not_configured(self):
        svc = CryptoService()
        result = svc.create_charge('u1', 10, 'USD')
        self.assertIn('error', result)

    @patch('services.payment.crypto_service.COINBASE_API_KEY', 'test-key')
    def test_handle_webhook_confirmed(self):
        svc = CryptoService()
        charge = svc.create_charge('u1', 10, 'USD')
        result = svc.handle_webhook('charge:confirmed', {'id': charge['id']})
        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(svc.get_charge(charge['id'])['status'], 'confirmed')

    @patch('services.payment.crypto_service.COINBASE_API_KEY', 'test-key')
    def test_handle_webhook_failed(self):
        svc = CryptoService()
        charge = svc.create_charge('u1', 10, 'USD')
        result = svc.handle_webhook('charge:failed', {'id': charge['id']})
        self.assertEqual(result['status'], 'failed')

    def test_handle_webhook_ignored(self):
        svc = CryptoService()
        result = svc.handle_webhook('charge:pending', {})
        self.assertEqual(result['status'], 'ignored')


if __name__ == '__main__':
    unittest.main()
