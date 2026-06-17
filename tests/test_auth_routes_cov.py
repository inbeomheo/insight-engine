"""auth_routes.py 라우트 커버리지 테스트.

인증, API 키, 커스텀 스타일, 사용량, 히스토리, 프로필, 관리자,
워크스페이스, 스타일 메모리, 스니펫, 채널 모니터, 대시보드 커버.
"""
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── Supabase 비활성화 상태 테스트 ─────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestAuthStatusDisabled(_Base):

    def test_auth_status(self, _):
        resp = self.client.get('/api/auth/status', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['enabled'])

    def test_auth_config(self, _):
        resp = self.client.get('/api/auth/config', headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('enabled', data)
        self.assertIn('url', data)

    def test_signup_disabled(self, _):
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Supabase', resp.get_json().get('error', ''))

    def test_login_disabled(self, _):
        resp = self.client.post('/api/auth/login',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_reset_password_disabled(self, _):
        resp = self.client.post('/api/auth/reset-password',
                                json={'email': 'a@b.com'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_oauth_login_disabled(self, _):
        resp = self.client.get('/api/auth/oauth/google', headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_oauth_callback_disabled(self, _):
        resp = self.client.post('/api/auth/oauth/callback',
                                json={'code': 'abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_refresh_token_disabled(self, _):
        resp = self.client.post('/api/auth/refresh',
                                json={'refresh_token': 'tok'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 인증 필요 엔드포인트 (Supabase 비활성 → g.user_id=None) ───


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestAuthEndpointsNoSupabase(_Base):
    """Supabase 비활성화 시 require_auth는 g.user_id=None으로 통과시킴."""

    def test_logout(self, _):
        resp = self.client.post('/api/auth/logout', headers=_H)
        # Supabase 비활성 시 get_supabase() 호출에서 에러 가능
        self.assertIn(resp.status_code, [200, 400, 500])

    @patch('routes.auth_routes.get_api_keys', return_value={})
    def test_get_user_keys(self, _mock_keys, _):
        resp = self.client.get('/api/user/keys', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('keys', resp.get_json())

    @patch('routes.auth_routes.save_api_keys', return_value=True)
    def test_save_user_keys_success(self, _mock_save, _):
        resp = self.client.post('/api/user/keys',
                                json={'gemini': 'key123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.save_api_keys', return_value=False)
    def test_save_user_keys_fail(self, _mock_save, _):
        resp = self.client.post('/api/user/keys',
                                json={'gemini': 'key123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.get_custom_styles', return_value=[])
    def test_get_user_styles(self, _mock_styles, _):
        resp = self.client.get('/api/user/styles', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.save_custom_style', return_value=True)
    def test_save_user_style_success(self, _mock_save, _):
        resp = self.client.post('/api/user/styles',
                                json={'name': 'my', 'prompt': 'test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.save_custom_style', return_value=False)
    def test_save_user_style_fail(self, _mock_save, _):
        resp = self.client.post('/api/user/styles',
                                json={'name': 'my', 'prompt': 'test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.delete_custom_style', return_value=True)
    def test_delete_user_style_success(self, _mock_del, _):
        resp = self.client.delete('/api/user/styles/s1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.delete_custom_style', return_value=False)
    def test_delete_user_style_fail(self, _mock_del, _):
        resp = self.client.delete('/api/user/styles/s1', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.is_admin', return_value=False)
    @patch('routes.auth_routes.get_usage', return_value={'remaining': 5, 'max': 10})
    def test_get_user_usage(self, _mock_usage, _mock_admin, _):
        resp = self.client.get('/api/user/usage', headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('remaining', data)
        self.assertFalse(data['is_admin'])

    @patch('routes.auth_routes.is_admin', return_value=True)
    @patch('routes.auth_routes.get_usage', return_value={'remaining': 99, 'max': 100})
    def test_get_user_usage_admin(self, _mock_usage, _mock_admin, _):
        resp = self.client.get('/api/user/usage', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['is_admin'])


# ── 히스토리 ────────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestHistoryRoutes(_Base):

    @patch('routes.auth_routes.is_admin', return_value=False)
    @patch('routes.auth_routes.get_histories', return_value={
        'histories': [{'report_id': 'r1', 'url': 'u', 'title': 't',
                       'style': 's', 'html': '<p>', 'content': 'c',
                       'prompt': 'p', 'usage': {}, 'elapsed_time': 1.0,
                       'is_favorite': False, 'keywords': [],
                       'created_at': '2026-01-01'}],
        'total': 1, 'page': 1, 'per_page': 20,
        'total_pages': 1, 'has_more': False
    })
    def test_get_history(self, _mock_hist, _mock_admin, _):
        resp = self.client.get('/api/user/history', headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['histories']), 1)

    @patch('routes.auth_routes.delete_history', return_value=True)
    def test_delete_history_success(self, _mock_del, _):
        resp = self.client.delete('/api/user/history/r1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.delete_history', return_value=False)
    def test_delete_history_fail(self, _mock_del, _):
        resp = self.client.delete('/api/user/history/r1', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.toggle_favorite', return_value={'success': True, 'is_favorite': True})
    def test_toggle_favorite_success(self, _mock_fav, _):
        resp = self.client.post('/api/user/history/r1/favorite', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['is_favorite'])

    @patch('routes.auth_routes.toggle_favorite', return_value={'success': False, 'error': 'fail'})
    def test_toggle_favorite_fail(self, _mock_fav, _):
        resp = self.client.post('/api/user/history/r1/favorite', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.update_history', return_value=True)
    def test_update_history_success(self, _mock_upd, _):
        resp = self.client.put('/api/user/history/r1',
                               json={'title': 'new'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.update_history', return_value=False)
    def test_update_history_fail(self, _mock_upd, _):
        resp = self.client.put('/api/user/history/r1',
                               json={'title': 'new'},
                               headers=_H)
        self.assertEqual(resp.status_code, 500)

    def test_update_history_no_fields(self, _):
        resp = self.client.put('/api/user/history/r1',
                               json={'invalid_field': 'x'},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 프로필/비밀번호/계정삭제 ──────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestProfileRoutes(_Base):

    @patch('routes.auth_routes.update_user_profile',
           return_value={'success': True, 'user': {'display_name': 'nick'}})
    def test_update_profile_success(self, _mock, _):
        resp = self.client.put('/api/user/profile',
                               json={'display_name': 'nick'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    def test_update_profile_empty(self, _):
        resp = self.client.put('/api/user/profile',
                               json={'display_name': ''},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_update_profile_too_long(self, _):
        resp = self.client.put('/api/user/profile',
                               json={'display_name': 'x' * 51},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.update_user_profile',
           return_value={'success': False, 'error': 'fail'})
    def test_update_profile_fail(self, _mock, _):
        resp = self.client.put('/api/user/profile',
                               json={'display_name': 'nick'},
                               headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.update_user_password', return_value={'success': True})
    def test_change_password_success(self, _mock, _):
        resp = self.client.put('/api/user/password',
                               json={'new_password': 'abcdef'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    def test_change_password_short(self, _):
        resp = self.client.put('/api/user/password',
                               json={'new_password': 'abc'},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.update_user_password',
           return_value={'success': False, 'error': 'fail'})
    def test_change_password_fail(self, _mock, _):
        resp = self.client.put('/api/user/password',
                               json={'new_password': 'abcdef'},
                               headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.delete_user_account', return_value=True)
    def test_delete_account_success(self, _mock, _):
        resp = self.client.delete('/api/user/account', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.delete_user_account', return_value=False)
    def test_delete_account_fail(self, _mock, _):
        resp = self.client.delete('/api/user/account', headers=_H)
        self.assertEqual(resp.status_code, 500)


# ── 관리자 API ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestAdminRoutes(_Base):

    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_check_admin(self, _mock_admin, _):
        resp = self.client.get('/api/admin/check', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['is_admin'])

    @patch('routes.auth_routes.is_admin', return_value=False)
    def test_check_admin_not_admin(self, _mock_admin, _):
        resp = self.client.get('/api/admin/check', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['is_admin'])

    @patch('routes.auth_routes.get_all_users_usage', return_value=[])
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_get_admin_users(self, _mock_admin, _mock_users, _):
        resp = self.client.get('/api/admin/users', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('users', resp.get_json())

    @patch('routes.auth_routes.is_admin', return_value=False)
    def test_get_admin_users_forbidden(self, _mock_admin, _):
        resp = self.client.get('/api/admin/users', headers=_H)
        self.assertEqual(resp.status_code, 403)

    @patch('routes.auth_routes.reset_user_usage', return_value=True)
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_admin_reset_user(self, _mock_admin, _mock_reset, _):
        resp = self.client.post('/api/admin/users/uid1/reset', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.reset_user_usage', return_value=False)
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_admin_reset_user_fail(self, _mock_admin, _mock_reset, _):
        resp = self.client.post('/api/admin/users/uid1/reset', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.get_usage_stats', return_value={'total': 100})
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_get_admin_stats(self, _mock_admin, _mock_stats, _):
        resp = self.client.get('/api/admin/stats', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.is_admin', return_value=False)
    def test_get_admin_stats_forbidden(self, _mock_admin, _):
        resp = self.client.get('/api/admin/stats', headers=_H)
        self.assertEqual(resp.status_code, 403)

    @patch('routes.auth_routes.get_all_contents', return_value={'contents': [], 'total': 0})
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_get_admin_contents(self, _mock_admin, _mock_contents, _):
        resp = self.client.get('/api/admin/contents', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_content_detail', return_value={'id': 'r1', 'title': 't'})
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_get_admin_content_detail(self, _mock_admin, _mock_detail, _):
        resp = self.client.get('/api/admin/contents/r1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_content_detail', return_value=None)
    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_get_admin_content_detail_not_found(self, _mock_admin, _mock_detail, _):
        resp = self.client.get('/api/admin/contents/r1', headers=_H)
        self.assertEqual(resp.status_code, 404)


# ── Supabase 활성 상태 — 인증 엔드포인트 ───────────────────


@patch('routes.auth_routes.is_supabase_enabled', return_value=True)
@patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
class TestAuthEndpointsEnabled(_Base):

    def test_signup_missing_fields(self, _, __):
        resp = self.client.post('/api/auth/signup', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_signup_short_password(self, _, __):
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '12345'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_signup_success(self, mock_sb, _, __):
        mock_user = MagicMock()
        mock_user.id = 'uid1'
        mock_user.email = 'a@b.com'
        mock_sb.return_value.auth.sign_up.return_value = MagicMock(user=mock_user)
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_supabase')
    def test_signup_no_user(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_up.return_value = MagicMock(user=None)
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_signup_already_registered(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_up.side_effect = Exception('User already registered')
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('이미 등록', resp.get_json().get('error', ''))

    @patch('routes.auth_routes.get_supabase')
    def test_signup_rate_limit(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_up.side_effect = Exception('Rate limit exceeded')
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_signup_invalid_email(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_up.side_effect = Exception('invalid email address')
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'bad', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_signup_unknown_error(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_up.side_effect = Exception('something unexpected')
        resp = self.client.post('/api/auth/signup',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_fields(self, _, __):
        resp = self.client.post('/api/auth/login', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_login_success(self, mock_sb, _, __):
        mock_user = MagicMock()
        mock_user.id = 'uid1'
        mock_user.email = 'a@b.com'
        mock_session = MagicMock()
        mock_session.access_token = 'at'
        mock_session.refresh_token = 'rt'
        mock_session.expires_at = 9999
        mock_sb.return_value.auth.sign_in_with_password.return_value = MagicMock(
            user=mock_user, session=mock_session
        )
        resp = self.client.post('/api/auth/login',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_supabase')
    def test_login_no_session(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_in_with_password.return_value = MagicMock(
            user=None, session=None
        )
        resp = self.client.post('/api/auth/login',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    @patch('routes.auth_routes.get_supabase')
    def test_login_exception(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_in_with_password.side_effect = Exception('bad')
        resp = self.client.post('/api/auth/login',
                                json={'email': 'a@b.com', 'password': '123456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    def test_reset_password_missing_email(self, _, __):
        resp = self.client.post('/api/auth/reset-password', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_reset_password_success(self, mock_sb, _, __):
        resp = self.client.post('/api/auth/reset-password',
                                json={'email': 'a@b.com'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_supabase')
    def test_reset_password_exception(self, mock_sb, _, __):
        mock_sb.return_value.auth.reset_password_email.side_effect = Exception('fail')
        resp = self.client.post('/api/auth/reset-password',
                                json={'email': 'a@b.com'},
                                headers=_H)
        # 계정 열거 방지: 예외 시에도 200 반환
        self.assertEqual(resp.status_code, 200)

    def test_oauth_unsupported_provider(self, _, __):
        resp = self.client.get('/api/auth/oauth/twitter', headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_login_success(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_in_with_oauth.return_value = MagicMock(url='https://oauth.example.com')
        resp = self.client.get('/api/auth/oauth/google', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('url', resp.get_json())

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_login_exception(self, mock_sb, _, __):
        mock_sb.return_value.auth.sign_in_with_oauth.side_effect = Exception('oauth fail')
        resp = self.client.get('/api/auth/oauth/google', headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_oauth_callback_missing_code(self, _, __):
        resp = self.client.post('/api/auth/oauth/callback', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_callback_success(self, mock_sb, _, __):
        mock_user = MagicMock()
        mock_user.id = 'uid1'
        mock_user.email = 'a@b.com'
        mock_session = MagicMock()
        mock_session.access_token = 'at'
        mock_session.refresh_token = 'rt'
        mock_session.expires_at = 9999
        mock_sb.return_value.auth.exchange_code_for_session.return_value = MagicMock(
            user=mock_user, session=mock_session
        )
        resp = self.client.post('/api/auth/oauth/callback',
                                json={'code': 'abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_callback_no_session(self, mock_sb, _, __):
        mock_sb.return_value.auth.exchange_code_for_session.return_value = MagicMock(
            user=None, session=None
        )
        resp = self.client.post('/api/auth/oauth/callback',
                                json={'code': 'abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_callback_exception(self, mock_sb, _, __):
        mock_sb.return_value.auth.exchange_code_for_session.side_effect = Exception('fail')
        resp = self.client.post('/api/auth/oauth/callback',
                                json={'code': 'abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    def test_refresh_token_missing(self, _, __):
        resp = self.client.post('/api/auth/refresh', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.get_supabase')
    def test_refresh_token_success(self, mock_sb, _, __):
        mock_session = MagicMock()
        mock_session.access_token = 'new_at'
        mock_session.refresh_token = 'new_rt'
        mock_session.expires_at = 9999
        mock_sb.return_value.auth.refresh_session.return_value = MagicMock(session=mock_session)
        resp = self.client.post('/api/auth/refresh',
                                json={'refresh_token': 'old_rt'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.get_supabase')
    def test_refresh_token_fail(self, mock_sb, _, __):
        mock_sb.return_value.auth.refresh_session.return_value = MagicMock(session=None)
        resp = self.client.post('/api/auth/refresh',
                                json={'refresh_token': 'old_rt'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    @patch('routes.auth_routes.get_supabase')
    def test_refresh_token_exception(self, mock_sb, _, __):
        mock_sb.return_value.auth.refresh_session.side_effect = Exception('err')
        resp = self.client.post('/api/auth/refresh',
                                json={'refresh_token': 'old_rt'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)


# ── 워크스페이스 API ─────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestWorkspaceRoutes(_Base):

    def test_create_workspace_disabled(self, _):
        resp = self.client.post('/api/workspaces',
                                json={'name': 'ws1'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_list_workspaces_disabled(self, _):
        """Supabase 비활성 시 빈 리스트 반환."""
        resp = self.client.get('/api/workspaces', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['workspaces'], [])

    def test_get_workspace_members_disabled(self, _):
        resp = self.client.get('/api/workspaces/ws1/members', headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_invite_workspace_member_disabled(self, _):
        resp = self.client.post('/api/workspaces/ws1/invite',
                                json={'user_email': 'a@b.com'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_remove_workspace_member_disabled(self, _):
        resp = self.client.delete('/api/workspaces/ws1/members/u1', headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_delete_workspace_disabled(self, _):
        resp = self.client.delete('/api/workspaces/ws1', headers=_H)
        self.assertEqual(resp.status_code, 400)


@patch('routes.auth_routes.is_supabase_enabled', return_value=True)
@patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
class TestWorkspaceRoutesEnabled(_Base):
    """Supabase 활성 + require_auth 우회(토큰 검증 mock)."""

    @staticmethod
    def _fake_validate(token):
        from flask import g
        g.user_id = 'test-user-id'
        g.user_email = 'test@test.com'
        g.access_token = token
        return {'valid': True, 'error': None, 'code': None}

    @patch('routes.auth_routes.workspace_service')
    @patch('services.data.supabase_service._extract_bearer_token', return_value='tok')
    def test_create_workspace_success(self, _tok, mock_ws, _, __):
        mock_ws.create_workspace.return_value = {'id': 'ws1', 'name': 'WS'}
        with patch('services.data.supabase_service._validate_token',
                   side_effect=self._fake_validate):
            resp = self.client.post('/api/workspaces',
                                    json={'name': 'WS'},
                                    headers={**_H, 'Authorization': 'Bearer tok'})
        self.assertIn(resp.status_code, [200, 201])

    @patch('routes.auth_routes.workspace_service')
    @patch('services.data.supabase_service._extract_bearer_token', return_value='tok')
    def test_create_workspace_error(self, _tok, mock_ws, _, __):
        mock_ws.create_workspace.return_value = {'error': 'dup'}
        with patch('services.data.supabase_service._validate_token',
                   side_effect=self._fake_validate):
            resp = self.client.post('/api/workspaces',
                                    json={'name': 'WS'},
                                    headers={**_H, 'Authorization': 'Bearer tok'})
        self.assertEqual(resp.status_code, 500)

    @patch('services.data.supabase_service._extract_bearer_token', return_value='tok')
    def test_create_workspace_no_name(self, _tok, _, __):
        with patch('services.data.supabase_service._validate_token',
                   side_effect=self._fake_validate):
            resp = self.client.post('/api/workspaces',
                                    json={'name': ''},
                                    headers={**_H, 'Authorization': 'Bearer tok'})
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service._extract_bearer_token', return_value='tok')
    def test_invite_no_email(self, _tok, _, __):
        with patch('services.data.supabase_service._validate_token',
                   side_effect=self._fake_validate):
            resp = self.client.post('/api/workspaces/ws1/invite',
                                    json={'user_email': ''},
                                    headers={**_H, 'Authorization': 'Bearer tok'})
        self.assertEqual(resp.status_code, 400)


# ── 스타일 메모리 ────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestStyleMemoryRoutes(_Base):

    @patch('services.data.style_memory_service.get_profile', return_value={})
    def test_get_style_memory(self, _mock, _):
        resp = self.client.get('/api/user/style-memory', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.get_json())

    @patch('services.data.style_memory_service.save_user_preferences', return_value=True)
    def test_update_style_memory(self, _mock, _):
        resp = self.client.put('/api/user/style-memory',
                               json={'custom_instructions': 'test'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.style_memory_service.save_user_preferences', return_value=False)
    def test_update_style_memory_fail(self, _mock, _):
        """실패해도 graceful 처리로 200."""
        resp = self.client.put('/api/user/style-memory',
                               json={'custom_instructions': 'test'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.style_memory_service.reset_profile')
    def test_reset_style_memory(self, _mock, _):
        resp = self.client.post('/api/user/style-memory/reset', headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 스니펫 ────────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestSnippetRoutes(_Base):

    @patch('routes.auth_routes.get_user_snippets', return_value=[])
    def test_get_snippets(self, _mock, _):
        resp = self.client.get('/api/user/snippets', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('snippets', resp.get_json())

    @patch('routes.auth_routes.create_snippet', return_value={'id': 's1', 'content': 'hi'})
    def test_create_snippet_success(self, _mock, _):
        resp = self.client.post('/api/user/snippets',
                                json={'content': 'hi'},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    def test_create_snippet_no_content(self, _):
        resp = self.client.post('/api/user/snippets',
                                json={'content': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth_routes.create_snippet', return_value={'error': 'fail'})
    def test_create_snippet_error(self, _mock, _):
        resp = self.client.post('/api/user/snippets',
                                json={'content': 'hi'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.create_snippet', side_effect=Exception('boom'))
    def test_create_snippet_exception(self, _mock, _):
        resp = self.client.post('/api/user/snippets',
                                json={'content': 'hi'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('routes.auth_routes.delete_snippet', return_value=True)
    def test_delete_snippet_success(self, _mock, _):
        resp = self.client.delete('/api/user/snippets/s1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('routes.auth_routes.delete_snippet', return_value=False)
    def test_delete_snippet_fail(self, _mock, _):
        resp = self.client.delete('/api/user/snippets/s1', headers=_H)
        self.assertEqual(resp.status_code, 500)


# ── 채널 모니터 ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestChannelMonitorRoutes(_Base):

    def test_get_channel_monitors_disabled(self, _):
        resp = self.client.get('/api/channel-monitors', headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_create_channel_monitor_disabled(self, _):
        resp = self.client.post('/api/channel-monitors',
                                json={'channel_id': 'ch1'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


@patch('routes.auth_routes.is_supabase_enabled', return_value=True)
class TestChannelMonitorBehavior(_Base):
    """Supabase 활성 시 등록/삭제 결과(None/bool)에 따른 상태 코드 검증.

    PR #20/#22 Codex 지적: 등록 실패(None)/삭제 실패(False)를 성공으로 위장하지
    않고 명시적 4xx로 응답해야 한다.
    """

    @patch('routes.auth.channel_monitoring._register_monitor', return_value=None)
    def test_create_returns_400_when_registration_fails(self, _reg, _enabled):
        # 도메인 검증 실패 등으로 None 반환 → 201이 아닌 400
        resp = self.client.post('/api/channel-monitors',
                                json={'channel_id': 'ch1', 'interval_minutes': 1},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('routes.auth.channel_monitoring._register_monitor',
           return_value={'id': 'm1', 'channel_id': 'ch1'})
    def test_create_returns_201_on_success(self, _reg, _enabled):
        resp = self.client.post('/api/channel-monitors',
                                json={'channel_id': 'ch1'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json().get('id'), 'm1')

    @patch('routes.auth.channel_monitoring._delete_monitor', return_value=False)
    def test_delete_returns_404_when_not_removed(self, _del, _enabled):
        # 실제로 삭제되지 않았는데 성공 응답하면 거짓 양성 → 404
        resp = self.client.delete('/api/channel-monitors/m1', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('routes.auth.channel_monitoring._delete_monitor', return_value=True)
    def test_delete_returns_success_when_removed(self, _del, _enabled):
        resp = self.client.delete('/api/channel-monitors/m1', headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 대시보드 ──────────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestDashboardRoutes(_Base):

    @patch('routes.auth_routes.is_admin', return_value=True)
    def test_admin_dashboard_no_supabase(self, _mock_admin, _):
        resp = self.client.get('/api/admin/dashboard', headers=_H)
        self.assertEqual(resp.status_code, 503)

    @patch('routes.auth_routes.is_admin', return_value=False)
    def test_admin_dashboard_forbidden(self, _mock_admin, _):
        resp = self.client.get('/api/admin/dashboard', headers=_H)
        self.assertEqual(resp.status_code, 403)


# ── 헬퍼 함수 단위 테스트 ────────────────────────────────


class TestMaskApiKey(unittest.TestCase):

    def test_mask_none(self):
        from routes.auth_routes import _mask_api_key
        self.assertIsNone(_mask_api_key(None))

    def test_mask_empty(self):
        from routes.auth_routes import _mask_api_key
        self.assertIsNone(_mask_api_key(''))

    def test_mask_short(self):
        from routes.auth_routes import _mask_api_key
        self.assertEqual(_mask_api_key('12345678'), '****')

    def test_mask_normal(self):
        from routes.auth_routes import _mask_api_key
        result = _mask_api_key('sk-1234567890abcdef')
        self.assertTrue(result.startswith('sk-1'))
        self.assertIn('...', result)


class TestSanitizeServiceError(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_safe_message(self, _):
        from routes.auth_routes import _sanitize_service_error
        with self.app.app_context():
            result = _sanitize_service_error('[인증 실패] 잘못된 자격증명', 'fallback')
            self.assertIn('인증', result)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_internal_error_uses_fallback(self, _):
        from routes.auth_routes import _sanitize_service_error
        with self.app.app_context():
            result = _sanitize_service_error('[서버 오류] traceback details', 'fallback')
            self.assertEqual(result, 'fallback')


if __name__ == '__main__':
    unittest.main()
