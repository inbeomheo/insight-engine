"""R29: /api/providers 응답에 프로바이더별 model_count 필드 포함 테스트"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app


class TestProvidersModelCount(unittest.TestCase):
    """/api/providers 응답의 model_count 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_each_provider_has_model_count(self, mock_providers, mock_supa):
        """각 프로바이더에 model_count 필드가 존재하는지 확인"""
        mock_providers.return_value = {
            'gemini': {
                'name': 'Google Gemini',
                'models': [
                    {'id': 'gemini/flash', 'name': 'Flash'},
                    {'id': 'gemini/pro', 'name': 'Pro'},
                ]
            },
            'deepseek': {
                'name': 'DeepSeek',
                'models': [
                    {'id': 'deepseek/chat', 'name': 'Chat'},
                ]
            }
        }

        resp = self.client.get('/api/providers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        for pid, pdata in data['providers'].items():
            self.assertIn('model_count', pdata, f'{pid}에 model_count 없음')
            self.assertIsInstance(pdata['model_count'], int)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_model_count_matches_actual_models(self, mock_providers, mock_supa):
        """model_count 값이 실제 models 리스트 길이와 일치하는지 확인"""
        mock_providers.return_value = {
            'gemini': {
                'name': 'Google Gemini',
                'models': [{'id': f'gemini/m{i}', 'name': f'M{i}'} for i in range(3)]
            },
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertEqual(data['providers']['gemini']['model_count'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_empty_models_returns_zero(self, mock_providers, mock_supa):
        """models가 빈 리스트일 때 model_count가 0인지 확인"""
        mock_providers.return_value = {
            'empty': {'name': 'Empty Provider', 'models': []}
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertEqual(data['providers']['empty']['model_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_missing_models_key_returns_zero(self, mock_providers, mock_supa):
        """models 키가 없는 프로바이더에서 model_count가 0인지 확인"""
        mock_providers.return_value = {
            'no_models': {'name': 'No Models'}
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertEqual(data['providers']['no_models']['model_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_existing_fields_preserved(self, mock_providers, mock_supa):
        """기존 필드(name, models, styles 등)가 보존되는지 확인"""
        mock_providers.return_value = {
            'gemini': {
                'name': 'Google Gemini',
                'models': [{'id': 'gemini/flash', 'name': 'Flash'}]
            }
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertIn('name', data['providers']['gemini'])
        self.assertIn('models', data['providers']['gemini'])
        self.assertIn('styles', data)
        self.assertIn('supadataConfigured', data)
        self.assertIn('hasAutoFallback', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_generation_diagnostics_limited_to_chatmock_and_glm(self, mock_providers, mock_supa):
        """생성용 진단 메타데이터는 ChatMock/GLM만 포함한다."""
        mock_providers.return_value = {
            'chatmock': {
                'name': 'ChatMock',
                'api_base': 'http://127.0.0.1:8000/v1',
                'models': [{'id': 'chatmock/gpt-5.3-codex-spark', 'name': 'Spark'}],
            },
            'zhipuai': {
                'name': 'Zhipu AI (GLM)',
                'api_base': 'https://open.bigmodel.cn/api/paas/v4/',
                'models': [{'id': 'zhipuai/GLM-4.7', 'name': 'GLM-4.7'}],
            },
            'deepseek': {
                'name': 'DeepSeek',
                'models': [{'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek Chat'}],
            },
            'ollama': {
                'name': 'Ollama',
                'api_base': 'http://localhost:11434',
                'models': [{'id': 'ollama_chat/llama3.2', 'name': 'Llama 3.2'}],
            },
        }

        with patch.dict('os.environ', {'ZAI_API_KEY': 'test-key'}, clear=False):
            resp = self.client.get('/api/providers')

        data = resp.get_json()
        self.assertEqual(set(data['providerDiagnostics'].keys()), {'chatmock', 'zhipuai'})
        self.assertNotIn('deepseek', data['providerDiagnostics'])
        self.assertNotIn('ollama', data['providerDiagnostics'])
        self.assertEqual(data['providers']['chatmock']['health']['status'], 'ready')
        self.assertEqual(data['providers']['zhipuai']['health']['status'], 'ready')
        self.assertTrue(data['providers']['zhipuai']['diagnostics']['api_key_configured'])


if __name__ == '__main__':
    unittest.main()
