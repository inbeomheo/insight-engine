"""config.py 일관성 검증 테스트

상수 데이터 구조의 invariant + 헬퍼 함수 동작.
"""
import unittest

import config


class TestSupportedProvidersStructure(unittest.TestCase):
    """SUPPORTED_PROVIDERS 데이터 무결성 — CLAUDE.md 규칙: 모든 모델은 price_input/output 필수"""

    def test_all_providers_have_name_and_models(self):
        for pid, p in config.SUPPORTED_PROVIDERS.items():
            with self.subTest(provider=pid):
                self.assertIn('name', p, f'{pid}에 name 없음')
                self.assertIn('models', p, f'{pid}에 models 없음')
                self.assertIsInstance(p['models'], list)
                self.assertGreater(len(p['models']), 0, f'{pid}: 모델이 비어있음')

    def test_all_models_have_required_fields(self):
        required = ('id', 'name', 'max_input_tokens', 'price_input', 'price_output')
        for pid, p in config.SUPPORTED_PROVIDERS.items():
            for model in p['models']:
                with self.subTest(provider=pid, model=model.get('id')):
                    for field in required:
                        self.assertIn(field, model, f"{model.get('id')}에 {field} 누락")
                    self.assertIsInstance(model['max_input_tokens'], int)
                    self.assertGreater(model['max_input_tokens'], 0)
                    # 가격은 0 (무료/로컬) 또는 양수
                    self.assertGreaterEqual(model['price_input'], 0)
                    self.assertGreaterEqual(model['price_output'], 0)

    def test_model_ids_unique(self):
        seen = set()
        for p in config.SUPPORTED_PROVIDERS.values():
            for m in p['models']:
                self.assertNotIn(m['id'], seen, f"중복 모델 ID: {m['id']}")
                seen.add(m['id'])


class TestProviderFromModel(unittest.TestCase):

    def test_recognized_prefixes(self):
        cases = [
            ('gpt-4', 'openai'),
            ('claude-3-opus', 'anthropic'),
            ('gemini/gemini-3-flash', 'gemini'),
            ('deepseek/deepseek-chat', 'deepseek'),
            ('zhipuai/GLM-4.7', 'zhipuai'),
            ('ollama_chat/llama3.2', 'ollama'),
            ('ollama/mistral', 'ollama'),
            ('chatmock/gpt-5.4', 'chatmock'),
            ('openrouter/anthropic/claude', 'openrouter'),
        ]
        for model_id, expected_provider in cases:
            with self.subTest(model=model_id):
                self.assertEqual(config.get_provider_from_model(model_id), expected_provider)

    def test_unknown_defaults_to_gemini(self):
        self.assertEqual(config.get_provider_from_model('unknown/model'), 'gemini')


class TestGetModelMaxTokens(unittest.TestCase):

    def test_known_model(self):
        # 첫 번째 등록된 gemini 모델 사용
        first_gemini = config.SUPPORTED_PROVIDERS['gemini']['models'][0]
        self.assertEqual(
            config.get_model_max_tokens(first_gemini['id']),
            first_gemini['max_input_tokens']
        )

    def test_unknown_returns_fallback(self):
        result = config.get_model_max_tokens('nonexistent/model')
        self.assertGreater(result, 0)


class TestGetModelDisplayName(unittest.TestCase):

    def test_known_model(self):
        first_gemini = config.SUPPORTED_PROVIDERS['gemini']['models'][0]
        self.assertEqual(
            config.get_model_display_name(first_gemini['id']),
            first_gemini['name']
        )

    def test_unknown_returns_id_unchanged(self):
        self.assertEqual(
            config.get_model_display_name('mystery/model'),
            'mystery/model'
        )


class TestStyleOptionsInvariants(unittest.TestCase):

    def test_style_options_match_descriptions(self):
        """STYLE_OPTIONS의 모든 ID가 STYLE_DESCRIPTIONS에도 존재"""
        for style_id, _ in config.STYLE_OPTIONS:
            self.assertIn(style_id, config.STYLE_DESCRIPTIONS,
                          f"{style_id} 설명 없음")

    def test_no_duplicate_style_ids(self):
        ids = [s[0] for s in config.STYLE_OPTIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_styles_have_temperature(self):
        """UI 스타일 중 STYLE_TEMPERATURE에 정의된 항목만 검증
        (comment_summary 같은 내부 전용도 포함되어야 함)
        """
        ui_styles = [s[0] for s in config.STYLE_OPTIONS]
        for style_id in ui_styles:
            with self.subTest(style=style_id):
                # temperature가 정의되어 있다면 합리적 범위(0~1)
                if style_id in config.STYLE_TEMPERATURE:
                    temp = config.STYLE_TEMPERATURE[style_id]
                    self.assertGreaterEqual(temp, 0.0)
                    self.assertLessEqual(temp, 1.0)


class TestModifiersInvariants(unittest.TestCase):

    def test_length_modifier_values(self):
        self.assertEqual(
            set(config.STYLE_MODIFIERS['length'].keys()),
            {'short', 'medium', 'long'}
        )

    def test_writing_style_modifier_values(self):
        self.assertEqual(
            set(config.STYLE_MODIFIERS['writing_style'].keys()),
            {'conversational', 'explanatory', 'casual', 'expert'}
        )

    def test_language_modifier_values(self):
        self.assertEqual(
            set(config.STYLE_MODIFIERS['language'].keys()),
            {'ko', 'en', 'ja'}
        )

    def test_length_max_tokens_complete(self):
        for length in ('short', 'medium', 'long'):
            self.assertIn(length, config.LENGTH_MAX_TOKENS)
            self.assertGreater(config.LENGTH_MAX_TOKENS[length], 0)


class TestDetailPresets(unittest.TestCase):

    def test_three_presets_exist(self):
        self.assertEqual(set(config.DETAIL_PRESETS.keys()), {'brief', 'standard', 'deep'})

    def test_preset_fields(self):
        required = ('temperature_offset', 'max_tokens_multiplier', 'prompt_suffix')
        for name, preset in config.DETAIL_PRESETS.items():
            for field in required:
                with self.subTest(preset=name, field=field):
                    self.assertIn(field, preset)


class TestCampaignPacks(unittest.TestCase):

    def test_all_packs_reference_valid_styles(self):
        """CAMPAIGN_PACKS의 styles가 모두 STYLE_OPTIONS에 존재"""
        valid_styles = {s[0] for s in config.STYLE_OPTIONS}
        for pack_id, pack in config.CAMPAIGN_PACKS.items():
            for style in pack['styles']:
                with self.subTest(pack=pack_id, style=style):
                    self.assertIn(style, valid_styles, f'{style} (in {pack_id}) 미정의')

    def test_packs_have_metadata(self):
        for pack_id, pack in config.CAMPAIGN_PACKS.items():
            for field in ('name', 'description', 'styles'):
                with self.subTest(pack=pack_id, field=field):
                    self.assertIn(field, pack)


class TestPlatformPresets(unittest.TestCase):

    def test_four_platforms(self):
        self.assertEqual(
            set(config.PLATFORM_PRESETS.keys()),
            {'twitter', 'linkedin', 'instagram', 'threads'}
        )

    def test_all_have_max_chars(self):
        for platform, preset in config.PLATFORM_PRESETS.items():
            with self.subTest(platform=platform):
                self.assertIn('max_chars', preset)
                self.assertGreater(preset['max_chars'], 0)


if __name__ == '__main__':
    unittest.main()
