"""prompts/base 및 prompts/__init__.build_full_prompt 단위 테스트

베이스 프롬프트 + 스타일 + 모디파이어 조합. 모든 콘텐츠 생성에 사용되는 핵심.
"""
import unittest

from prompts.base import (
    BASE_PROMPT,
    FORBIDDEN_EXPRESSIONS,
    FORBIDDEN_REMINDER,
    SELF_CHECK,
    build_prompt,
)
from prompts import (
    build_full_prompt,
    get_available_styles,
    STYLE_PROMPTS,
)


class TestBaseConstants(unittest.TestCase):

    def test_base_prompt_non_empty(self):
        self.assertIsInstance(BASE_PROMPT, str)
        self.assertGreater(len(BASE_PROMPT), 500)

    def test_forbidden_expressions_list(self):
        """금지 표현 목록 — CLAUDE.md 규칙과 일치"""
        for word in ('놀라운', '혁신적', '획기적', '최고의', '게임체인저'):
            self.assertIn(word, FORBIDDEN_EXPRESSIONS)

    def test_forbidden_expressions_in_base_prompt(self):
        """베이스 프롬프트 본문에도 금지 표현이 명시되어야 함"""
        # 사용자에게 직접 보이는 문구로 강조
        for word in ('놀라운', '혁신적'):
            self.assertIn(word, BASE_PROMPT)

    def test_self_check_present(self):
        self.assertIn('체크리스트', SELF_CHECK)

    def test_forbidden_reminder_present(self):
        self.assertIn('절대 사용 금지', FORBIDDEN_REMINDER)


class TestBuildPrompt(unittest.TestCase):

    def test_includes_base_style_self_check_forbidden(self):
        """build_prompt 결과 = BASE + STYLE + SELF_CHECK + FORBIDDEN"""
        style = '# 테스트 스타일\n블로그 작성 가이드'
        result = build_prompt(style)
        self.assertIn(BASE_PROMPT.strip(), result)
        self.assertIn(style.strip(), result)
        self.assertIn('체크리스트', result)
        self.assertIn('절대 사용 금지', result)

    def test_modifier_section_added(self):
        result = build_prompt('# 스타일', modifiers={'length': 'short'})
        self.assertIn('# 추가 지침', result)
        self.assertIn('500~800', result)

    def test_no_modifier_section_when_empty_modifiers(self):
        result = build_prompt('# 스타일', modifiers={})
        self.assertNotIn('# 추가 지침', result)

    def test_invalid_modifier_skipped_silently(self):
        result = build_prompt('# 스타일', modifiers={'length': 'unknown'})
        # 무효 값은 빈 modifier_text를 생성하므로 섹션 미추가
        self.assertNotIn('# 추가 지침', result)


class TestBuildFullPrompt(unittest.TestCase):

    def test_known_style(self):
        result = build_full_prompt('blog_seo')
        # 베이스 + blog_seo 스타일 모두 포함
        self.assertIn(BASE_PROMPT.strip(), result)

    def test_unknown_style_falls_back_to_blog_seo(self):
        """unknown style은 blog_seo 폴백"""
        result_unknown = build_full_prompt('does_not_exist')
        result_blog_seo = build_full_prompt('blog_seo')
        # 동일 모디파이어 기본값 사용 시 결과 일치
        self.assertEqual(result_unknown, result_blog_seo)

    def test_default_modifiers_applied(self):
        """모디파이어 미지정 시 기본값 적용 — 한국어 + medium 길이"""
        result = build_full_prompt('blog_seo')
        # language=ko 기본값
        self.assertIn('한국어', result)
        # length=medium 기본값
        self.assertIn('1000~1500', result)

    def test_custom_modifiers_override_defaults(self):
        result = build_full_prompt('blog_seo', {'length': 'long', 'language': 'en'})
        self.assertIn('2000~3000', result)
        self.assertIn('You MUST write', result)
        # 기본값(ko)이 덮어써졌어야 함
        self.assertNotIn('결과는 반드시 한국어로', result)

    def test_partial_modifiers_merge_with_defaults(self):
        """일부만 지정 → 나머지는 기본값"""
        result = build_full_prompt('blog_seo', {'length': 'long'})
        # length: long 적용
        self.assertIn('2000~3000', result)
        # language: ko (기본) 적용
        self.assertIn('한국어', result)


class TestGetAvailableStyles(unittest.TestCase):

    def test_returns_dict(self):
        styles = get_available_styles()
        self.assertIsInstance(styles, dict)
        self.assertGreater(len(styles), 0)

    def test_includes_blog_seo(self):
        self.assertIn('blog_seo', get_available_styles())

    def test_all_returned_styles_in_style_prompts(self):
        """반환된 모든 스타일은 STYLE_PROMPTS에도 존재해야 함"""
        for style_id in get_available_styles():
            self.assertIn(style_id, STYLE_PROMPTS)


if __name__ == '__main__':
    unittest.main()
