"""
HybridBillingService 단위 테스트 (F4-11)
"""
import unittest
from services.payment.hybrid_billing_service import HybridBillingService


class TestHybridBillingService(unittest.TestCase):

    def setUp(self):
        self.svc = HybridBillingService()

    def test_setup_and_consume_within_base(self):
        self.svc.setup_account('u1', base_credits=10, overage_rate=100)
        result = self.svc.consume('u1', 5)
        self.assertEqual(result['base_remaining'], 5)
        self.assertEqual(result['overage_count'], 0)
        self.assertEqual(result['overage_charges'], 0)

    def test_overage_charges(self):
        self.svc.setup_account('u1', base_credits=5, overage_rate=200)
        self.svc.consume('u1', 5)  # 기본 소진
        result = self.svc.consume('u1', 3)  # 3건 초과
        self.assertEqual(result['overage_count'], 3)
        self.assertEqual(result['overage_charges'], 600)

    def test_consume_no_account(self):
        result = self.svc.consume('no-user')
        self.assertIn('error', result)

    def test_billing_summary(self):
        self.svc.setup_account('u1', base_credits=10, overage_rate=100)
        self.svc.consume('u1', 12)
        summary = self.svc.get_billing_summary('u1')
        self.assertEqual(summary['overage_count'], 2)
        self.assertEqual(summary['overage_charges'], 200)

    def test_reset_monthly(self):
        self.svc.setup_account('u1', base_credits=10, overage_rate=100)
        self.svc.consume('u1', 8)
        self.svc.reset_monthly('u1')
        summary = self.svc.get_billing_summary('u1')
        self.assertEqual(summary['used'], 0)
        self.assertEqual(summary['base_remaining'], 10)


if __name__ == '__main__':
    unittest.main()
