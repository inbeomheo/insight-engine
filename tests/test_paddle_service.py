"""
PaddleService 단위 테스트 (F4-16)
"""
import unittest
from services.payment.paddle_service import PaddleService


class TestPaddleService(unittest.TestCase):

    def setUp(self):
        self.svc = PaddleService()

    def test_handle_subscription_created(self):
        data = {'subscription_id': 'sub-1', 'customer_id': 'cust-1', 'plan_id': 'plan-pro'}
        result = self.svc.handle_webhook('subscription.created', data)
        self.assertEqual(result['status'], 'created')
        sub = self.svc.get_subscription('sub-1')
        self.assertEqual(sub['status'], 'active')

    def test_handle_subscription_canceled(self):
        self.svc.handle_webhook('subscription.created', {'subscription_id': 'sub-1'})
        result = self.svc.handle_webhook('subscription.canceled', {'subscription_id': 'sub-1'})
        self.assertEqual(result['status'], 'canceled')
        sub = self.svc.get_subscription('sub-1')
        self.assertEqual(sub['status'], 'canceled')

    def test_handle_unknown_event(self):
        result = self.svc.handle_webhook('unknown.event', {})
        self.assertEqual(result['status'], 'ignored')

    def test_get_subscription_not_found(self):
        self.assertIsNone(self.svc.get_subscription('nope'))


if __name__ == '__main__':
    unittest.main()
