"""supabase_service 확장 테스트 — CRUD, 사용량, 관리자, 암호화 등 미커버 함수"""
import unittest
from unittest.mock import patch, MagicMock


class TestGetFernet(unittest.TestCase):
    """_get_fernet 테스트"""

    def test_no_secret_raises(self):
        from services.data.supabase_service import _get_fernet
        from services.exceptions import ConfigurationError
        import services.data.supabase_service as mod
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
        import services.data.supabase_service as mod
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
        import services.data.supabase_service as mod
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
        import services.data.supabase_service as mod
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


class TestUpdateHistory(unittest.TestCase):
    """update_history 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import update_history
        self.assertFalse(update_history('user1', 'report1', {'title': 'new'}))

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import update_history
        self.assertFalse(update_history(None, 'report1', {}))

    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb):
        from services.data.supabase_service import update_history
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        self.assertTrue(update_history('user1', 'report1', {'title': 'updated'}))


class TestToggleFavorite(unittest.TestCase):
    """toggle_favorite 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import toggle_favorite
        result = toggle_favorite('user1', 'report1')
        self.assertFalse(result.get('success'))

    @patch('services.data.supabase_service.get_supabase')
    def test_not_found(self, mock_sb):
        from services.data.supabase_service import toggle_favorite
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        result = toggle_favorite('user1', 'report1')
        self.assertFalse(result.get('success'))

    @patch('services.data.supabase_service.get_supabase')
    def test_toggle_on(self, mock_sb):
        from services.data.supabase_service import toggle_favorite
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        # 현재 False → True로 토글
        select_chain = MagicMock()
        select_chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'is_favorite': False}]
        )
        update_chain = MagicMock()
        update_chain.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_client.table.side_effect = [select_chain, update_chain]
        result = toggle_favorite('user1', 'report1')
        self.assertTrue(result.get('success'))
        self.assertTrue(result.get('is_favorite'))


class TestDeleteHistory(unittest.TestCase):
    """delete_history 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import delete_history
        self.assertFalse(delete_history('user1', 'report1'))

    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb):
        from services.data.supabase_service import delete_history
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        self.assertTrue(delete_history('user1', 'report1'))


class TestDeleteUserAccount(unittest.TestCase):
    """delete_user_account 테스트"""

    @patch('services.data.supabase_service._get_admin_client', return_value=None)
    def test_no_admin_client(self, _):
        from services.data.supabase_service import delete_user_account
        self.assertFalse(delete_user_account('user1'))

    @patch('services.data.supabase_service._get_admin_client')
    def test_success(self, mock_admin):
        from services.data.supabase_service import delete_user_account
        admin = MagicMock()
        mock_admin.return_value = admin
        self.assertTrue(delete_user_account('user1'))
        admin.auth.admin.delete_user.assert_called_once_with('user1')

    @patch('services.data.supabase_service._get_admin_client')
    def test_exception(self, mock_admin):
        from services.data.supabase_service import delete_user_account
        admin = MagicMock()
        admin.auth.admin.delete_user.side_effect = Exception('fail')
        mock_admin.return_value = admin
        self.assertFalse(delete_user_account('user1'))


class TestUpdateUserProfile(unittest.TestCase):
    """update_user_profile 테스트"""

    @patch('services.data.supabase_service._get_admin_client', return_value=None)
    def test_no_admin_client(self, _):
        from services.data.supabase_service import update_user_profile
        result = update_user_profile('user1', '새이름')
        self.assertFalse(result.get('success'))

    @patch('services.data.supabase_service._get_admin_client')
    def test_success(self, mock_admin):
        from services.data.supabase_service import update_user_profile
        admin = MagicMock()
        mock_admin.return_value = admin
        mock_user = MagicMock()
        mock_user.user.id = 'user1'
        mock_user.user.email = 'test@test.com'
        mock_user.user.user_metadata = {'display_name': '새이름'}
        admin.auth.admin.update_user_by_id.return_value = mock_user
        result = update_user_profile('user1', '새이름')
        self.assertTrue(result.get('success'))


class TestUpdateUserPassword(unittest.TestCase):
    """update_user_password 테스트"""

    @patch('services.data.supabase_service._get_admin_client', return_value=None)
    def test_no_admin_client(self, _):
        from services.data.supabase_service import update_user_password
        result = update_user_password('user1', 'newpass')
        self.assertFalse(result.get('success'))

    @patch('services.data.supabase_service._get_admin_client')
    def test_success(self, mock_admin):
        from services.data.supabase_service import update_user_password
        admin = MagicMock()
        mock_admin.return_value = admin
        result = update_user_password('user1', 'newpass')
        self.assertTrue(result.get('success'))

    @patch('services.data.supabase_service._get_admin_client')
    def test_exception(self, mock_admin):
        from services.data.supabase_service import update_user_password
        admin = MagicMock()
        admin.auth.admin.update_user_by_id.side_effect = Exception('fail')
        mock_admin.return_value = admin
        result = update_user_password('user1', 'newpass')
        self.assertFalse(result.get('success'))


class TestSaveApiKeys(unittest.TestCase):
    """save_api_keys 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import save_api_keys
        self.assertFalse(save_api_keys('user1', {'openai': 'key'}))

    @patch('services.data.supabase_service.encrypt_api_key', side_effect=lambda x: x)
    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb, _):
        from services.data.supabase_service import save_api_keys
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        self.assertTrue(save_api_keys('user1', {'openai': 'sk-test'}))


class TestGetApiKeys(unittest.TestCase):
    """get_api_keys 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_api_keys
        self.assertEqual(get_api_keys('user1'), {})

    @patch('services.data.supabase_service.decrypt_api_key', side_effect=lambda x: x)
    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb, _):
        from services.data.supabase_service import get_api_keys
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'selected_provider': 'openai', 'openai_key': 'sk-test', 'anthropic_key': None,
                   'google_key': None, 'zhipu_key': None, 'deepseek_key': None, 'supadata_key': None}]
        )
        result = get_api_keys('user1')
        self.assertEqual(result['selectedProvider'], 'openai')

    @patch('services.data.supabase_service.get_supabase')
    def test_no_data(self, mock_sb):
        from services.data.supabase_service import get_api_keys
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        self.assertEqual(get_api_keys('user1'), {})


class TestCustomStyles(unittest.TestCase):
    """save_custom_style, get_custom_styles, delete_custom_style 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_save_no_client(self, _):
        from services.data.supabase_service import save_custom_style
        self.assertFalse(save_custom_style('user1', {'id': 'my_style'}))

    @patch('services.data.supabase_service.get_supabase')
    def test_save_success(self, mock_sb):
        from services.data.supabase_service import save_custom_style
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        self.assertTrue(save_custom_style('user1', {'id': 'my_style', 'name': 'My Style', 'prompt': 'test'}))

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_get_no_client(self, _):
        from services.data.supabase_service import get_custom_styles
        self.assertEqual(get_custom_styles('user1'), [])

    @patch('services.data.supabase_service.get_supabase')
    def test_get_success(self, mock_sb):
        from services.data.supabase_service import get_custom_styles
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{'style_id': 's1', 'name': 'Style1', 'icon': 'edit', 'prompt': 'p1'}]
        )
        result = get_custom_styles('user1')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 's1')

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_delete_no_client(self, _):
        from services.data.supabase_service import delete_custom_style
        self.assertFalse(delete_custom_style('user1', 's1'))


class TestGetUsage(unittest.TestCase):
    """get_usage 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_usage
        result = get_usage('user1')
        self.assertFalse(result['can_use'])

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import get_usage
        result = get_usage(None)
        self.assertEqual(result['usage_count'], 0)


class TestDecrementUsage(unittest.TestCase):
    """decrement_usage 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import decrement_usage
        self.assertFalse(decrement_usage('user1'))

    @patch('services.data.supabase_service.get_supabase', return_value=None)
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


class TestGetAdminPermissions(unittest.TestCase):
    """get_admin_permissions 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_admin_permissions
        self.assertEqual(get_admin_permissions('user1'), {})

    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb):
        from services.data.supabase_service import get_admin_permissions
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'permissions': {'can_delete': True}}]
        )
        result = get_admin_permissions('user1')
        self.assertTrue(result.get('can_delete'))

    @patch('services.data.supabase_service.get_supabase')
    def test_no_data(self, mock_sb):
        from services.data.supabase_service import get_admin_permissions
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        self.assertEqual(get_admin_permissions('user1'), {})


class TestGetAllUsersUsage(unittest.TestCase):
    """get_all_users_usage 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_all_users_usage
        self.assertEqual(get_all_users_usage(), [])


class TestResetUserUsage(unittest.TestCase):
    """reset_user_usage 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import reset_user_usage
        self.assertFalse(reset_user_usage('user1'))

    @patch('services.data.supabase_service.get_supabase')
    def test_success(self, mock_sb):
        from services.data.supabase_service import reset_user_usage
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        self.assertTrue(reset_user_usage('user1'))


class TestGetUsageStats(unittest.TestCase):
    """get_usage_stats 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_usage_stats
        self.assertEqual(get_usage_stats(), {})


class TestGetAllContents(unittest.TestCase):
    """get_all_contents 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_all_contents
        result = get_all_contents()
        self.assertEqual(result['contents'], [])

    @patch('services.data.supabase_service.get_supabase')
    def test_with_data(self, mock_sb):
        from services.data.supabase_service import get_all_contents
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        # count 쿼리
        count_chain = MagicMock()
        count_chain.select.return_value.execute.return_value = MagicMock(count=2)
        # data 쿼리
        data_chain = MagicMock()
        data_chain.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[
                {'report_id': 'r1', 'user_id': 'u1', 'user_email': 'a@b.com', 'url': 'http://yt', 'title': 'T1', 'style': 'blog_seo', 'created_at': '2026-01-01'},
            ]
        )
        mock_client.table.side_effect = [count_chain, data_chain]
        result = get_all_contents()
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['contents']), 1)


class TestGetContentDetail(unittest.TestCase):
    """get_content_detail 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_content_detail
        self.assertEqual(get_content_detail('r1'), {})

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_report_id(self, _):
        from services.data.supabase_service import get_content_detail
        self.assertEqual(get_content_detail(None), {})


class TestGetAdminClient(unittest.TestCase):
    """_get_admin_client 테스트"""

    def test_no_service_role_key(self):
        from services.data.supabase_service import _get_admin_client
        import services.data.supabase_service as mod
        old = mod._supabase_admin
        mod._supabase_admin = None
        try:
            with patch.dict('os.environ', {'SUPABASE_URL': '', 'SUPABASE_SERVICE_ROLE_KEY': ''}):
                result = _get_admin_client()
                self.assertIsNone(result)
        finally:
            mod._supabase_admin = old


class TestGetUserSnippets(unittest.TestCase):
    """get_user_snippets 테스트"""

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_client(self, _):
        from services.data.supabase_service import get_user_snippets
        self.assertEqual(get_user_snippets('user1'), [])

    @patch('services.data.supabase_service.get_supabase', return_value=None)
    def test_no_user_id(self, _):
        from services.data.supabase_service import get_user_snippets
        self.assertEqual(get_user_snippets(None), [])


if __name__ == '__main__':
    unittest.main()
