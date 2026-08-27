"""supabase_service 확장 테스트 — CRUD, 사용량, 관리자, 암호화 등 미커버 함수"""
import unittest
from unittest.mock import patch, MagicMock


class TestSupabaseClientLifetime(unittest.TestCase):
    """인증 세션을 바꾸는 요청은 전역 클라이언트를 공유하지 않는다."""

    @patch.dict(
        'os.environ',
        {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_ANON_KEY': 'anon'},
    )
    @patch('src.shared.infrastructure.supabase_client._lazy_create_client')
    def test_fresh_client_is_not_cached(self, create_client):
        import src.shared.infrastructure.supabase_client as mod

        cached = mod._supabase_client
        mod._supabase_client = None
        create_client.side_effect = [MagicMock(name='first'), MagicMock(name='second')]
        try:
            first = mod.get_supabase(fresh=True)
            second = mod.get_supabase(fresh=True)
            self.assertIsNot(first, second)
            self.assertIsNone(mod._supabase_client)
            self.assertEqual(create_client.call_count, 2)
            for call in create_client.call_args_list:
                options = call.args[2]
                self.assertFalse(options.auto_refresh_token)
                self.assertFalse(options.persist_session)
        finally:
            mod._supabase_client = cached

    @patch.dict(
        'os.environ',
        {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_ANON_KEY': 'anon'},
    )
    @patch('src.shared.infrastructure.supabase_client._lazy_create_client')
    def test_default_client_remains_cached(self, create_client):
        import src.shared.infrastructure.supabase_client as mod

        cached = mod._supabase_client
        mod._supabase_client = None
        create_client.return_value = MagicMock(name='cached')
        try:
            self.assertIs(mod.get_supabase(), mod.get_supabase())
            self.assertEqual(create_client.call_count, 1)
        finally:
            mod._supabase_client = cached

    @patch.dict(
        'os.environ',
        {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_ANON_KEY': 'anon'},
    )
    def test_real_fresh_auth_client_has_no_session_timer(self):
        import src.shared.infrastructure.supabase_client as mod

        client = mod.get_supabase(fresh=True)

        self.assertFalse(client.auth._auto_refresh_token)
        self.assertFalse(client.auth._persist_session)
        self.assertIsNone(client.auth._refresh_token_timer)


class TestGetFernet(unittest.TestCase):
    """_get_fernet 테스트

    Issue #17 소PR A: 구현 + 싱글톤 상태(_fernet_instance 등)가
    src.shared.infrastructure.supabase_client로 이전됨 (기존 모듈은 re-export shim).
    """

    def test_no_secret_raises(self):
        from services.data.supabase_service import _get_fernet
        from services.exceptions import ConfigurationError
        import src.shared.infrastructure.supabase_client as mod
        old = mod._fernet_instance
        mod._fernet_instance = None
        try:
            with patch.dict('os.environ', {'ENCRYPTION_SECRET': ''}):
                with self.assertRaises(ConfigurationError):
                    _get_fernet()
        finally:
            mod._fernet_instance = old

    def test_with_secret_creates_fernet(self):
        from services.data.supabase_service import _get_fernet
        from cryptography.fernet import Fernet
        import src.shared.infrastructure.supabase_client as mod
        old = mod._fernet_instance
        mod._fernet_instance = None
        try:
            with patch.dict('os.environ', {'ENCRYPTION_SECRET': 'test-secret-key'}):
                fernet = _get_fernet()
                self.assertIsInstance(fernet, Fernet)
        finally:
            mod._fernet_instance = old


class TestEncryptDecryptRoundTrip(unittest.TestCase):
    """암호화 활성 시 encrypt/decrypt 왕복 테스트"""

    def test_roundtrip(self):
        from services.data.supabase_service import encrypt_api_key, decrypt_api_key
        # Issue #17 소PR A: 싱글톤 상태는 src.shared.infrastructure.supabase_client에 있음
        import src.shared.infrastructure.supabase_client as mod
        # 강제로 암호화 활성화
        old_enc = mod._encryption_enabled
        old_fernet = mod._fernet_instance
        mod._encryption_enabled = None
        mod._fernet_instance = None
        try:
            with patch.dict('os.environ', {'ENCRYPTION_SECRET': 'test-roundtrip-secret'}):
                encrypted = encrypt_api_key('my-api-key')
                self.assertNotEqual(encrypted, 'my-api-key')
                decrypted = decrypt_api_key(encrypted)
                self.assertEqual(decrypted, 'my-api-key')
        finally:
            mod._encryption_enabled = old_enc
            mod._fernet_instance = old_fernet

    def test_decrypt_invalid_token(self):
        from services.data.supabase_service import decrypt_api_key
        # Issue #17 소PR A: 싱글톤 상태는 src.shared.infrastructure.supabase_client에 있음
        import src.shared.infrastructure.supabase_client as mod
        old_enc = mod._encryption_enabled
        old_fernet = mod._fernet_instance
        mod._encryption_enabled = None
        mod._fernet_instance = None
        try:
            with patch.dict('os.environ', {'ENCRYPTION_SECRET': 'test-secret'}):
                result = decrypt_api_key('not-a-valid-fernet-token')
                self.assertIsNone(result)
        finally:
            mod._encryption_enabled = old_enc
            mod._fernet_instance = old_fernet


class TestGetUsage(unittest.TestCase):
    """get_usage 테스트"""

    @patch('services.data.supabase_service.get_user_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_usage
        result = get_usage('user1')
        self.assertFalse(result['can_use'])

    @patch('services.data.supabase_service.get_user_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import get_usage
        result = get_usage(None)
        self.assertEqual(result['usage_count'], 0)


class TestDecrementUsage(unittest.TestCase):
    """decrement_usage 테스트"""

    @patch('services.data.supabase_service.get_user_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import decrement_usage
        self.assertFalse(decrement_usage('user1'))

    @patch('services.data.supabase_service.get_user_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import decrement_usage
        self.assertFalse(decrement_usage(None))


class TestIsAdmin(unittest.TestCase):
    """is_admin 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import is_admin
        self.assertFalse(is_admin('user1'))

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import is_admin
        self.assertFalse(is_admin(None))


class TestGetAdminClient(unittest.TestCase):
    """_get_admin_client 테스트"""

    def test_no_service_role_key(self):
        from services.data.supabase_service import _get_admin_client
        # Issue #17 소PR A: 싱글톤 상태는 src.shared.infrastructure.supabase_client에 있음
        import src.shared.infrastructure.supabase_client as mod
        old = mod._supabase_admin
        mod._supabase_admin = None
        try:
            with patch.dict('os.environ', {'SUPABASE_URL': '', 'SUPABASE_SERVICE_ROLE_KEY': ''}):
                result = _get_admin_client()
                self.assertIsNone(result)
        finally:
            mod._supabase_admin = old


if __name__ == '__main__':
    unittest.main()
