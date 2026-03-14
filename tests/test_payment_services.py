"""결제 서비스 단위 테스트 (Stripe, 구독, 체험)"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone


@pytest.fixture(autouse=True)
def mock_supabase_disabled():
    with patch('services.supabase_service.is_supabase_enabled', return_value=False):
        yield


class TestStripeService:
    def test_is_enabled_without_key(self):
        with patch('services.payment.stripe_service.STRIPE_SECRET_KEY', ''):
            from services.payment.stripe_service import StripeService
            assert StripeService.is_enabled() is False

    def test_is_enabled_with_key(self):
        with patch('services.payment.stripe_service.STRIPE_SECRET_KEY', 'sk_test_xxx'):
            from services.payment.stripe_service import StripeService
            assert StripeService.is_enabled() is True

    def test_create_checkout_no_stripe_module(self):
        """stripe 모듈 미설치 시 에러 반환"""
        with patch('services.payment.stripe_service._get_stripe', return_value=None):
            from services.payment.stripe_service import StripeService
            result = StripeService.create_checkout_session('user-1', 'price_123')
            assert 'error' in result


class TestSubscriptionService:
    @pytest.fixture
    def tmp_subs_file(self, tmp_path):
        f = tmp_path / 'subscriptions.json'
        f.write_text('{}', encoding='utf-8')
        with patch('services.payment.subscription_service._LOCAL_SUBS_FILE', str(f)):
            yield f

    def test_get_default_subscription(self, tmp_subs_file):
        from services.payment.subscription_service import SubscriptionService
        sub = SubscriptionService.get_subscription('user-123')
        assert sub['plan'] == 'free'
        assert sub['status'] == 'active'

    def test_activate_subscription(self, tmp_subs_file):
        from services.payment.subscription_service import SubscriptionService
        result = SubscriptionService.activate('user-123', 'sub_xxx', 'pro')
        assert result['success'] is True
        assert result['plan'] == 'pro'

        # 확인
        sub = SubscriptionService.get_subscription('user-123')
        assert sub['plan'] == 'pro'
        assert sub['status'] == 'active'

    def test_cancel_subscription(self, tmp_subs_file):
        from services.payment.subscription_service import SubscriptionService
        SubscriptionService.activate('user-123', 'sub_xxx', 'pro')
        result = SubscriptionService.cancel('user-123')
        assert result['success'] is True

        sub = SubscriptionService.get_subscription('user-123')
        assert sub['plan'] == 'free'
        assert sub['status'] == 'canceled'


class TestTrialService:
    @pytest.fixture
    def tmp_trials_file(self, tmp_path):
        f = tmp_path / 'trials.json'
        f.write_text('{}', encoding='utf-8')
        with patch('services.payment.trial_service._LOCAL_TRIALS_FILE', str(f)):
            yield f

    def test_start_trial(self, tmp_trials_file):
        from services.payment.trial_service import TrialService
        result = TrialService.start_trial('user-123')
        assert result['success'] is True
        assert 'trial_end' in result

    def test_start_trial_twice_fails(self, tmp_trials_file):
        from services.payment.trial_service import TrialService
        TrialService.start_trial('user-123')
        result = TrialService.start_trial('user-123')
        assert result['success'] is False
        assert result.get('already_used') is True

    def test_is_trial_active(self, tmp_trials_file):
        from services.payment.trial_service import TrialService
        TrialService.start_trial('user-123')
        assert TrialService.is_trial_active('user-123') is True

    def test_remaining_days(self, tmp_trials_file):
        from services.payment.trial_service import TrialService
        TrialService.start_trial('user-123')
        days = TrialService.get_remaining_days('user-123')
        assert 6 <= days <= 7  # 시작 직후이므로 6~7일


class TestReferralService:
    @pytest.fixture
    def tmp_referrals_file(self, tmp_path):
        f = tmp_path / 'referrals.json'
        f.write_text('{"codes": {}, "history": []}', encoding='utf-8')
        with patch('services.referral_service._LOCAL_REFERRALS_FILE', str(f)):
            yield f

    def test_get_or_create_code(self, tmp_referrals_file):
        from services.platform.referral_service import ReferralService
        code1 = ReferralService.get_or_create_code('user-123')
        code2 = ReferralService.get_or_create_code('user-123')
        assert code1 == code2  # 동일 코드 반환
        assert len(code1) > 0

    def test_apply_referral(self, tmp_referrals_file):
        from services.platform.referral_service import ReferralService
        # 크레딧 파일도 임시로 설정
        with patch('services.usage.credit_service._LOCAL_CREDITS_FILE',
                    str(tmp_referrals_file.parent / 'credits.json')):
            code = ReferralService.get_or_create_code('referrer-1')
            result = ReferralService.apply_referral('new-user-1', code)
            assert result['success'] is True
            assert result['credits_given'] == 5

    def test_apply_invalid_code(self, tmp_referrals_file):
        from services.platform.referral_service import ReferralService
        result = ReferralService.apply_referral('new-user-1', 'invalid-code')
        assert result['success'] is False

    def test_apply_own_code_rejected(self, tmp_referrals_file):
        from services.platform.referral_service import ReferralService
        code = ReferralService.get_or_create_code('user-123')
        result = ReferralService.apply_referral('user-123', code)
        assert result['success'] is False


class TestApiKeyService:
    @pytest.fixture
    def tmp_keys_file(self, tmp_path):
        f = tmp_path / 'user_api_keys.json'
        f.write_text('{}', encoding='utf-8')
        with patch('services.api_key_service._LOCAL_API_KEYS_FILE', str(f)):
            yield f

    def test_create_key(self, tmp_keys_file):
        from services.data.api_key_service import ApiKeyService
        result = ApiKeyService.create_key('user-123', 'test-key')
        assert 'key' in result
        assert result['key'].startswith('ie_')
        assert result['name'] == 'test-key'

    def test_list_keys(self, tmp_keys_file):
        from services.data.api_key_service import ApiKeyService
        ApiKeyService.create_key('user-123', 'key-1')
        ApiKeyService.create_key('user-123', 'key-2')
        keys = ApiKeyService.list_keys('user-123')
        assert len(keys) == 2

    def test_revoke_key(self, tmp_keys_file):
        from services.data.api_key_service import ApiKeyService
        result = ApiKeyService.create_key('user-123', 'to-revoke')
        key_id = result['key_id']
        assert ApiKeyService.revoke_key('user-123', key_id) is True
        keys = ApiKeyService.list_keys('user-123')
        assert len(keys) == 0

    def test_validate_key(self, tmp_keys_file):
        from services.data.api_key_service import ApiKeyService
        result = ApiKeyService.create_key('user-123', 'valid-key')
        raw_key = result['key']

        validated = ApiKeyService.validate_key(raw_key)
        assert validated is not None
        assert validated['user_id'] == 'user-123'

    def test_validate_invalid_key(self, tmp_keys_file):
        from services.data.api_key_service import ApiKeyService
        result = ApiKeyService.validate_key('ie_invalid_key_xxx')
        assert result is None
