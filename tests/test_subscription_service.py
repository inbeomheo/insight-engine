"""Subscription Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestSubscriptionService(unittest.TestCase):

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs', return_value={})
    def test_get_subscription_default_free(self, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        result = SubscriptionService.get_subscription('user_new')
        self.assertEqual(result['plan'], 'free')
        self.assertEqual(result['status'], 'active')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs')
    def test_get_subscription_existing(self, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        mock_load.return_value = {
            'user1': {'plan': 'pro', 'status': 'active', 'stripe_subscription_id': 'sub_123'}
        }
        result = SubscriptionService.get_subscription('user1')
        self.assertEqual(result['plan'], 'pro')
        self.assertEqual(result['stripe_subscription_id'], 'sub_123')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs', return_value={})
    @patch('services.payment.subscription_service._save_local_subs')
    def test_activate_success(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        result = SubscriptionService.activate('user1', 'sub_123', 'pro')
        self.assertTrue(result['success'])
        self.assertEqual(result['plan'], 'pro')
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved['user1']['plan'], 'pro')
        self.assertEqual(saved['user1']['status'], 'active')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs', return_value={})
    @patch('services.payment.subscription_service._save_local_subs')
    def test_activate_enterprise_plan(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        result = SubscriptionService.activate('user2', 'sub_456', 'enterprise')
        self.assertTrue(result['success'])
        self.assertEqual(result['plan'], 'enterprise')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs')
    @patch('services.payment.subscription_service._save_local_subs')
    def test_cancel_success(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        mock_load.return_value = {
            'user1': {'plan': 'pro', 'status': 'active'}
        }
        result = SubscriptionService.cancel('user1')
        self.assertTrue(result['success'])
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved['user1']['plan'], 'free')
        self.assertEqual(saved['user1']['status'], 'canceled')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs')
    @patch('services.payment.subscription_service._save_local_subs')
    def test_cancel_includes_timestamp(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        mock_load.return_value = {}
        SubscriptionService.cancel('user1')
        saved = mock_save.call_args[0][0]
        self.assertIn('canceled_at', saved['user1'])
        self.assertIn('updated_at', saved['user1'])

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs')
    @patch('services.payment.subscription_service._save_local_subs')
    def test_downgrade_delegates_to_activate(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        mock_load.return_value = {
            'user1': {
                'plan': 'pro', 'status': 'active',
                'stripe_subscription_id': None,
            }
        }
        result = SubscriptionService.downgrade('user1', 'free')
        self.assertTrue(result['success'])
        self.assertEqual(result['plan'], 'free')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs')
    @patch('services.payment.subscription_service._save_local_subs')
    def test_upgrade_without_stripe(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        mock_load.return_value = {
            'user1': {
                'plan': 'free', 'status': 'active',
                'stripe_subscription_id': None,
            }
        }
        result = SubscriptionService.upgrade('user1', 'pro')
        self.assertTrue(result['success'])
        self.assertEqual(result['plan'], 'pro')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs', return_value={})
    @patch('services.payment.subscription_service._save_local_subs')
    def test_activate_stores_stripe_id(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        SubscriptionService.activate('user1', 'sub_xyz', 'pro')
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved['user1']['stripe_subscription_id'], 'sub_xyz')

    @patch('services.payment.subscription_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.subscription_service._load_local_subs', return_value={})
    @patch('services.payment.subscription_service._save_local_subs')
    def test_activate_includes_timestamps(self, mock_save, mock_load, mock_supa):
        from services.payment.subscription_service import SubscriptionService
        SubscriptionService.activate('user1', 'sub_1', 'pro')
        saved = mock_save.call_args[0][0]
        self.assertIn('activated_at', saved['user1'])
        self.assertIn('updated_at', saved['user1'])


if __name__ == '__main__':
    unittest.main()
