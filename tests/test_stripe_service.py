"""Stripe Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.payment.stripe_service import StripeService, _get_stripe


class TestStripeService(unittest.TestCase):

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', '')
    def test_is_enabled_false(self):
        self.assertFalse(StripeService.is_enabled())

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_is_enabled_true(self):
        self.assertTrue(StripeService.is_enabled())

    def test_get_stripe_no_module(self):
        with patch.dict('sys.modules', {'stripe': None}):
            result = _get_stripe()
            # ImportError 시 None 반환
            self.assertIsNone(result)

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', '')
    def test_create_checkout_no_stripe(self):
        with patch('services.payment.stripe_service._get_stripe', return_value=None):
            result = StripeService.create_checkout_session('user1', 'price_xxx')
            self.assertIn('error', result)

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_create_checkout_success(self):
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_123'
        mock_stripe.checkout.Session.create.return_value = mock_session

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            result = StripeService.create_checkout_session('user1', 'price_xxx')
            self.assertEqual(result['session_id'], 'cs_test_123')
            self.assertIn('url', result)

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_create_checkout_exception(self):
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.side_effect = Exception('Stripe API error')

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            result = StripeService.create_checkout_session('user1', 'price_xxx')
            self.assertIn('error', result)

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_create_checkout_custom_urls(self):
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.id = 'cs_test_456'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_456'
        mock_stripe.checkout.Session.create.return_value = mock_session

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            result = StripeService.create_checkout_session(
                'user1', 'price_xxx',
                success_url='https://app.com/ok',
                cancel_url='https://app.com/cancel',
            )
            self.assertEqual(result['session_id'], 'cs_test_456')
            call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
            self.assertEqual(call_kwargs['success_url'], 'https://app.com/ok')
            self.assertEqual(call_kwargs['cancel_url'], 'https://app.com/cancel')

    def test_handle_webhook_no_stripe(self):
        with patch('services.payment.stripe_service._get_stripe', return_value=None):
            result = StripeService.handle_webhook(b'payload', 'sig_header')
            self.assertFalse(result['success'])

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_handle_webhook_success(self):
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = {
            'type': 'checkout.session.completed',
            'data': {'object': {'client_reference_id': 'user1', 'mode': 'subscription', 'subscription': 'sub_1'}},
        }

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            with patch('services.payment.stripe_service._handle_checkout_completed'):
                result = StripeService.handle_webhook(b'payload', 'sig')
                self.assertTrue(result['success'])
                self.assertEqual(result['event_type'], 'checkout.session.completed')

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_handle_webhook_signature_error(self):
        mock_stripe = MagicMock()
        mock_stripe.error.SignatureVerificationError = type('SignatureVerificationError', (Exception,), {})
        mock_stripe.Webhook.construct_event.side_effect = mock_stripe.error.SignatureVerificationError('bad sig')

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            result = StripeService.handle_webhook(b'payload', 'bad_sig')
            self.assertFalse(result['success'])

    @patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx')
    def test_create_checkout_payment_mode(self):
        mock_stripe = MagicMock()
        mock_session = MagicMock()
        mock_session.id = 'cs_pay_789'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_pay_789'
        mock_stripe.checkout.Session.create.return_value = mock_session

        with patch('services.payment.stripe_service._get_stripe', return_value=mock_stripe):
            result = StripeService.create_checkout_session('user1', 'price_xxx', mode='payment')
            self.assertEqual(result['session_id'], 'cs_pay_789')
            call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
            self.assertEqual(call_kwargs['mode'], 'payment')


if __name__ == '__main__':
    unittest.main()
