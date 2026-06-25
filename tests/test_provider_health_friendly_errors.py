"""Provider health diagnostics and friendly generation error context tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app
from routes.blog_routes import _build_provider_error_context


class TestProviderHealthFriendlyErrors(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_chatmock_error_context_has_safe_korean_action(self):
        ctx = _build_provider_error_context(
            'Connection refused api_key=SHOULD_NOT_APPEAR bearer SHOULD_NOT_APPEAR',
            'chatmock/gpt-5.3-codex-spark',
        )

        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx['provider_id'], 'chatmock')
        self.assertIn('ChatMock', ctx['provider_label'])
        self.assertIn('연결', ctx['reason'])
        self.assertIn('CHATMOCK_BASE_URL', ctx['action'])
        self.assertNotIn('SHOULD_NOT_APPEAR', str(ctx))

    def test_glm_error_context_explains_missing_key_without_value(self):
        ctx = _build_provider_error_context(
            'ZAI_API_KEY 환경변수가 설정되지 않았습니다.',
            'zhipuai/GLM-4.7',
        )

        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx['provider_id'], 'zhipuai')
        self.assertIn('GLM', ctx['provider_label'])
        self.assertIn('API 키', ctx['reason'])
        self.assertFalse(ctx['retryable'])
        self.assertIn('ZAI_API_KEY', ctx['action'])

    def test_hidden_provider_has_no_generation_error_context(self):
        ctx = _build_provider_error_context(
            'DeepSeek connection failed',
            'deepseek/deepseek-chat',
        )

        self.assertIsNone(ctx)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_provider_response_has_safe_generation_diagnostics(self, mock_providers, _):
        mock_providers.return_value = {
            'chatmock': {
                'name': 'ChatMock',
                'api_base': 'http://127.0.0.1:8000/v1',
                'models': [{'id': 'chatmock/gpt-5.3-codex-spark', 'name': 'Spark'}],
            },
            'deepseek': {
                'name': 'DeepSeek',
                'models': [{'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek Chat'}],
            },
        }

        resp = self.client.get('/api/providers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn('style_options', data)
        self.assertEqual(set(data['providerDiagnostics'].keys()), {'chatmock', 'zhipuai'})
        self.assertIn('safe_summary', data['providerDiagnostics']['chatmock']['diagnostics'])
        self.assertNotIn('deepseek', data['providerDiagnostics'])
        self.assertNotIn('ollama', data['providerDiagnostics'])


if __name__ == '__main__':
    unittest.main()
