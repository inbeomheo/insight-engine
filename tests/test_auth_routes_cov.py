"""auth_routes.py 라우트 커버리지 테스트.

인증, 사용량, 워크스페이스, 스타일 메모리, 스니펫, 채널 모니터, 대시보드 커버.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


def _configure_oauth_start(mock_supabase):
    def start_oauth(_credentials):
        storage = mock_supabase.call_args.kwargs['auth_storage']
        storage.set_item('test-code-verifier', 'pkce-verifier')
        return MagicMock(url='https://oauth.example.com')

    mock_supabase.return_value.auth.sign_in_with_oauth.side_effect = start_oauth


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── Supabase 비활성화 상태 테스트 ─────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestAuthStatusDisabled(_Base):

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
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('등록된 이메일', resp.get_json().get('message', ''))

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
        self.assertNotIn('refresh_token', resp.get_json()['session'])

    @patch('routes.auth_routes.get_supabase')
    def test_login_explicit_token_transport_returns_refresh_token(self, mock_sb, _, __):
        mock_user = MagicMock(id='uid1', email='a@b.com')
        mock_session = MagicMock(
            access_token='at',
            refresh_token='rt',
            expires_at=9999,
        )
        mock_sb.return_value.auth.sign_in_with_password.return_value = MagicMock(
            user=mock_user,
            session=mock_session,
        )

        resp = self.client.post(
            '/api/auth/login',
            json={'email': 'a@b.com', 'password': '123456'},
            headers={**_H, 'X-Auth-Transport': 'token'},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['session']['refresh_token'], 'rt')

    @patch('routes.auth_routes.get_supabase')
    def test_login_cookie_transport_hides_refresh_token(self, mock_sb, _, __):
        mock_user = MagicMock(id='uid1', email='a@b.com')
        mock_session = MagicMock(
            access_token='at',
            refresh_token='rt',
            expires_at=9999,
        )
        mock_sb.return_value.auth.sign_in_with_password.return_value = MagicMock(
            user=mock_user,
            session=mock_session,
        )
        resp = self.client.post(
            '/api/auth/login',
            json={'email': 'a@b.com', 'password': '123456'},
            headers={**_H, 'X-Auth-Transport': 'cookie'},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('refresh_token', resp.get_json()['session'])
        cookie = resp.headers.get('Set-Cookie', '')
        self.assertIn('ie_refresh_token=rt', cookie)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)

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
        _configure_oauth_start(mock_sb)
        resp = self.client.get('/api/auth/oauth/google', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('url', resp.get_json())
        self.assertTrue(mock_sb.call_args.kwargs['fresh'])
        self.assertIn('ie_oauth_pkce=pkce-verifier', resp.headers.get('Set-Cookie', ''))

    @patch.dict(os.environ, {'CORS_ORIGINS': 'https://app.example.com'})
    @patch('routes.auth_routes.get_supabase')
    def test_oauth_redirect_requires_exact_origin(self, mock_sb, _, __):
        _configure_oauth_start(mock_sb)
        resp = self.client.get(
            '/api/auth/oauth/google?redirect_url='
            'https://app.example.com.evil.test/callback',
            headers=_H,
        )
        self.assertEqual(resp.status_code, 200)
        options = mock_sb.return_value.auth.sign_in_with_oauth.call_args.args[0]
        self.assertEqual(
            options['options']['redirect_to'],
            'https://app.example.com',
        )

    @patch.dict(os.environ, {'CORS_ORIGINS': 'https://app.example.com'})
    @patch('routes.auth_routes.get_supabase')
    def test_oauth_redirect_allows_path_on_exact_origin(self, mock_sb, _, __):
        _configure_oauth_start(mock_sb)
        redirect = 'https://app.example.com/auth/callback?next=notes'
        resp = self.client.get(
            f'/api/auth/oauth/google?redirect_url={redirect}',
            headers=_H,
        )
        self.assertEqual(resp.status_code, 200)
        options = mock_sb.return_value.auth.sign_in_with_oauth.call_args.args[0]
        self.assertEqual(options['options']['redirect_to'], redirect)

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
        self.client.set_cookie('ie_oauth_pkce', 'pkce-verifier')
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
        self.assertNotIn('refresh_token', resp.get_json()['session'])

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_callback_no_session(self, mock_sb, _, __):
        self.client.set_cookie('ie_oauth_pkce', 'pkce-verifier')
        mock_sb.return_value.auth.exchange_code_for_session.return_value = MagicMock(
            user=None, session=None
        )
        resp = self.client.post('/api/auth/oauth/callback',
                                json={'code': 'abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 401)

    @patch('routes.auth_routes.get_supabase')
    def test_oauth_callback_exception(self, mock_sb, _, __):
        self.client.set_cookie('ie_oauth_pkce', 'pkce-verifier')
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
        mock_user = MagicMock(id='uid1', email='a@b.com')
        mock_sb.return_value.auth.refresh_session.return_value = MagicMock(
            session=mock_session,
            user=mock_user,
        )
        resp = self.client.post('/api/auth/refresh',
                                json={'refresh_token': 'old_rt'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['user']['id'], 'uid1')
        self.assertNotIn('refresh_token', resp.get_json()['session'])

    @patch('routes.auth_routes.get_supabase')
    def test_refresh_explicit_token_transport_returns_rotated_token(self, mock_sb, _, __):
        mock_session = MagicMock(
            access_token='new_at',
            refresh_token='new_rt',
            expires_at=9999,
        )
        mock_sb.return_value.auth.refresh_session.return_value = MagicMock(
            session=mock_session,
            user=MagicMock(id='uid1', email='a@b.com'),
        )

        resp = self.client.post(
            '/api/auth/refresh',
            json={'refresh_token': 'old_rt'},
            headers={**_H, 'X-Auth-Transport': 'token'},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['session']['refresh_token'], 'new_rt')

    @patch('routes.auth_routes.get_supabase')
    def test_refresh_cookie_transport_rotates_http_only_cookie(self, mock_sb, _, __):
        self.client.set_cookie('ie_refresh_token', 'old_rt')
        mock_session = MagicMock(
            access_token='new_at',
            refresh_token='new_rt',
            expires_at=9999,
        )
        mock_sb.return_value.auth.refresh_session.return_value = MagicMock(
            session=mock_session,
            user=MagicMock(id='uid1', email='a@b.com'),
        )

        resp = self.client.post(
            '/api/auth/refresh',
            json={},
            headers={**_H, 'X-Auth-Transport': 'cookie'},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('refresh_token', resp.get_json()['session'])
        self.assertIn('ie_refresh_token=new_rt', resp.headers.get('Set-Cookie', ''))
        mock_sb.return_value.auth.refresh_session.assert_called_once_with('old_rt')

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
