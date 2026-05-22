"""supabase_service 단위 테스트 (순수 함수 및 유틸리티)"""
import unittest
from unittest.mock import patch

from services.data.supabase_service import (
    is_supabase_enabled,
    encrypt_api_key,
    decrypt_api_key,
    _is_encryption_enabled,
    _db_operation,
    save_history,
    get_histories,
)


class TestIsSupabaseEnabled(unittest.TestCase):

    def test_always_false(self):
        """현재 구현: 항상 False"""
        self.assertFalse(is_supabase_enabled())


class TestEncryptDecryptApiKey(unittest.TestCase):

    @patch('services.data.supabase_service._is_encryption_enabled', return_value=False)
    def test_encrypt_disabled(self, mock_enc):
        """암호화 비활성 → 원본 반환"""
        result = encrypt_api_key('my-secret-key')
        self.assertEqual(result, 'my-secret-key')

    @patch('services.data.supabase_service._is_encryption_enabled', return_value=False)
    def test_decrypt_disabled(self, mock_enc):
        """암호화 비활성 → 원본 반환"""
        result = decrypt_api_key('my-secret-key')
        self.assertEqual(result, 'my-secret-key')

    def test_encrypt_none(self):
        """None 입력 → None"""
        result = encrypt_api_key(None)
        self.assertIsNone(result)

    def test_encrypt_empty(self):
        """빈 문자열 → None"""
        result = encrypt_api_key('')
        self.assertIsNone(result)

    def test_decrypt_none(self):
        """None 입력 → None"""
        result = decrypt_api_key(None)
        self.assertIsNone(result)

    def test_decrypt_empty(self):
        """빈 문자열 → None"""
        result = decrypt_api_key('')
        self.assertIsNone(result)


class TestIsEncryptionEnabled(unittest.TestCase):

    # Issue #17 소PR A: 인프라 헬퍼가 src.shared.infrastructure.supabase_client로 이전됨.
    # `_encryption_enabled` 모듈 변수는 이제 새 모듈에 있어 patch 경로를 갱신.
    @patch.dict('os.environ', {'ENCRYPTION_SECRET': ''}, clear=False)
    def test_no_secret(self):
        """시크릿 없음 → False"""
        import src.shared.infrastructure.supabase_client as mod
        mod._encryption_enabled = None
        result = _is_encryption_enabled()
        self.assertFalse(result)

    @patch.dict('os.environ', {'ENCRYPTION_SECRET': 'my-secret'}, clear=False)
    def test_with_secret(self):
        """시크릿 있음 → True"""
        import src.shared.infrastructure.supabase_client as mod
        mod._encryption_enabled = None
        result = _is_encryption_enabled()
        self.assertTrue(result)


class TestDbOperation(unittest.TestCase):

    def test_success(self):
        """정상 실행"""
        result = _db_operation('test', 'default', lambda: 'ok')
        self.assertEqual(result, 'ok')

    def test_error(self):
        """예외 → 기본값"""
        result = _db_operation('test', 'fallback', lambda: 1/0)
        self.assertEqual(result, 'fallback')


class TestSaveHistory(unittest.TestCase):

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, mock_sb):
        """클라이언트 없음 → None"""
        result = save_history('user1', {'title': 'test'})
        self.assertIsNone(result)

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, mock_sb):
        """user_id 없음 → None"""
        result = save_history(None, {'title': 'test'})
        self.assertIsNone(result)


class TestGetHistories(unittest.TestCase):

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, mock_sb):
        """클라이언트 없음 → 빈 결과"""
        result = get_histories('user1')
        self.assertEqual(result['histories'], [])
        self.assertEqual(result['total'], 0)

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, mock_sb):
        """user_id 없음 → 빈 결과"""
        result = get_histories(None)
        self.assertEqual(result['histories'], [])


if __name__ == '__main__':
    unittest.main()
