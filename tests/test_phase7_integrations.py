"""
Phase 7 통합 & 플러그인 테스트 (F7-01 ~ F7-25)
"""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── F7-01 Chrome 확장 파일 존재 확인 ──────────────────────────────────────


class TestChromeExtension(unittest.TestCase):
    BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chrome-extension')

    def test_manifest_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.BASE, 'manifest.json')))

    def test_manifest_v3(self):
        with open(os.path.join(self.BASE, 'manifest.json'), encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['manifest_version'], 3)
        self.assertIn('action', data)
        self.assertIn('content_scripts', data)

    def test_popup_html_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.BASE, 'popup.html')))

    def test_content_js_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.BASE, 'content.js')))

    def test_background_js_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.BASE, 'background.js')))


# ── F7-02 Slack 봇 ──────────────────────────────────────


class TestSlackBotService(unittest.TestCase):
    def setUp(self):
        from services.integrations.slack_bot_service import SlackBotService
        self.service = SlackBotService()

    def test_url_verification_challenge(self):
        result = self.service.handle_event({'type': 'url_verification', 'challenge': 'test_challenge'})
        self.assertEqual(result['challenge'], 'test_challenge')

    def test_bot_message_ignored(self):
        result = self.service.handle_event({
            'event': {'type': 'message', 'bot_id': 'B123', 'text': 'hello'}
        })
        self.assertEqual(result, {'ok': True})

    def test_youtube_url_detected(self):
        with patch.object(self.service, '_send_message', return_value=None):
            result = self.service.handle_event({
                'event': {
                    'type': 'message',
                    'text': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'channel': 'C123',
                }
            })
        self.assertEqual(result['ok'], True)
        self.assertIn('url', result)

    def test_is_configured_false_without_env(self):
        self.service.bot_token = ''
        self.service.signing_secret = ''
        self.assertFalse(self.service.is_configured)


# ── F7-03 Discord 봇 ──────────────────────────────────────


class TestDiscordBotService(unittest.TestCase):
    def setUp(self):
        from services.integrations.discord_bot_service import DiscordBotService
        self.service = DiscordBotService()

    def test_ping_pong(self):
        result = self.service.handle_interaction({'type': 1})
        self.assertEqual(result['type'], 1)

    def test_generate_command_valid_url(self):
        result = self.service.handle_interaction({
            'type': 2,
            'data': {
                'name': 'generate',
                'options': [
                    {'name': 'url', 'value': 'https://www.youtube.com/watch?v=abc123'},
                    {'name': 'style', 'value': 'blog_seo'},
                ],
            },
        })
        self.assertEqual(result['type'], 4)
        self.assertIn('content', result['data'])

    def test_generate_command_invalid_url(self):
        result = self.service.handle_interaction({
            'type': 2,
            'data': {
                'name': 'generate',
                'options': [{'name': 'url', 'value': 'https://example.com'}],
            },
        })
        self.assertIn('❌', result['data']['content'])


# ── F7-04 Telegram 봇 ──────────────────────────────────────


class TestTelegramBotService(unittest.TestCase):
    def setUp(self):
        from services.integrations.telegram_bot_service import TelegramBotService
        self.service = TelegramBotService()

    def test_start_command(self):
        with patch.object(self.service, '_send_message', return_value=None):
            result = self.service.handle_update({
                'message': {'text': '/start', 'chat': {'id': 123}}
            })
        self.assertEqual(result['ok'], True)

    def test_styles_command(self):
        with patch.object(self.service, '_send_message', return_value=None):
            result = self.service.handle_update({
                'message': {'text': '/styles', 'chat': {'id': 123}}
            })
        self.assertEqual(result['ok'], True)

    def test_youtube_url_triggers_keyboard(self):
        with patch.object(self.service, '_send_message', return_value=None):
            result = self.service.handle_update({
                'message': {
                    'text': 'https://www.youtube.com/watch?v=test123',
                    'chat': {'id': 456}
                }
            })
        self.assertEqual(result['ok'], True)

    def test_generate_command_invalid_url(self):
        with patch.object(self.service, '_send_message', return_value=None):
            result = self.service.handle_update({
                'message': {'text': '/generate https://example.com', 'chat': {'id': 789}}
            })
        self.assertEqual(result['ok'], True)


# ── F7-08 OpenAPI ──────────────────────────────────────


class TestOpenAPIService(unittest.TestCase):
    def setUp(self):
        from services.openapi_service import build_openapi_spec
        self.spec = build_openapi_spec()

    def test_openapi_version(self):
        self.assertEqual(self.spec['openapi'], '3.0.3')

    def test_has_info(self):
        self.assertIn('info', self.spec)
        self.assertIn('title', self.spec['info'])
        self.assertIn('version', self.spec['info'])

    def test_has_paths(self):
        self.assertIn('paths', self.spec)
        self.assertIn('/generate', self.spec['paths'])
        self.assertIn('/api/mcp/plugins', self.spec['paths'])

    def test_has_components(self):
        self.assertIn('components', self.spec)
        self.assertIn('schemas', self.spec['components'])
        self.assertIn('GenerateRequest', self.spec['components']['schemas'])
        self.assertIn('GenerateResponse', self.spec['components']['schemas'])

    def test_security_scheme(self):
        self.assertIn('securitySchemes', self.spec['components'])
        self.assertIn('BearerAuth', self.spec['components']['securitySchemes'])


# ── F7-09 GraphQL ──────────────────────────────────────


class TestGraphQL(unittest.TestCase):
    def setUp(self):
        from routes.graphql_routes import execute_graphql
        self.execute = execute_graphql

    def test_ping_query(self):
        result = self.execute('{ ping }')
        self.assertIn('data', result)
        self.assertEqual(result['data']['ping'], 'pong')

    def test_introspection_query(self):
        result = self.execute('{ __schema { types { name } } }')
        self.assertIn('data', result)
        self.assertIn('__schema', result['data'])

    def test_unknown_query(self):
        result = self.execute('{ unknownField }')
        self.assertIn('errors', result)

    def test_plugins_query(self):
        with patch('routes.graphql_routes.resolve_plugins', return_value=[
            {'id': 'test', 'name': 'Test Plugin', 'description': 'Test'}
        ]):
            result = self.execute('{ plugins { id name description } }')
        self.assertIn('data', result)
        self.assertIn('plugins', result['data'])


# ── F7-10 Plugin SDK ──────────────────────────────────────


class TestPluginSDK(unittest.TestCase):
    def test_plugin_base_validate_required(self):
        from services.mcp.plugin_sdk import PluginBase

        class TestPlugin(PluginBase):
            _name = 'Test'
            _description = 'Test plugin'
            SCHEMA = {
                'type': 'object',
                'properties': {'api_key': {'type': 'string'}},
                'required': ['api_key'],
            }

            def publish(self, title, content, **kwargs):
                return {'success': True, 'message': 'ok', 'url': None}

        p = TestPlugin()
        # 필수 필드 없으면 실패
        result = p.execute('content', 'title')
        self.assertFalse(result['success'])
        self.assertIn('api_key', result['message'])

        # 필수 필드 있으면 성공
        result = p.execute('content', 'title', api_key='test-key')
        self.assertTrue(result['success'])

    def test_plugin_decorator(self):
        from services.mcp.plugin_sdk import plugin, PluginBase
        from services.mcp.registry import plugin_registry

        @plugin(plugin_id='sdk_test_plugin', name='SDK Test', description='SDK 테스트')
        class SDKTestPlugin(PluginBase):
            def publish(self, title, content, **kwargs):
                return {'success': True, 'message': '테스트 성공', 'url': None}

        registered = plugin_registry.get('sdk_test_plugin')
        self.assertIsNotNone(registered)
        self.assertEqual(registered.name, 'SDK Test')


# ── F7-11 ~ F7-18 플러그인 인터페이스 ──────────────────────────────────────


class TestPluginInterfaces(unittest.TestCase):
    """각 플러그인이 MCPPlugin 인터페이스를 올바르게 구현하는지 확인"""

    def _check_plugin(self, plugin_cls):
        from services.mcp.plugin_interface import MCPPlugin
        p = plugin_cls()
        self.assertIsInstance(p, MCPPlugin)
        self.assertIsInstance(p.name, str)
        self.assertIsInstance(p.description, str)
        schema = p.schema()
        self.assertIsInstance(schema, dict)
        self.assertIn('type', schema)

    def test_tistory_plugin(self):
        from services.mcp.plugins.tistory import TistoryPlugin
        self._check_plugin(TistoryPlugin)

    def test_velog_plugin(self):
        from services.mcp.plugins.velog import VelogPlugin
        self._check_plugin(VelogPlugin)

    def test_ghost_plugin(self):
        from services.mcp.plugins.ghost import GhostPlugin
        self._check_plugin(GhostPlugin)

    def test_shopify_plugin(self):
        from services.mcp.plugins.shopify import ShopifyPlugin
        self._check_plugin(ShopifyPlugin)

    def test_linkedin_plugin(self):
        from services.mcp.plugins.linkedin import LinkedInPlugin
        self._check_plugin(LinkedInPlugin)

    def test_twitter_plugin(self):
        from services.mcp.plugins.twitter import TwitterPlugin
        self._check_plugin(TwitterPlugin)

    def test_instagram_plugin(self):
        from services.mcp.plugins.instagram import InstagramPlugin
        self._check_plugin(InstagramPlugin)

    def test_threads_plugin(self):
        from services.mcp.plugins.threads import ThreadsPlugin
        self._check_plugin(ThreadsPlugin)

    def test_missing_token_returns_failure(self):
        """토큰 없으면 execute() → success=False"""
        from services.mcp.plugins.tistory import TistoryPlugin
        p = TistoryPlugin()
        result = p.execute('content', 'title')
        self.assertFalse(result['success'])
        self.assertIsNone(result['url'])

    def test_ghost_jwt_wrong_format(self):
        from services.mcp.plugins.ghost import GhostPlugin
        p = GhostPlugin()
        result = p.execute('content', 'title', api_url='https://example.com', admin_api_key='invalid')
        self.assertFalse(result['success'])


# ── F7-19 Webhook Relay ──────────────────────────────────────


class TestWebhookRelayService(unittest.TestCase):
    def setUp(self):
        from services.webhook_relay_service import WebhookRelayService
        self.service = WebhookRelayService()

    def test_empty_urls(self):
        result = self.service.send_all([], {'event': 'test'})
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['success'], 0)

    def test_connection_error_handled(self):
        result = self.service.send_all(
            ['http://localhost:99999/nonexistent'],
            {'event': 'test'},
            timeout=1,
        )
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 1)
        self.assertFalse(result['results'][0]['success'])

    def test_relay_content_generated(self):
        with patch.object(self.service, 'send_all', return_value={'total': 1, 'success': 1, 'failed': 0, 'results': []}):
            result = self.service.relay_content_generated(
                ['http://example.com/webhook'],
                title='Test', content='Content', style='blog_seo',
            )
        self.assertEqual(result['success'], 1)


# ── F7-21 Airtable ──────────────────────────────────────


class TestAirtableService(unittest.TestCase):
    def setUp(self):
        from services.integrations.airtable_service import AirtableService
        self.service = AirtableService()
        self.service.api_key = ''
        self.service.base_id = ''

    def test_not_configured_returns_failure(self):
        result = self.service.sync_content('Title', 'Content', 'blog_seo')
        self.assertFalse(result['success'])
        self.assertIsNone(result['record_id'])

    def test_is_configured_false(self):
        self.assertFalse(self.service.is_configured)

    def test_is_configured_true(self):
        self.service.api_key = 'test'
        self.service.base_id = 'base123'
        self.assertTrue(self.service.is_configured)


# ── F7-22 Google Sheets ──────────────────────────────────────


class TestGoogleSheetsService(unittest.TestCase):
    def setUp(self):
        from services.integrations.gsheets_service import GoogleSheetsService
        self.service = GoogleSheetsService()
        self.service.api_key = ''
        self.service.spreadsheet_id = ''

    def test_not_configured_returns_failure(self):
        result = self.service.sync_content('Title', 'Content', 'blog_seo')
        self.assertFalse(result['success'])

    def test_is_configured(self):
        self.service.api_key = 'AIza...'
        self.service.spreadsheet_id = '1BxiM...'
        self.assertTrue(self.service.is_configured)


# ── F7-23 CMS Hub ──────────────────────────────────────


class TestCMSHub(unittest.TestCase):
    def setUp(self):
        from services.mcp.cms_hub import CMSHub
        self.hub = CMSHub()

    def test_empty_plugin_ids(self):
        result = self.hub.publish_to_all([], 'Title', 'Content')
        self.assertEqual(result['total'], 0)

    def test_unknown_plugin(self):
        result = self.hub.publish_to_all(['nonexistent_plugin'], 'Title', 'Content')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['failed'], 1)
        self.assertFalse(result['results']['nonexistent_plugin']['success'])

    def test_validate_config_unknown_plugin(self):
        result = self.hub.validate_plugin_config('nonexistent', {})
        self.assertFalse(result['valid'])
        self.assertTrue(len(result['errors']) > 0)

    def test_get_available_plugins(self):
        plugins = self.hub.get_available_plugins()
        self.assertIsInstance(plugins, list)


# ── F7-24 피드백 위젯 파일 존재 확인 ──────────────────────────────────────


class TestFeedbackWidget(unittest.TestCase):
    WIDGET_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'frontend', 'components', 'feedback', 'FeedbackWidget.tsx'
    )

    def test_widget_file_exists(self):
        self.assertTrue(os.path.exists(self.WIDGET_PATH))

    def test_widget_has_key_elements(self):
        with open(self.WIDGET_PATH, encoding='utf-8') as f:
            content = f.read()
        self.assertIn('FeedbackWidget', content)
        self.assertIn('rating', content)
        self.assertIn('comment', content)
        self.assertIn('apiEndpoint', content)


# ── F7-25 OAuth 2.0 ──────────────────────────────────────


class TestOAuthProviderService(unittest.TestCase):
    def setUp(self):
        from services.auth.oauth_provider_service import OAuthProviderService
        self.service = OAuthProviderService()
        # 테스트용 클라이언트 등록
        self.client_info = self.service.register_client(
            client_name='Test App',
            redirect_uris=['https://testapp.com/callback'],
            scopes=['read', 'write'],
        )

    def test_register_client(self):
        self.assertIn('client_id', self.client_info)
        self.assertIn('client_secret', self.client_info)
        self.assertTrue(len(self.client_info['client_id']) > 0)

    def test_list_clients(self):
        clients = self.service.list_clients()
        ids = [c['client_id'] for c in clients]
        self.assertIn(self.client_info['client_id'], ids)

    def test_authorization_code_flow(self):
        client_id = self.client_info['client_id']
        client_secret = self.client_info['client_secret']

        # 인가 코드 발급
        code = self.service.create_authorization_code(
            client_id=client_id,
            user_id='user123',
            scope='read',
            redirect_uri='https://testapp.com/callback',
        )
        self.assertIsNotNone(code)

        # 토큰 교환
        token_result = self.service.exchange_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri='https://testapp.com/callback',
        )
        self.assertIn('access_token', token_result)
        self.assertEqual(token_result['token_type'], 'Bearer')
        self.assertEqual(token_result['scope'], 'read')

    def test_invalid_code(self):
        result = self.service.exchange_code_for_token(
            code='invalid_code',
            client_id='any',
            client_secret='any',
            redirect_uri='https://example.com',
        )
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'invalid_grant')

    def test_client_credentials_flow(self):
        client_id = self.client_info['client_id']
        client_secret = self.client_info['client_secret']
        result = self.service.client_credentials_token(client_id, client_secret, 'read')
        self.assertIn('access_token', result)

    def test_wrong_secret(self):
        result = self.service.client_credentials_token(
            self.client_info['client_id'], 'wrong_secret', 'read'
        )
        self.assertIn('error', result)

    def test_validate_token(self):
        client_id = self.client_info['client_id']
        client_secret = self.client_info['client_secret']
        token_result = self.service.client_credentials_token(client_id, client_secret, 'read')
        token = token_result['access_token']

        data = self.service.validate_token(token)
        self.assertIsNotNone(data)
        self.assertEqual(data['client_id'], client_id)

    def test_revoke_token(self):
        client_id = self.client_info['client_id']
        client_secret = self.client_info['client_secret']
        token_result = self.service.client_credentials_token(client_id, client_secret, 'read')
        token = token_result['access_token']

        self.service.revoke_token(token)
        data = self.service.validate_token(token)
        self.assertIsNone(data)

    def test_invalid_redirect_uri(self):
        code = self.service.create_authorization_code(
            client_id=self.client_info['client_id'],
            user_id='user',
            scope='read',
            redirect_uri='https://malicious.com/callback',
        )
        self.assertIsNone(code)

    def test_unknown_client(self):
        code = self.service.create_authorization_code(
            client_id='unknown_client',
            user_id='user',
            scope='read',
            redirect_uri='https://testapp.com/callback',
        )
        self.assertIsNone(code)

    def test_get_active_token_count(self):
        count = self.service.get_active_token_count()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)

    def test_pkce_flow(self):
        import base64
        import hashlib

        code_verifier = 'test_verifier_1234567890abcdefghijklmnopqrstuv'
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b'=').decode()

        client_id = self.client_info['client_id']
        client_secret = self.client_info['client_secret']

        code = self.service.create_authorization_code(
            client_id=client_id,
            user_id='user_pkce',
            scope='read',
            redirect_uri='https://testapp.com/callback',
            code_challenge=code_challenge,
            code_challenge_method='S256',
        )
        self.assertIsNotNone(code)

        result = self.service.exchange_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri='https://testapp.com/callback',
            code_verifier=code_verifier,
        )
        self.assertIn('access_token', result)


# ── n8n 노드 파일 존재 확인 (F7-07) ──────────────────────────────────────


class TestN8nNode(unittest.TestCase):
    NODE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'n8n-nodes', 'InsightEngine.node.ts'
    )

    def test_node_file_exists(self):
        self.assertTrue(os.path.exists(self.NODE_PATH))

    def test_node_has_operations(self):
        with open(self.NODE_PATH, encoding='utf-8') as f:
            content = f.read()
        self.assertIn('generate', content)
        self.assertIn('listPlugins', content)
        self.assertIn('publish', content)
        self.assertIn('INodeType', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
