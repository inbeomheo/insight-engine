"""R60: /api/providers 응답에 프로바이더별 default_model 필드 포함 테스트"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app


class TestProvidersDefaultModel(unittest.TestCase):
    """/api/providers 응답의 default_model 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_default_model_is_first_model(self, mock_providers, _):
        """default_model이 models 리스트의 첫 번째 모델 id인지 확인"""
        mock_providers.return_value = {
            'gemini': {
                'name': 'Google Gemini',
                'models': [
                    {'id': 'gemini/flash', 'name': 'Flash'},
                    {'id': 'gemini/pro', 'name': 'Pro'},
                ]
            },
        }

        resp = self.client.get('/api/providers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['providers']['gemini']['default_model'], 'gemini/flash')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_default_model_none_when_no_models(self, mock_providers, _):
        """models가 빈 리스트일 때 default_model이 None인지 확인"""
        mock_providers.return_value = {
            'empty': {'name': 'Empty', 'models': []}
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertIsNone(data['providers']['empty']['default_model'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_default_model_none_when_models_key_missing(self, mock_providers, _):
        """models 키가 없을 때 default_model이 None인지 확인"""
        mock_providers.return_value = {
            'no_models': {'name': 'No Models'}
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertIsNone(data['providers']['no_models']['default_model'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.get_available_providers')
    def test_multiple_providers_each_have_default(self, mock_providers, _):
        """여러 프로바이더 각각 default_model 포함"""
        mock_providers.return_value = {
            'gemini': {
                'name': 'Gemini',
                'models': [{'id': 'gemini/flash', 'name': 'Flash'}]
            },
            'deepseek': {
                'name': 'DeepSeek',
                'models': [{'id': 'deepseek/chat', 'name': 'Chat'}]
            },
        }

        resp = self.client.get('/api/providers')
        data = resp.get_json()
        self.assertEqual(data['providers']['gemini']['default_model'], 'gemini/flash')
        self.assertEqual(data['providers']['deepseek']['default_model'], 'deepseek/chat')

    def test_backend_default_model_is_production_model(self):
        """명시 모델이 없을 때 제품 기본은 운영 GLM 모델이다."""
        from routes.blog_routes import DEFAULT_MODEL

        self.assertEqual(DEFAULT_MODEL, 'zhipuai/GLM-4.5-Air')


if __name__ == '__main__':
    unittest.main()
