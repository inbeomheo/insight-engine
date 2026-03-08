"""Trial Service 테스트"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


class TestTrialService(unittest.TestCase):

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials', return_value={})
    @patch('services.payment.trial_service._save_local_trials')
    def test_start_trial_success(self, mock_save, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        result = TrialService.start_trial('user1')
        self.assertTrue(result['success'])
        self.assertIn('trial_end', result)
        mock_save.assert_called_once()

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    @patch('services.payment.trial_service._save_local_trials')
    def test_start_trial_already_used(self, mock_save, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        existing = {
            'user1': {
                'started': True,
                'trial_end': (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            }
        }
        mock_load.return_value = existing
        result = TrialService.start_trial('user1')
        self.assertFalse(result['success'])
        self.assertTrue(result.get('already_used'))

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_get_trial_not_started(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        mock_load.return_value = {}
        result = TrialService.get_trial('user_new')
        self.assertFalse(result.get('started', False))

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_get_trial_existing(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        trial_data = {
            'user1': {
                'started': True,
                'trial_end': '2026-12-31T00:00:00+00:00',
                'plan': 'pro',
            }
        }
        mock_load.return_value = trial_data
        result = TrialService.get_trial('user1')
        self.assertTrue(result['started'])
        self.assertEqual(result['plan'], 'pro')

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_is_trial_active_true(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        mock_load.return_value = {'user1': {'started': True, 'trial_end': future}}
        self.assertTrue(TrialService.is_trial_active('user1'))

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_is_trial_active_expired(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mock_load.return_value = {'user1': {'started': True, 'trial_end': past}}
        self.assertFalse(TrialService.is_trial_active('user1'))

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_is_trial_active_not_started(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        mock_load.return_value = {}
        self.assertFalse(TrialService.is_trial_active('user_new'))

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_get_remaining_days_active(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        mock_load.return_value = {'user1': {'started': True, 'trial_end': future}}
        remaining = TrialService.get_remaining_days('user1')
        self.assertGreaterEqual(remaining, 4)
        self.assertLessEqual(remaining, 5)

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_get_remaining_days_expired(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_load.return_value = {'user1': {'started': True, 'trial_end': past}}
        self.assertEqual(TrialService.get_remaining_days('user1'), 0)

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_get_remaining_days_not_started(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        mock_load.return_value = {}
        self.assertEqual(TrialService.get_remaining_days('user_new'), 0)

    @patch('services.payment.trial_service.is_supabase_enabled', return_value=False)
    @patch('services.payment.trial_service._load_local_trials')
    def test_is_trial_active_invalid_date(self, mock_load, mock_supa):
        from services.payment.trial_service import TrialService
        mock_load.return_value = {'user1': {'started': True, 'trial_end': 'invalid'}}
        self.assertFalse(TrialService.is_trial_active('user1'))


if __name__ == '__main__':
    unittest.main()
