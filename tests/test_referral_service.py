"""referral_service 단위 테스트 (로컬 모드)"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import services.platform.referral_service as referral_mod
from services.platform.referral_service import ReferralService, REFERRAL_REWARD_CREDITS


class TestReferralServiceLocal(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_file = referral_mod._LOCAL_REFERRALS_FILE
        referral_mod._LOCAL_REFERRALS_FILE = os.path.join(self._tmpdir, 'referrals.json')
        self._patch = patch.object(referral_mod, 'is_supabase_enabled', return_value=False)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        referral_mod._LOCAL_REFERRALS_FILE = self._orig_file
        # cleanup
        tmp_file = os.path.join(self._tmpdir, 'referrals.json')
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)
        os.rmdir(self._tmpdir)

    def test_load_local_empty(self):
        """파일 없으면 빈 데이터"""
        data = referral_mod._load_local()
        self.assertEqual(data, {'codes': {}, 'history': []})

    def test_save_and_load(self):
        """저장 후 로드"""
        test_data = {'codes': {'user1': {'code': 'ABC', 'referral_count': 0}}, 'history': []}
        referral_mod._save_local(test_data)
        loaded = referral_mod._load_local()
        self.assertEqual(loaded['codes']['user1']['code'], 'ABC')

    def test_get_or_create_code_new(self):
        """새 사용자 코드 생성"""
        code = ReferralService.get_or_create_code('user_new')
        self.assertIsInstance(code, str)
        self.assertGreater(len(code), 0)

    def test_get_or_create_code_existing(self):
        """기존 코드 반환"""
        code1 = ReferralService.get_or_create_code('user_exist')
        code2 = ReferralService.get_or_create_code('user_exist')
        self.assertEqual(code1, code2)

    def test_get_referral_info(self):
        """추천 정보 조회"""
        ReferralService.get_or_create_code('user_info')
        info = ReferralService.get_referral_info('user_info')
        self.assertIn('code', info)
        self.assertEqual(info['referral_count'], 0)
        self.assertEqual(info['total_earned'], 0)

    def test_apply_referral_invalid_code(self):
        """잘못된 추천 코드 → 실패"""
        result = ReferralService.apply_referral('new_user', 'INVALID_CODE')
        self.assertFalse(result['success'])
        self.assertIn('유효하지 않은', result['error'])

    def test_apply_referral_self(self):
        """본인 추천 코드 → 실패"""
        code = ReferralService.get_or_create_code('self_user')
        result = ReferralService.apply_referral('self_user', code)
        self.assertFalse(result['success'])
        self.assertIn('본인', result['error'])

    @patch('services.usage.credit_service.credit_service')
    def test_apply_referral_success(self, mock_credit):
        """추천 성공"""
        mock_credit.add_credits = MagicMock()
        code = ReferralService.get_or_create_code('referrer')
        result = ReferralService.apply_referral('new_user', code)
        self.assertTrue(result['success'])
        self.assertEqual(result['referrer_id'], 'referrer')
        self.assertEqual(result['credits_given'], REFERRAL_REWARD_CREDITS)

    def test_reward_credits_constant(self):
        """보상 크레딧 상수"""
        self.assertEqual(REFERRAL_REWARD_CREDITS, 5)


if __name__ == '__main__':
    unittest.main()
