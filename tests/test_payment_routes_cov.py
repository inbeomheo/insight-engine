"""payment_routes.py 커버리지 보강 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}
_SB_PATCH = 'services.data.supabase_service.is_supabase_enabled'


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


class TestCredits(_Base):
    """크레딧 API (F4-01)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.usage.credit_service.credit_service')
    def test_get_balance(self, mock_cs, _):
        mock_cs.get_balance.return_value = {'credits': 100}
        resp = self.client.get('/api/credits/balance', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_purchase_credits_no_price_id(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        resp = self.client.post('/api/credits/purchase', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_purchase_credits_disabled(self, mock_ss, _):
        mock_ss.is_enabled.return_value = False
        resp = self.client.post('/api/credits/purchase', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 503)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_purchase_credits_success(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.return_value = {'url': 'https://checkout.stripe.com/xxx'}
        resp = self.client.post('/api/credits/purchase', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_purchase_credits_error(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.return_value = {'error': '결제 실패'}
        resp = self.client.post('/api/credits/purchase', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_purchase_credits_exception(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.side_effect = Exception('boom')
        resp = self.client.post('/api/credits/purchase', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.usage.credit_plan.get_all_plans', return_value=[{'id': 'free', 'credits': 10}])
    def test_get_credit_plans(self, _m1, _):
        resp = self.client.get('/api/credits/plans', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestStripeCheckout(_Base):
    """Stripe 결제 API (F4-02)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_checkout_disabled(self, mock_ss, _):
        mock_ss.is_enabled.return_value = False
        resp = self.client.post('/api/payment/checkout', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 503)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_checkout_no_price_id(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        resp = self.client.post('/api/payment/checkout', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_checkout_success(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.return_value = {'url': 'https://stripe.com'}
        resp = self.client.post('/api/payment/checkout', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_checkout_error_result(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.return_value = {'error': 'fail'}
        resp = self.client.post('/api/payment/checkout', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_checkout_exception(self, mock_ss, _):
        mock_ss.is_enabled.return_value = True
        mock_ss.create_checkout_session.side_effect = Exception('e')
        resp = self.client.post('/api/payment/checkout', json={'price_id': 'p1'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestStripeWebhook(_Base):
    """Stripe Webhook."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_webhook_success(self, mock_ss, _):
        mock_ss.handle_webhook.return_value = {'success': True}
        resp = self.client.post('/api/payment/webhook', data=b'payload',
                                headers={'Stripe-Signature': 'sig'})
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_webhook_signature_fail(self, mock_ss, _):
        mock_ss.handle_webhook.return_value = {'success': False, 'error': '서명 검증 실패'}
        resp = self.client.post('/api/payment/webhook', data=b'payload',
                                headers={**_H, 'Stripe-Signature': 'bad'})
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_webhook_exception(self, mock_ss, _):
        mock_ss.handle_webhook.side_effect = Exception('boom')
        resp = self.client.post('/api/payment/webhook', data=b'x',
                                headers={**_H, 'Stripe-Signature': 's'})
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.stripe_service.stripe_service')
    def test_webhook_generic_failure(self, mock_ss, _):
        mock_ss.handle_webhook.return_value = {'success': False, 'error': 'unknown error'}
        resp = self.client.post('/api/payment/webhook', data=b'x',
                                headers={**_H, 'Stripe-Signature': 's'})
        self.assertEqual(resp.status_code, 400)


class TestSubscription(_Base):
    """구독 API (F4-03)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_get_subscription(self, mock_ss, _):
        mock_ss.get_subscription.return_value = {'plan': 'free'}
        resp = self.client.get('/api/subscription', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_get_subscription_error(self, mock_ss, _):
        mock_ss.get_subscription.side_effect = Exception('e')
        resp = self.client.get('/api/subscription', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_upgrade_success(self, mock_ss, _):
        mock_ss.upgrade.return_value = {'success': True}
        resp = self.client.post('/api/subscription/upgrade', json={'plan': 'pro'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_upgrade_failure(self, mock_ss, _):
        mock_ss.upgrade.return_value = {'success': False, 'error': 'insufficient'}
        resp = self.client.post('/api/subscription/upgrade', json={'plan': 'pro'}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_upgrade_exception(self, mock_ss, _):
        mock_ss.upgrade.side_effect = Exception('e')
        resp = self.client.post('/api/subscription/upgrade', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_cancel_success(self, mock_ss, _):
        mock_ss.cancel.return_value = {'success': True}
        resp = self.client.post('/api/subscription/cancel', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_cancel_failure(self, mock_ss, _):
        mock_ss.cancel.return_value = {'success': False, 'error': 'no sub'}
        resp = self.client.post('/api/subscription/cancel', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    def test_cancel_exception(self, mock_ss, _):
        mock_ss.cancel.side_effect = Exception('e')
        resp = self.client.post('/api/subscription/cancel', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestTrial(_Base):
    """무료 체험 API (F4-04)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_start_trial_success(self, mock_ts, _):
        mock_ts.start_trial.return_value = {'success': True}
        resp = self.client.post('/api/trial/start', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_start_trial_already_used(self, mock_ts, _):
        mock_ts.start_trial.return_value = {'success': False, 'already_used': True}
        resp = self.client.post('/api/trial/start', json={}, headers=_H)
        self.assertEqual(resp.status_code, 409)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_start_trial_failure(self, mock_ts, _):
        mock_ts.start_trial.return_value = {'success': False, 'error': 'err'}
        resp = self.client.post('/api/trial/start', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_start_trial_exception(self, mock_ts, _):
        mock_ts.start_trial.side_effect = Exception('e')
        resp = self.client.post('/api/trial/start', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_get_trial_status(self, mock_ts, _):
        mock_ts.get_trial.return_value = {'trial_end': '2030-01-01'}
        mock_ts.is_trial_active.return_value = True
        mock_ts.get_remaining_days.return_value = 5
        resp = self.client.get('/api/trial/status', headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['active'])
        self.assertEqual(data['remaining_days'], 5)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.trial_service.trial_service')
    def test_get_trial_status_exception(self, mock_ts, _):
        mock_ts.get_trial.side_effect = Exception('e')
        resp = self.client.get('/api/trial/status', headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestMyUsage(_Base):
    """사용량 대시보드 (F4-05)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    @patch('services.usage.usage_service.UsageService')
    @patch('services.usage.credit_service.credit_service')
    def test_get_my_usage(self, mock_cs, mock_us, mock_ss, _):
        mock_cs.get_balance.return_value = {'credits': 50}
        mock_us.get_current.return_value = {'used': 5}
        mock_ss.get_subscription.return_value = {'plan': 'free'}
        resp = self.client.get('/api/usage/my-usage', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.subscription_service.subscription_service')
    @patch('services.usage.usage_service.UsageService')
    @patch('services.usage.credit_service.credit_service')
    def test_get_my_usage_error(self, mock_cs, mock_us, mock_ss, _):
        mock_cs.get_balance.side_effect = Exception('e')
        resp = self.client.get('/api/usage/my-usage', headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestReferral(_Base):
    """레퍼럴 API (F4-06)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.referral_service.referral_service')
    def test_get_referral_info(self, mock_rs, _):
        mock_rs.get_referral_info.return_value = {'code': 'ABC123'}
        resp = self.client.get('/api/referral/info', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.referral_service.referral_service')
    def test_get_referral_info_error(self, mock_rs, _):
        mock_rs.get_referral_info.side_effect = Exception('e')
        resp = self.client.get('/api/referral/info', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    def test_apply_referral_no_code(self, _):
        resp = self.client.post('/api/referral/apply', json={'code': ''}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.referral_service.referral_service')
    def test_apply_referral_success(self, mock_rs, _):
        mock_rs.apply_referral.return_value = {'success': True}
        resp = self.client.post('/api/referral/apply', json={'code': 'ABC'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.referral_service.referral_service')
    def test_apply_referral_failure(self, mock_rs, _):
        mock_rs.apply_referral.return_value = {'success': False, 'error': 'invalid'}
        resp = self.client.post('/api/referral/apply', json={'code': 'BAD'}, headers=_H)
        self.assertEqual(resp.status_code, 400)


class TestApiKeys(_Base):
    """API 키 관리 (F4-07)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_list_keys(self, mock_aks, _):
        mock_aks.list_keys.return_value = []
        resp = self.client.get('/api/keys', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_list_keys_error(self, mock_aks, _):
        mock_aks.list_keys.side_effect = Exception('e')
        resp = self.client.get('/api/keys', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_create_key_success(self, mock_aks, _):
        mock_aks.create_key.return_value = {'key': 'ie_xxx', 'name': 'test'}
        resp = self.client.post('/api/keys', json={'name': 'test'}, headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_create_key_error(self, mock_aks, _):
        mock_aks.create_key.return_value = {'error': 'limit reached'}
        resp = self.client.post('/api/keys', json={'name': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_create_key_exception(self, mock_aks, _):
        mock_aks.create_key.side_effect = Exception('e')
        resp = self.client.post('/api/keys', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_revoke_key_success(self, mock_aks, _):
        mock_aks.revoke_key.return_value = True
        resp = self.client.delete('/api/keys/k1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.api_key_service.api_key_service')
    def test_revoke_key_fail(self, mock_aks, _):
        mock_aks.revoke_key.return_value = False
        resp = self.client.delete('/api/keys/k1', headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestInvoices(_Base):
    """인보이스 API (F4-10)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_list_invoices(self, mock_is, _):
        mock_is.list_invoices.return_value = []
        resp = self.client.get('/api/invoices', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_list_invoices_error(self, mock_is, _):
        mock_is.list_invoices.side_effect = Exception('e')
        resp = self.client.get('/api/invoices', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    def test_create_invoice_no_items(self, _):
        resp = self.client.post('/api/invoices', json={'items': []}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_create_invoice_success(self, mock_is, _):
        mock_is.create_invoice.return_value = {'id': 'inv1'}
        resp = self.client.post('/api/invoices', json={'items': [{'name': 'x', 'amount': 100}]}, headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_create_invoice_error_result(self, mock_is, _):
        mock_is.create_invoice.return_value = {'error': 'bad'}
        resp = self.client.post('/api/invoices', json={'items': [{'name': 'x'}]}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_pay_invoice(self, mock_is, _):
        mock_is.mark_paid.return_value = {'paid': True}
        resp = self.client.post('/api/invoices/inv1/pay', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.invoice_service.invoice_service')
    def test_pay_invoice_not_found(self, mock_is, _):
        mock_is.mark_paid.return_value = {'error': 'not found'}
        resp = self.client.post('/api/invoices/bad/pay', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)


class TestCoupons(_Base):
    """쿠폰 API (F4-12)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_list_coupons(self, mock_cs, _):
        mock_cs.list_coupons.return_value = []
        resp = self.client.get('/api/coupons', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_create_coupon_success(self, mock_cs, _):
        mock_cs.create_coupon.return_value = {'code': 'SAVE10'}
        resp = self.client.post('/api/coupons', json={'code': 'SAVE10'}, headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_create_coupon_error(self, mock_cs, _):
        mock_cs.create_coupon.return_value = {'error': 'dup'}
        resp = self.client.post('/api/coupons', json={'code': 'SAVE10'}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    def test_validate_coupon_no_code(self, _):
        resp = self.client.post('/api/coupons/validate', json={'code': ''}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_validate_coupon_success(self, mock_cs, _):
        mock_cs.validate_coupon.return_value = {'valid': True}
        resp = self.client.post('/api/coupons/validate', json={'code': 'SAVE10'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    def test_redeem_coupon_no_amount(self, _):
        resp = self.client.post('/api/coupons/redeem', json={'code': 'SAVE10', 'amount': 0}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_redeem_coupon_success(self, mock_cs, _):
        mock_cs.redeem_coupon.return_value = {'discounted_amount': 90}
        resp = self.client.post('/api/coupons/redeem', json={'code': 'SAVE10', 'amount': 100}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.coupon_service.coupon_service')
    def test_redeem_coupon_error(self, mock_cs, _):
        mock_cs.redeem_coupon.return_value = {'error': 'expired'}
        resp = self.client.post('/api/coupons/redeem', json={'code': 'OLD', 'amount': 100}, headers=_H)
        self.assertEqual(resp.status_code, 400)


class TestTeamBilling(_Base):
    """팀 과금 API (F4-08)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.team_billing_service.team_billing_service')
    def test_get_team_billing(self, mock_tbs, _):
        mock_tbs.get_team_usage.return_value = {'total': 100}
        resp = self.client.get('/api/team-billing/t1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.team_billing_service.team_billing_service')
    def test_get_team_billing_error(self, mock_tbs, _):
        mock_tbs.get_team_usage.return_value = {'error': 'not found'}
        resp = self.client.get('/api/team-billing/bad', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.team_billing_service.team_billing_service')
    def test_get_team_member_usage(self, mock_tbs, _):
        mock_tbs.get_member_usage.return_value = []
        resp = self.client.get('/api/team-billing/t1/members', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.team_billing_service.team_billing_service')
    def test_get_team_member_usage_error(self, mock_tbs, _):
        mock_tbs.get_member_usage.side_effect = Exception('e')
        resp = self.client.get('/api/team-billing/t1/members', headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestHybridBilling(_Base):
    """하이브리드 과금 API (F4-11)."""

    @patch(_SB_PATCH, return_value=False)
    def test_billing_setup_missing_params(self, _):
        resp = self.client.post('/api/billing/setup', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_setup_success(self, mock_hbs, _):
        mock_hbs.setup_account.return_value = {'ok': True}
        resp = self.client.post('/api/billing/setup',
                                json={'base_credits': 100, 'overage_rate': 0.1}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_consume_success(self, mock_hbs, _):
        mock_hbs.consume.return_value = {'remaining': 99}
        resp = self.client.post('/api/billing/consume', json={'amount': 1}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_consume_error(self, mock_hbs, _):
        mock_hbs.consume.return_value = {'error': 'no credits'}
        resp = self.client.post('/api/billing/consume', json={'amount': 1}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_summary(self, mock_hbs, _):
        mock_hbs.get_billing_summary.return_value = {'total': 100}
        resp = self.client.get('/api/billing/summary', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_summary_error(self, mock_hbs, _):
        mock_hbs.get_billing_summary.return_value = {'error': 'not found'}
        resp = self.client.get('/api/billing/summary', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_reset_monthly(self, mock_hbs, _):
        mock_hbs.reset_monthly.return_value = {'reset': True}
        resp = self.client.post('/api/billing/reset-monthly', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.hybrid_billing_service.hybrid_billing_service')
    def test_billing_reset_monthly_error(self, mock_hbs, _):
        mock_hbs.reset_monthly.return_value = {'error': 'not found'}
        resp = self.client.post('/api/billing/reset-monthly', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)


class TestCrypto(_Base):
    """암호화폐 결제 API (F4-17)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_charge_not_configured(self, mock_cs, _):
        mock_cs.is_configured = False
        resp = self.client.post('/api/crypto/charge', json={'amount': 10}, headers=_H)
        self.assertEqual(resp.status_code, 503)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_charge_no_amount(self, mock_cs, _):
        mock_cs.is_configured = True
        resp = self.client.post('/api/crypto/charge', json={'amount': 0}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_charge_success(self, mock_cs, _):
        mock_cs.is_configured = True
        mock_cs.create_charge.return_value = {'charge_id': 'ch1'}
        resp = self.client.post('/api/crypto/charge', json={'amount': 10}, headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_get_charge_found(self, mock_cs, _):
        mock_cs.get_charge.return_value = {'id': 'ch1', 'status': 'pending'}
        resp = self.client.get('/api/crypto/charge/ch1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_get_charge_not_found(self, mock_cs, _):
        mock_cs.get_charge.return_value = None
        resp = self.client.get('/api/crypto/charge/bad', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_webhook_verify_fail(self, mock_cs, _):
        mock_cs.verify_webhook.return_value = False
        resp = self.client.post('/api/crypto/webhook', data=b'x',
                                headers={**_H, 'X-CC-Webhook-Signature': 'bad'})
        self.assertEqual(resp.status_code, 401)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.crypto_service.crypto_service')
    def test_crypto_webhook_success(self, mock_cs, _):
        mock_cs.verify_webhook.return_value = True
        mock_cs.handle_webhook.return_value = {'ok': True}
        resp = self.client.post('/api/crypto/webhook',
                                data=b'{"type":"charge:confirmed","data":{}}',
                                content_type='application/json',
                                headers={'X-CC-Webhook-Signature': 'good'})
        self.assertEqual(resp.status_code, 200)


class TestPaddle(_Base):
    """Paddle 결제 API (F4-16)."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_status(self, mock_ps, _):
        mock_ps.is_configured = True
        resp = self.client.get('/api/paddle/status', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_webhook_verify_fail(self, mock_ps, _):
        mock_ps.verify_webhook.return_value = False
        resp = self.client.post('/api/paddle/webhook', data=b'x',
                                headers={**_H, 'Paddle-Signature': 'bad'})
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_webhook_success(self, mock_ps, _):
        mock_ps.verify_webhook.return_value = True
        mock_ps.handle_webhook.return_value = {'ok': True}
        resp = self.client.post('/api/paddle/webhook',
                                data=b'{"event_type":"subscription.created","data":{}}',
                                content_type='application/json',
                                headers={'Paddle-Signature': 'good'})
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_get_subscription_found(self, mock_ps, _):
        mock_ps.get_subscription.return_value = {'id': 's1'}
        resp = self.client.get('/api/paddle/subscription/s1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.payment.paddle_service.paddle_service')
    def test_paddle_get_subscription_not_found(self, mock_ps, _):
        mock_ps.get_subscription.return_value = None
        resp = self.client.get('/api/paddle/subscription/bad', headers=_H)
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
