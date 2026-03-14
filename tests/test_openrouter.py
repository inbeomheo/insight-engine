"""
OpenRouter 프로바이더 통합 테스트
config 등록, 모델 매핑, LiteLLM 호출 구조 검증
"""
import unittest
from unittest.mock import patch, MagicMock


class TestOpenRouterProviderConfig(unittest.TestCase):
    """OpenRouter 프로바이더 설정 테스트"""

    def test_openrouter_in_supported_providers(self):
        """SUPPORTED_PROVIDERS에 openrouter 존재 확인"""
        from config import SUPPORTED_PROVIDERS

        self.assertIn('openrouter', SUPPORTED_PROVIDERS)

    def test_openrouter_has_required_fields(self):
        """openrouter 프로바이더 구조 검증"""
        from config import SUPPORTED_PROVIDERS

        provider = SUPPORTED_PROVIDERS['openrouter']
        self.assertIn('name', provider)
        self.assertIn('models', provider)
        self.assertIn('api_base', provider)

    def test_openrouter_api_base_url(self):
        """api_base가 OpenRouter URL로 설정됨"""
        from config import SUPPORTED_PROVIDERS

        api_base = SUPPORTED_PROVIDERS['openrouter']['api_base']
        self.assertEqual(api_base, 'https://openrouter.ai/api/v1')

    def test_openrouter_has_models(self):
        """openrouter에 최소 1개 모델 존재"""
        from config import SUPPORTED_PROVIDERS

        models = SUPPORTED_PROVIDERS['openrouter']['models']
        self.assertGreater(len(models), 0)

    def test_openrouter_model_ids_have_correct_prefix(self):
        """openrouter 모델 ID는 openrouter/ 접두사"""
        from config import SUPPORTED_PROVIDERS

        for model in SUPPORTED_PROVIDERS['openrouter']['models']:
            self.assertTrue(
                model['id'].startswith('openrouter/'),
                f"모델 ID '{model['id']}'가 openrouter/로 시작하지 않음"
            )

    def test_openrouter_models_have_required_fields(self):
        """모든 모델에 필수 필드 존재"""
        from config import SUPPORTED_PROVIDERS

        required = {'id', 'name', 'max_input_tokens', 'price_input', 'price_output'}
        for model in SUPPORTED_PROVIDERS['openrouter']['models']:
            for field in required:
                self.assertIn(field, model, f"모델 '{model.get('id')}' 에 '{field}' 필드 없음")

    def test_openrouter_contains_popular_models(self):
        """지정된 4개 인기 모델 포함 여부"""
        from config import SUPPORTED_PROVIDERS

        model_ids = {m['id'] for m in SUPPORTED_PROVIDERS['openrouter']['models']}
        expected = [
            'openrouter/anthropic/claude-sonnet-4',
            'openrouter/google/gemini-2.5-flash',
            'openrouter/meta-llama/llama-4-scout',
            'openrouter/mistralai/mistral-large-2',
        ]
        for mid in expected:
            self.assertIn(mid, model_ids, f"'{mid}' 모델이 openrouter 목록에 없음")


class TestOpenRouterProviderMapping(unittest.TestCase):
    """get_provider_from_model OpenRouter 매핑 테스트"""

    def test_openrouter_prefix_mapping(self):
        """openrouter/ 접두사 → openrouter"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('openrouter/anthropic/claude-sonnet-4'), 'openrouter')
        self.assertEqual(get_provider_from_model('openrouter/google/gemini-2.5-flash'), 'openrouter')
        self.assertEqual(get_provider_from_model('openrouter/meta-llama/llama-4-scout'), 'openrouter')
        self.assertEqual(get_provider_from_model('openrouter/mistralai/mistral-large-2'), 'openrouter')

    def test_other_providers_not_affected(self):
        """OpenRouter 추가 후 기존 프로바이더 매핑 불변"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('deepseek/deepseek-chat'), 'deepseek')
        self.assertEqual(get_provider_from_model('zhipuai/GLM-4.7'), 'zhipuai')
        self.assertEqual(get_provider_from_model('ollama_chat/llama3.2'), 'ollama')
        self.assertEqual(get_provider_from_model('gemini/gemini-2.5-flash'), 'gemini')


class TestOpenRouterApiKeyConfig(unittest.TestCase):
    """OpenRouter API 키 설정 테스트"""

    def test_openrouter_in_provider_api_keys(self):
        """PROVIDER_API_KEYS에 openrouter 존재"""
        from config import PROVIDER_API_KEYS

        self.assertIn('openrouter', PROVIDER_API_KEYS)

    def test_openrouter_reads_env_var(self):
        """OPENROUTER_API_KEY 환경변수 읽기"""
        import importlib
        import config

        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'sk-or-test-key'}):
            importlib.reload(config)
            self.assertEqual(config.PROVIDER_API_KEYS['openrouter'], 'sk-or-test-key')

        # 테스트 후 원상복구
        importlib.reload(config)

    def test_openrouter_empty_by_default(self):
        """OPENROUTER_API_KEY 미설정 시 빈 문자열"""
        import importlib
        import config

        with patch.dict('os.environ', {}, clear=False):
            # OPENROUTER_API_KEY가 없는 상태 시뮬레이션
            env_backup = __import__('os').environ.pop('OPENROUTER_API_KEY', None)
            importlib.reload(config)
            self.assertEqual(config.PROVIDER_API_KEYS.get('openrouter', ''), '')
            if env_backup:
                __import__('os').environ['OPENROUTER_API_KEY'] = env_backup
            importlib.reload(config)


class TestOpenRouterAvailability(unittest.TestCase):
    """get_available_providers OpenRouter 활성화 테스트"""

    def test_openrouter_not_available_without_key(self):
        """OPENROUTER_API_KEY 미설정 시 openrouter 비활성화"""
        import importlib
        import config

        env_backup = __import__('os').environ.pop('OPENROUTER_API_KEY', None)
        importlib.reload(config)

        providers = config.get_available_providers()
        self.assertNotIn('openrouter', providers)

        if env_backup:
            __import__('os').environ['OPENROUTER_API_KEY'] = env_backup
        importlib.reload(config)

    def test_openrouter_available_with_key(self):
        """OPENROUTER_API_KEY 설정 시 openrouter 활성화"""
        import importlib
        import config

        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'sk-or-test-key'}):
            importlib.reload(config)
            providers = config.get_available_providers()
            self.assertIn('openrouter', providers)

        importlib.reload(config)


class TestOpenRouterCompletionKwargs(unittest.TestCase):
    """_build_completion_kwargs에서 OpenRouter 설정 검증"""

    def test_openrouter_api_base_injected(self):
        """openrouter/ 모델 → api_base와 api_key가 kwargs에 주입됨"""
        from services.core.ai_service import _build_completion_kwargs
        import app as flask_app

        flask_application = flask_app.create_app()
        with flask_application.app_context():
            with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'sk-or-test-key'}):
                kwargs = _build_completion_kwargs(
                    model='openrouter/anthropic/claude-sonnet-4',
                    prompt='테스트 프롬프트'
                )
                self.assertEqual(kwargs['api_base'], 'https://openrouter.ai/api/v1')
                self.assertEqual(kwargs['api_key'], 'sk-or-test-key')

    def test_openrouter_raises_without_api_key(self):
        """OPENROUTER_API_KEY 미설정 시 ValueError 발생"""
        from services.core.ai_service import _build_completion_kwargs
        import app as flask_app
        import os

        flask_application = flask_app.create_app()
        with flask_application.app_context():
            env_backup = os.environ.pop('OPENROUTER_API_KEY', None)
            try:
                with self.assertRaises(ValueError) as ctx:
                    _build_completion_kwargs(
                        model='openrouter/anthropic/claude-sonnet-4',
                        prompt='테스트 프롬프트'
                    )
                self.assertIn('OPENROUTER_API_KEY', str(ctx.exception))
            finally:
                if env_backup:
                    os.environ['OPENROUTER_API_KEY'] = env_backup

    def test_non_openrouter_model_not_affected(self):
        """openrouter/ 아닌 모델은 api_base 미주입"""
        from services.core.ai_service import _build_completion_kwargs
        import app as flask_app

        flask_application = flask_app.create_app()
        with flask_application.app_context():
            with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                kwargs = _build_completion_kwargs(
                    model='gemini/gemini-2.5-flash',
                    prompt='테스트 프롬프트'
                )
                # openrouter api_base가 주입되지 않아야 함
                self.assertNotEqual(
                    kwargs.get('api_base', ''),
                    'https://openrouter.ai/api/v1'
                )


class TestOpenRouterLiteLLMCall(unittest.TestCase):
    """LiteLLM을 통한 OpenRouter 실제 호출 구조 테스트 (Mock)"""

    def setUp(self):
        import app as flask_app
        self.app = flask_app.create_app()
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()

    def tearDown(self):
        self.app_ctx.pop()

    @patch('services.ai_service.completion')
    def test_openrouter_litellm_call_structure(self, mock_completion):
        """LiteLLM completion 호출 시 올바른 파라미터 전달"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# 테스트 제목\n\n테스트 본문"
        mock_response.usage = MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_completion.return_value = mock_response

        from services.core.ai_service import create_content
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'sk-or-test-key'}):
            result = create_content(
                content='테스트 자막 내용',
                model='openrouter/anthropic/claude-sonnet-4',
                style_prompt='블로그 스타일로 작성'
            )

        # LiteLLM이 정확히 1번 호출됨
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]

        # 모델 ID 그대로 전달 (openrouter/ 접두사 유지)
        self.assertEqual(call_kwargs['model'], 'openrouter/anthropic/claude-sonnet-4')
        # api_base 주입됨
        self.assertEqual(call_kwargs['api_base'], 'https://openrouter.ai/api/v1')
        # api_key 주입됨
        self.assertEqual(call_kwargs['api_key'], 'sk-or-test-key')

        # 결과 구조 검증
        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('html', result)
        self.assertIn('usage', result)


if __name__ == '__main__':
    unittest.main()
