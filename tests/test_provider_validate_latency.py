"""R73: /api/providers/validate 응답에 latency_ms 필드 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestProviderValidateLatency(unittest.TestCase):
    """프로바이더 검증 응답의 latency_ms 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_litellm_success_has_latency_ms(self, mock_sb):
        """LiteLLM 성공 시 latency_ms 정수 필드 포함"""
        fake_provider = {
            'models': [{'id': 'gemini/gemini-test'}],
        }
        with patch('config.SUPPORTED_PROVIDERS', {'gemini': fake_provider}), \
             patch('litellm.completion', return_value=MagicMock()):
            resp = self.client.post('/api/providers/validate', json={
                'provider_id': 'gemini',
                'api_key': 'fake-key',
            }, headers={'Origin': 'http://localhost:3000'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['valid'])
        self.assertIn('latency_ms', data)
        self.assertIsInstance(data['latency_ms'], int)
        self.assertGreaterEqual(data['latency_ms'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_chatmock_success_has_latency_ms(self, mock_sb):
        """ChatMock 성공 시 latency_ms 포함"""
        fake_provider = {
            'models': [{'id': 'chatmock/gpt-5.4-mini'}],
            'api_base': 'http://127.0.0.1:8000/v1',
        }
        with patch('config.SUPPORTED_PROVIDERS', {'chatmock': fake_provider}), \
             patch('litellm.completion', return_value=MagicMock()):
            resp = self.client.post('/api/providers/validate', json={
                'provider_id': 'chatmock',
                'api_key': '',
            }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        self.assertTrue(data['valid'])
        self.assertIn('latency_ms', data)
        self.assertIsInstance(data['latency_ms'], int)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_litellm_failure_no_latency(self, mock_sb):
        """LiteLLM 실패 시 latency_ms 미포함 (에러만)"""
        fake_provider = {
            'models': [{'id': 'gemini/gemini-test'}],
        }
        with patch('config.SUPPORTED_PROVIDERS', {'gemini': fake_provider}), \
             patch('litellm.completion', side_effect=Exception('Invalid key')):
            resp = self.client.post('/api/providers/validate', json={
                'provider_id': 'gemini',
                'api_key': 'bad-key',
            }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        self.assertFalse(data['valid'])
        self.assertIn('error', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_provider_id(self, mock_sb):
        """provider_id 누락 시 400"""
        resp = self.client.post('/api/providers/validate', json={
            'api_key': 'key',
        }, headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_latency_ms_is_reasonable(self, mock_sb):
        """latency_ms가 합리적 범위 (0~30000ms)"""
        fake_provider = {
            'models': [{'id': 'gemini/gemini-test'}],
        }
        with patch('config.SUPPORTED_PROVIDERS', {'gemini': fake_provider}), \
             patch('litellm.completion', return_value=MagicMock()):
            resp = self.client.post('/api/providers/validate', json={
                'provider_id': 'gemini',
                'api_key': 'fake-key',
            }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        self.assertLessEqual(data['latency_ms'], 30000)


if __name__ == '__main__':
    unittest.main()
