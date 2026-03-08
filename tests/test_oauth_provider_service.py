"""OAuth Provider Service 테스트"""
import hashlib
import base64
import time
import unittest
from unittest.mock import patch

from services.auth.oauth_provider_service import (
    OAuthProviderService, _clients, _auth_codes, _access_tokens,
)


class TestOAuthProviderService(unittest.TestCase):

    def setUp(self):
        _clients.clear()
        _auth_codes.clear()
        _access_tokens.clear()
        self.svc = OAuthProviderService()

    def tearDown(self):
        _clients.clear()
        _auth_codes.clear()
        _access_tokens.clear()

    # --- register_client ---

    def test_register_client_returns_credentials(self):
        result = self.svc.register_client('TestApp', ['http://localhost/cb'], ['read'])
        self.assertIn('client_id', result)
        self.assertIn('client_secret', result)
        self.assertTrue(len(result['client_id']) > 10)
        self.assertTrue(len(result['client_secret']) > 20)

    def test_register_client_stores_in_clients(self):
        result = self.svc.register_client('MyApp', ['http://example.com/cb'], ['read', 'write'])
        self.assertIn(result['client_id'], _clients)
        stored = _clients[result['client_id']]
        self.assertEqual(stored['name'], 'MyApp')
        self.assertEqual(stored['redirect_uris'], ['http://example.com/cb'])

    def test_register_client_hashes_secret(self):
        result = self.svc.register_client('App', ['http://x/cb'], ['read'])
        stored = _clients[result['client_id']]
        expected_hash = hashlib.sha256(result['client_secret'].encode()).hexdigest()
        self.assertEqual(stored['secret_hash'], expected_hash)

    # --- create_authorization_code ---

    def test_create_auth_code_success(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
        )
        self.assertIsNotNone(code)
        self.assertIn(code, _auth_codes)

    def test_create_auth_code_unknown_client(self):
        code = self.svc.create_authorization_code('bad_id', 'user1', 'read', 'http://x/cb')
        self.assertIsNone(code)

    def test_create_auth_code_wrong_redirect(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://wrong/cb',
        )
        self.assertIsNone(code)

    # --- exchange_code_for_token ---

    def test_exchange_code_success(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
        )
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], creds['client_secret'], 'http://x/cb',
        )
        self.assertIn('access_token', result)
        self.assertEqual(result['token_type'], 'Bearer')
        self.assertEqual(result['scope'], 'read')

    def test_exchange_code_invalid_code(self):
        result = self.svc.exchange_code_for_token('bad_code', 'cid', 'sec', 'http://x/cb')
        self.assertEqual(result['error'], 'invalid_grant')

    def test_exchange_code_wrong_secret(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
        )
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], 'wrong_secret', 'http://x/cb',
        )
        self.assertEqual(result['error'], 'invalid_client')

    def test_exchange_code_expired(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
        )
        # 만료시키기
        _auth_codes[code]['expires_at'] = time.time() - 1
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], creds['client_secret'], 'http://x/cb',
        )
        self.assertEqual(result['error'], 'invalid_grant')

    def test_exchange_code_wrong_redirect(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
        )
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], creds['client_secret'], 'http://wrong/cb',
        )
        self.assertEqual(result['error'], 'invalid_grant')

    # --- PKCE ---

    def test_pkce_flow(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        verifier = 'test_code_verifier_string_1234567890'
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b'=').decode()

        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
            code_challenge=challenge,
        )
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], creds['client_secret'], 'http://x/cb',
            code_verifier=verifier,
        )
        self.assertIn('access_token', result)

    def test_pkce_wrong_verifier(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(b'correct_verifier').digest()
        ).rstrip(b'=').decode()

        code = self.svc.create_authorization_code(
            creds['client_id'], 'user1', 'read', 'http://x/cb',
            code_challenge=challenge,
        )
        result = self.svc.exchange_code_for_token(
            code, creds['client_id'], creds['client_secret'], 'http://x/cb',
            code_verifier='wrong_verifier',
        )
        self.assertEqual(result['error'], 'invalid_grant')

    # --- client_credentials_token ---

    def test_client_credentials_success(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['admin'])
        result = self.svc.client_credentials_token(
            creds['client_id'], creds['client_secret'], 'admin',
        )
        self.assertIn('access_token', result)
        self.assertIsNone(_access_tokens[result['access_token']]['user_id'])

    def test_client_credentials_wrong_secret(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['admin'])
        result = self.svc.client_credentials_token(creds['client_id'], 'bad', 'admin')
        self.assertEqual(result['error'], 'invalid_client')

    def test_client_credentials_unknown_client(self):
        result = self.svc.client_credentials_token('unknown', 'sec', 'admin')
        self.assertEqual(result['error'], 'invalid_client')

    # --- validate_token ---

    def test_validate_token_success(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        token_result = self.svc.client_credentials_token(
            creds['client_id'], creds['client_secret'], 'read',
        )
        data = self.svc.validate_token(token_result['access_token'])
        self.assertIsNotNone(data)
        self.assertEqual(data['scope'], 'read')

    def test_validate_token_invalid(self):
        self.assertIsNone(self.svc.validate_token('nonexistent'))

    def test_validate_token_expired(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        token_result = self.svc.client_credentials_token(
            creds['client_id'], creds['client_secret'], 'read',
        )
        token = token_result['access_token']
        _access_tokens[token]['expires_at'] = time.time() - 1
        self.assertIsNone(self.svc.validate_token(token))
        self.assertNotIn(token, _access_tokens)

    # --- revoke_token ---

    def test_revoke_token_success(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        token_result = self.svc.client_credentials_token(
            creds['client_id'], creds['client_secret'], 'read',
        )
        self.assertTrue(self.svc.revoke_token(token_result['access_token']))
        self.assertIsNone(self.svc.validate_token(token_result['access_token']))

    def test_revoke_token_nonexistent(self):
        self.assertFalse(self.svc.revoke_token('nonexistent'))

    # --- list_clients ---

    def test_list_clients(self):
        self.svc.register_client('App1', ['http://a/cb'], ['read'])
        self.svc.register_client('App2', ['http://b/cb'], ['write'])
        clients = self.svc.list_clients()
        self.assertEqual(len(clients), 2)
        names = {c['name'] for c in clients}
        self.assertEqual(names, {'App1', 'App2'})
        # 시크릿 노출 안 됨
        for c in clients:
            self.assertNotIn('secret_hash', c)

    # --- get_active_token_count ---

    def test_active_token_count(self):
        creds = self.svc.register_client('App', ['http://x/cb'], ['read'])
        self.assertEqual(self.svc.get_active_token_count(), 0)
        self.svc.client_credentials_token(creds['client_id'], creds['client_secret'], 'read')
        self.svc.client_credentials_token(creds['client_id'], creds['client_secret'], 'read')
        self.assertEqual(self.svc.get_active_token_count(), 2)


if __name__ == '__main__':
    unittest.main()
