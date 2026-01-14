"""
설정(config.py) 단위 테스트
프로바이더 목록, 토큰 제한, 스타일 설정 검증
"""
import unittest


class TestSupportedProviders(unittest.TestCase):
    """지원 프로바이더 설정 테스트"""

    def test_supported_providers_structure(self):
        """SUPPORTED_PROVIDERS 구조 검증"""
        from config import SUPPORTED_PROVIDERS

        self.assertIsInstance(SUPPORTED_PROVIDERS, dict)

        for provider, config in SUPPORTED_PROVIDERS.items():
            self.assertIn('name', config, f"{provider}에 name 없음")
            self.assertIn('models', config, f"{provider}에 models 없음")

    def test_each_provider_has_models(self):
        """각 프로바이더에 최소 1개 모델 존재"""
        from config import SUPPORTED_PROVIDERS

        for provider, config in SUPPORTED_PROVIDERS.items():
            self.assertGreater(
                len(config['models']), 0,
                f"{provider}에 모델이 없습니다"
            )

    def test_model_structure(self):
        """모델 구조 검증 (id, name, max_input_tokens)"""
        from config import SUPPORTED_PROVIDERS

        for provider, config in SUPPORTED_PROVIDERS.items():
            for model in config['models']:
                self.assertIn('id', model, f"{provider}의 모델에 id 없음")
                self.assertIn('name', model, f"{provider}의 모델에 name 없음")
                self.assertIn('max_input_tokens', model, f"{provider}의 모델에 max_input_tokens 없음")
                self.assertGreater(model['max_input_tokens'], 0)


class TestTokenLimits(unittest.TestCase):
    """토큰 제한 설정 테스트"""

    def test_max_content_tokens_exists(self):
        """MAX_CONTENT_TOKENS 존재 확인"""
        from config import MAX_CONTENT_TOKENS

        self.assertIsInstance(MAX_CONTENT_TOKENS, int)
        self.assertGreater(MAX_CONTENT_TOKENS, 0)

    def test_max_transcript_tokens_exists(self):
        """MAX_TRANSCRIPT_TOKENS 존재 확인"""
        from config import MAX_TRANSCRIPT_TOKENS

        self.assertIsInstance(MAX_TRANSCRIPT_TOKENS, int)
        self.assertGreater(MAX_TRANSCRIPT_TOKENS, 0)

    def test_max_comments_tokens_exists(self):
        """MAX_COMMENTS_TOKENS 존재 확인"""
        from config import MAX_COMMENTS_TOKENS

        self.assertIsInstance(MAX_COMMENTS_TOKENS, int)
        self.assertGreater(MAX_COMMENTS_TOKENS, 0)


class TestStyleConfiguration(unittest.TestCase):
    """스타일 설정 테스트"""

    def test_style_options_exist(self):
        """STYLE_OPTIONS 존재 확인"""
        from config import STYLE_OPTIONS

        self.assertIsInstance(STYLE_OPTIONS, list)
        self.assertGreater(len(STYLE_OPTIONS), 0)

    def test_style_options_structure(self):
        """STYLE_OPTIONS 구조 검증 (tuple of id, name)"""
        from config import STYLE_OPTIONS

        for option in STYLE_OPTIONS:
            self.assertIsInstance(option, tuple)
            self.assertEqual(len(option), 2)
            style_id, style_name = option
            self.assertIsInstance(style_id, str)
            self.assertIsInstance(style_name, str)

    def test_expected_styles_present(self):
        """필수 스타일 존재 확인"""
        from config import STYLE_OPTIONS

        style_ids = [opt[0] for opt in STYLE_OPTIONS]
        expected_styles = ['blog', 'summary', 'easy', 'news']

        for style in expected_styles:
            self.assertIn(style, style_ids, f"{style} 스타일 누락")

    def test_style_prompts_match_options(self):
        """STYLE_PROMPTS와 STYLE_OPTIONS 일치 확인"""
        from config import STYLE_OPTIONS
        from prompts import STYLE_PROMPTS

        style_ids = [opt[0] for opt in STYLE_OPTIONS]

        for style_id in style_ids:
            self.assertIn(
                style_id, STYLE_PROMPTS,
                f"{style_id} 스타일의 프롬프트가 STYLE_PROMPTS에 없음"
            )


class TestProviderFunctions(unittest.TestCase):
    """프로바이더 관련 함수 테스트"""

    def test_get_provider_from_model_openai(self):
        """OpenAI 모델 ID에서 프로바이더 추출"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('gpt-4o'), 'openai')
        self.assertEqual(get_provider_from_model('gpt-4o-mini'), 'openai')

    def test_get_provider_from_model_anthropic(self):
        """Anthropic 모델 ID에서 프로바이더 추출"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('claude-3-5-sonnet'), 'anthropic')
        self.assertEqual(get_provider_from_model('claude-3-haiku'), 'anthropic')

    def test_get_provider_from_model_gemini(self):
        """Gemini 모델 ID에서 프로바이더 추출"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('gemini/gemini-2.0-flash'), 'gemini')

    def test_get_provider_from_model_deepseek(self):
        """DeepSeek 모델 ID에서 프로바이더 추출"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('deepseek/deepseek-chat'), 'deepseek')

    def test_get_provider_from_model_unknown_defaults_to_openai(self):
        """알 수 없는 모델은 openai 기본값"""
        from config import get_provider_from_model

        self.assertEqual(get_provider_from_model('unknown-model'), 'openai')


class TestProviderApiKeys(unittest.TestCase):
    """프로바이더 API 키 설정 테스트"""

    def test_provider_api_keys_structure(self):
        """PROVIDER_API_KEYS 구조 검증"""
        from config import PROVIDER_API_KEYS

        self.assertIsInstance(PROVIDER_API_KEYS, dict)

        expected_keys = ['openai', 'anthropic', 'gemini', 'deepseek']
        for key in expected_keys:
            self.assertIn(key, PROVIDER_API_KEYS)


if __name__ == '__main__':
    unittest.main()
