"""
Shorts 클립 스타일 통합 테스트
프롬프트 로드, config 등록, temperature 확인
"""
import unittest


class TestShortsStyle(unittest.TestCase):
    def test_shorts_prompt_loaded(self):
        """STYLE_PROMPTS에 shorts_script 프롬프트가 로드되는지 확인"""
        from prompts.styles import STYLE_PROMPTS

        self.assertIn('shorts_script', STYLE_PROMPTS)
        self.assertIsInstance(STYLE_PROMPTS['shorts_script'], str)
        self.assertGreater(len(STYLE_PROMPTS['shorts_script']), 100)

    def test_shorts_in_style_options(self):
        """config.STYLE_OPTIONS에 shorts_script이 등록되어 있는지 확인"""
        import config

        style_keys = [k for k, _ in config.STYLE_OPTIONS]
        self.assertIn('shorts_script', style_keys)

    def test_shorts_temperature_exists(self):
        """STYLE_TEMPERATURE에 shorts_script이 존재하는지 확인"""
        import config

        self.assertIn('shorts_script', config.STYLE_TEMPERATURE)
        self.assertEqual(config.STYLE_TEMPERATURE['shorts_script'], 0.7)

    def test_shorts_prompt_contains_key_elements(self):
        """Shorts 프롬프트에 핵심 요소가 포함되어 있는지 확인"""
        from prompts.styles import STYLE_PROMPTS

        prompt = STYLE_PROMPTS['shorts_script']

        # 핵심 구조 요소 확인
        self.assertIn('후킹 문구', prompt)
        self.assertIn('스크립트', prompt)
        self.assertIn('60초', prompt)
        self.assertIn('클립', prompt)

    def test_shorts_prompt_has_forbidden_expressions(self):
        """Shorts 프롬프트에 금지 표현 규칙이 포함되어 있는지 확인"""
        from prompts.styles import STYLE_PROMPTS

        prompt = STYLE_PROMPTS['shorts_script']
        self.assertIn('금지 표현', prompt)

    def test_build_full_prompt_with_shorts(self):
        """build_full_prompt가 shorts_script 스타일로 정상 작동하는지 확인"""
        import config

        prompt = config.build_full_prompt('shorts_script', {
            'length': 'medium',
            'writing_style': 'conversational'
        })

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)


if __name__ == "__main__":
    unittest.main()
