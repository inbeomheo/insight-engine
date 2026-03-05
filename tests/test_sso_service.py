"""
SSOService 단위 테스트 (F4-24)
"""
import unittest
from services.auth.sso_service import SSOService


class TestSSOService(unittest.TestCase):

    def setUp(self):
        self.svc = SSOService()

    def test_configure_saml(self):
        config = {'entity_id': 'eid', 'sso_url': 'https://idp.example.com/sso'}
        result = self.svc.configure_sso('ws-1', 'saml', config)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['provider'], 'saml')

    def test_configure_oidc(self):
        config = {'client_id': 'cid', 'issuer_url': 'https://auth.example.com'}
        result = self.svc.configure_sso('ws-1', 'oidc', config)
        self.assertEqual(result['provider'], 'oidc')

    def test_configure_invalid_provider(self):
        result = self.svc.configure_sso('ws-1', 'ldap', {})
        self.assertIn('error', result)

    def test_configure_missing_fields(self):
        result = self.svc.configure_sso('ws-1', 'saml', {})
        self.assertIn('error', result)

    def test_is_enabled(self):
        self.assertFalse(self.svc.is_enabled('ws-1'))
        self.svc.configure_sso('ws-1', 'oidc', {'client_id': 'c', 'issuer_url': 'u'})
        self.assertTrue(self.svc.is_enabled('ws-1'))

    def test_initiate_login_oidc(self):
        self.svc.configure_sso('ws-1', 'oidc', {'client_id': 'cid', 'issuer_url': 'https://auth.example.com'})
        result = self.svc.initiate_login('ws-1')
        self.assertIn('redirect_url', result)
        self.assertIn('cid', result['redirect_url'])

    def test_initiate_login_not_configured(self):
        result = self.svc.initiate_login('ws-no')
        self.assertIn('error', result)

    def test_validate_callback(self):
        self.svc.configure_sso('ws-1', 'oidc', {'client_id': 'c', 'issuer_url': 'u'})
        result = self.svc.validate_callback('ws-1', {'email': 'test@example.com'})
        self.assertIn('session_id', result)
        self.assertEqual(result['email'], 'test@example.com')

    def test_validate_callback_no_email(self):
        self.svc.configure_sso('ws-1', 'oidc', {'client_id': 'c', 'issuer_url': 'u'})
        result = self.svc.validate_callback('ws-1', {})
        self.assertIn('error', result)

    def test_disable_sso(self):
        self.svc.configure_sso('ws-1', 'oidc', {'client_id': 'c', 'issuer_url': 'u'})
        self.svc.disable_sso('ws-1')
        self.assertFalse(self.svc.is_enabled('ws-1'))


if __name__ == '__main__':
    unittest.main()
