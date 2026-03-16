"""SSO 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestSSORoutes(unittest.TestCase):
    """SSO 설정/로그인/콜백/비활성화 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_configure_saml(self, _mock_sb):
        """SAML SSO 설정 성공."""
        resp = self.client.post(
            '/api/sso/ws1/config',
            json={
                'provider': 'saml',
                'config': {'entity_id': 'eid', 'sso_url': 'https://idp.example.com/sso'},
            },
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['provider'], 'saml')
        self.assertTrue(data['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_configure_missing_provider(self, _mock_sb):
        """provider 누락 시 에러."""
        resp = self.client.post(
            '/api/sso/ws1/config',
            json={'provider': '', 'config': {}},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_config_not_set(self, _mock_sb):
        """미설정 시 enabled=False."""
        resp = self.client.get('/api/sso/ws_none/config', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_login_not_configured(self, _mock_sb):
        """SSO 미설정 워크스페이스 로그인 시 에러."""
        resp = self.client.post(
            '/api/sso/ws_none/login',
            json={},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_callback_no_email(self, _mock_sb):
        """콜백에 이메일 없으면 에러."""
        resp = self.client.post(
            '/api/sso/ws_none/callback',
            json={},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
