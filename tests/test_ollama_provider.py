"""
Ollama 프로바이더 통합 테스트
config 등록, 모델 매핑, health check 엔드포인트 검증
"""
import unittest
from unittest.mock import patch, MagicMock


class TestOllamaProviderConfig(unittest.TestCase):
    """Ollama 프로바이더 설정 테스트"""

    def test_ollama_in_supported_providers(self):
        """SUPPORTED_PROVIDERS에 ollama 존재 확인"""
        from config import SUPPORTED_PROVIDERS

        self.assertIn('ollama', SUPPORTED_PROVIDERS)

    def test_ollama_has_required_fields(self):
        """ollama 프로바이더 구조 검증"""
        from config import SUPPORTED_PROVIDERS

        ollama = SUPPORTED_PROVIDERS['ollama']
        self.assertIn('name', ollama)
        self.assertIn('models', ollama)
        self.assertIn('api_base', ollama)
        self.assertEqual(ollama['name'], 'Ollama (로컬)')

    def test_ollama_has_models(self):
        """ollama에 최소 1개 모델 존재"""
        from config import SUPPORTED_PROVIDERS

        models = SUPPORTED_PROVIDERS['ollama']['models']
        self.assertGreater(len(models), 0)

    def test_ollama_models_have_zero_price(self):
        """ollama 모델은 무료 (price=0)"""
        from config import SUPPORTED_PROVIDERS

        for model in SUPPORTED_PROVIDERS['ollama']['models']:
            self.assertEqual(model['price_input'], 0)
            self.assertEqual(model['price_output'], 0)

    def test_ollama_model_ids_have_correct_prefix(self):
        """ollama 모델 ID는 ollama_chat/ 접두사"""
        from config import SUPPORTED_PROVIDERS

        for model in SUPPORTED_PROVIDERS['ollama']['models']:
            self.assertTrue(
                model['id'].startswith('ollama_chat/'),
                f"모델 ID '{model['id']}'가 ollama_chat/로 시작하지 않음"
            )


class TestOllamaProviderMapping(unittest.TestCase):
    """get_provider_from_model Ollama 매핑 테스트"""

    def test_ollama_chat_prefix(self):
        """ollama_chat/ 접두사 → ollama"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('ollama_chat/llama3.2'), 'ollama')
        self.assertEqual(get_provider_from_model('ollama_chat/mistral'), 'ollama')
        self.assertEqual(get_provider_from_model('ollama_chat/gemma2'), 'ollama')

    def test_ollama_prefix(self):
        """ollama/ 접두사 → ollama"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('ollama/llama3'), 'ollama')


class TestOllamaApiKeys(unittest.TestCase):
    """Ollama API 키 (Base URL) 설정 테스트"""

    def test_ollama_in_provider_api_keys(self):
        """PROVIDER_API_KEYS에 ollama 존재"""
        from config import PROVIDER_API_KEYS

        self.assertIn('ollama', PROVIDER_API_KEYS)

    def test_ollama_default_base_url(self):
        """OLLAMA_BASE_URL 미설정 시 기본값 사용"""
        from config import SUPPORTED_PROVIDERS

        api_base = SUPPORTED_PROVIDERS['ollama']['api_base']
        self.assertIn('localhost', api_base)
        self.assertIn('11434', api_base)


class TestOllamaAvailability(unittest.TestCase):
    """get_available_providers Ollama 활성화 테스트"""

    def test_ollama_available_with_default_url(self):
        """기본 OLLAMA_BASE_URL이 있으면 ollama 활성화"""
        from config import get_available_providers

        providers = get_available_providers()
        # 기본값 'http://localhost:11434'가 truthy이므로 활성화
        self.assertIn('ollama', providers)


class TestOllamaHealthEndpoint(unittest.TestCase):
    """Ollama health check 엔드포인트 테스트"""

    def setUp(self):
        """Flask 테스트 클라이언트 생성"""
        import app as flask_app
        self.app = flask_app.create_app()
        self.client = self.app.test_client()

    @patch('requests.get')
    def test_health_ok(self, mock_get):
        """Ollama 서버 정상 연결 시 200 + 모델 목록 반환"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'models': [
                {'name': 'llama3.2:latest'},
                {'name': 'mistral:latest'},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        resp = self.client.get('/api/ollama/health')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertIn('llama3.2:latest', data['models'])

    @patch('requests.get')
    def test_health_fail(self, mock_get):
        """Ollama 서버 연결 실패 시 503 반환"""
        mock_get.side_effect = ConnectionError('Connection refused')

        resp = self.client.get('/api/ollama/health')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 503)
        self.assertFalse(data['ok'])
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
