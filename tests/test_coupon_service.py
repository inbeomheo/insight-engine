"""
CouponService 단위 테스트 (F4-12)
"""
import unittest
from services.payment.coupon_service import CouponService


class TestCouponService(unittest.TestCase):

    def setUp(self):
        self.svc = CouponService()

    def test_create_coupon(self):
        result = self.svc.create_coupon(code='TEST10', discount_type='percentage', discount_value=10)
        self.assertEqual(result['code'], 'TEST10')
        self.assertTrue(result['is_active'])

    def test_create_auto_code(self):
        result = self.svc.create_coupon()
        self.assertTrue(result['code'].startswith('COUP-'))

    def test_create_duplicate_rejected(self):
        self.svc.create_coupon(code='DUP')
        result = self.svc.create_coupon(code='DUP')
        self.assertIn('error', result)

    def test_invalid_discount_type(self):
        result = self.svc.create_coupon(discount_type='invalid')
        self.assertIn('error', result)

    def test_percentage_over_100_rejected(self):
        result = self.svc.create_coupon(discount_type='percentage', discount_value=150)
        self.assertIn('error', result)

    def test_validate_valid_coupon(self):
        self.svc.create_coupon(code='VALID')
        result = self.svc.validate_coupon('VALID')
        self.assertTrue(result['valid'])

    def test_validate_nonexistent(self):
        result = self.svc.validate_coupon('NONE')
        self.assertFalse(result['valid'])

    def test_validate_deactivated(self):
        self.svc.create_coupon(code='OFF')
        self.svc.deactivate_coupon('OFF')
        result = self.svc.validate_coupon('OFF')
        self.assertFalse(result['valid'])

    def test_redeem_percentage(self):
        self.svc.create_coupon(code='P10', discount_type='percentage', discount_value=10)
        result = self.svc.redeem_coupon('P10', 'user-1', 10000)
        self.assertEqual(result['discount'], 1000)
        self.assertEqual(result['final'], 9000)

    def test_redeem_fixed(self):
        self.svc.create_coupon(code='F500', discount_type='fixed', discount_value=500)
        result = self.svc.redeem_coupon('F500', 'user-1', 1000)
        self.assertEqual(result['discount'], 500)

    def test_redeem_max_uses(self):
        self.svc.create_coupon(code='ONE', max_uses=1)
        self.svc.redeem_coupon('ONE', 'u1', 1000)
        result = self.svc.redeem_coupon('ONE', 'u2', 1000)
        self.assertIn('error', result)

    def test_list_coupons(self):
        self.svc.create_coupon(code='A')
        self.svc.create_coupon(code='B')
        self.assertEqual(len(self.svc.list_coupons()), 2)


if __name__ == '__main__':
    unittest.main()
