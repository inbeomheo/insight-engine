"""
스타일 프롬프트 테스트 v3.1
8개 스타일, 2개 모디파이어 검증
"""
import unittest


class TestStylePrompts(unittest.TestCase):
    def test_style_options_include_core_styles(self):
        """11개 스타일이 STYLE_OPTIONS에 포함되어 있는지 확인"""
        import config

        style_keys = [k for k, _ in config.STYLE_OPTIONS]

        # 11개 스타일 확인
        self.assertIn('blog_seo', style_keys)
        self.assertIn('summary', style_keys)
        self.assertIn('tutorial', style_keys)
        self.assertIn('qna', style_keys)
        self.assertIn('app_ideas', style_keys)
        self.assertIn('yozm_it', style_keys)
        self.assertIn('brunch_essay', style_keys)
        self.assertIn('naver_popular', style_keys)
        self.assertIn('sns_post', style_keys)
        self.assertIn('newsletter', style_keys)
        self.assertIn('show_notes', style_keys)

        self.assertEqual(len(style_keys), 11)

    def test_style_prompts_contain_all_styles(self):
        """STYLE_PROMPTS에 모든 스타일이 포함되어 있는지 확인"""
        import config

        for style_id, _ in config.STYLE_OPTIONS:
            self.assertIn(style_id, config.STYLE_PROMPTS)

    def test_modifiers_have_only_two_categories(self):
        """모디파이어가 2개 카테고리만 있는지 확인"""
        import config

        modifier_keys = list(config.MODIFIER_OPTIONS.keys())

        self.assertIn('length', modifier_keys)
        self.assertIn('writing_style', modifier_keys)
        self.assertEqual(len(modifier_keys), 2)

    def test_default_modifiers(self):
        """기본 모디파이어 값 확인"""
        import config

        self.assertEqual(config.DEFAULT_MODIFIERS['length'], 'medium')
        self.assertEqual(config.DEFAULT_MODIFIERS['writing_style'], 'conversational')

    def test_build_full_prompt_works(self):
        """프롬프트 빌드 함수가 정상 작동하는지 확인"""
        import config

        prompt = config.build_full_prompt('blog_seo', {
            'length': 'short',
            'writing_style': 'casual'
        })

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

    def test_writing_style_options(self):
        """문체 옵션이 4가지인지 확인"""
        import config

        writing_style_options = config.MODIFIER_OPTIONS['writing_style']['options']
        values = [opt[0] for opt in writing_style_options]

        self.assertIn('conversational', values)
        self.assertIn('explanatory', values)
        self.assertIn('casual', values)
        self.assertIn('expert', values)
        self.assertEqual(len(values), 4)

    def test_all_styles_use_markdown_only(self):
        """모든 스타일 프롬프트가 HTML 태그를 사용하지 않는지 확인"""
        import config
        import re

        # 검사할 HTML 태그 패턴 (마크다운과 충돌하지 않는 태그만)
        html_tag_pattern = re.compile(r'<(?![-/])(idea|div|span|section|article|header|footer)[^>]*>')

        for style_id in config.STYLE_PROMPTS:
            prompt = config.STYLE_PROMPTS[style_id]
            matches = html_tag_pattern.findall(prompt)
            self.assertEqual(
                len(matches), 0,
                f"스타일 '{style_id}'에 HTML 태그 발견: {matches}"
            )

    def test_prompt_line_count_reasonable(self):
        """각 스타일 프롬프트가 160줄 이하인지 확인"""
        import config

        max_lines = 160

        for style_id in config.STYLE_PROMPTS:
            prompt = config.STYLE_PROMPTS[style_id]
            line_count = len(prompt.strip().split('\n'))
            self.assertLessEqual(
                line_count, max_lines,
                f"스타일 '{style_id}'의 줄 수({line_count})가 {max_lines}줄을 초과합니다."
            )

    def test_modifiers_validation_matches_config(self):
        """routes의 모디파이어 검증이 config와 일치하는지 확인"""
        import config

        # config.py의 모디파이어 키
        config_keys = set(config.MODIFIER_OPTIONS.keys())

        # config.py의 모디파이어 값
        config_values = {}
        for key in config_keys:
            config_values[key] = {opt[0] for opt in config.MODIFIER_OPTIONS[key]['options']}

        # 검증: length와 writing_style만 있어야 함
        self.assertEqual(config_keys, {'length', 'writing_style'})

        # 검증: length 값
        self.assertEqual(config_values['length'], {'short', 'medium', 'long'})

        # 검증: writing_style 값
        self.assertEqual(
            config_values['writing_style'],
            {'conversational', 'explanatory', 'casual', 'expert'}
        )

    def test_forbidden_reminder_in_built_prompt(self):
        """빌드된 프롬프트에 금지 표현 재강조가 포함되는지 확인"""
        import config

        prompt = config.build_full_prompt('blog_seo')

        self.assertIn('필수 준수 사항', prompt)
        self.assertIn('절대 사용 금지', prompt)


if __name__ == "__main__":
    unittest.main()
