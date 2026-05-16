"""prompts/modifiers 단위 테스트 — 모디파이어 시스템 데이터 + 빌더 함수"""
import unittest

from prompts.modifiers import (
    MODIFIERS,
    DEFAULT_MODIFIERS,
    MODIFIER_OPTIONS,
    build_modifier_text,
    get_modifier_text,
)


class TestModifierData(unittest.TestCase):

    def test_categories(self):
        self.assertEqual(set(MODIFIERS.keys()), {'length', 'writing_style', 'language'})

    def test_length_values(self):
        self.assertEqual(set(MODIFIERS['length'].keys()), {'short', 'medium', 'long'})

    def test_writing_style_values(self):
        self.assertEqual(
            set(MODIFIERS['writing_style'].keys()),
            {'conversational', 'explanatory', 'casual', 'expert'}
        )

    def test_language_values(self):
        self.assertEqual(set(MODIFIERS['language'].keys()), {'ko', 'en', 'ja'})

    def test_default_modifiers_in_modifiers_table(self):
        """DEFAULT_MODIFIERS가 가리키는 모든 값이 MODIFIERS에 실재해야 함"""
        for cat, val in DEFAULT_MODIFIERS.items():
            with self.subTest(category=cat, value=val):
                self.assertIn(cat, MODIFIERS)
                self.assertIn(val, MODIFIERS[cat])

    def test_modifier_options_keys_match(self):
        """MODIFIER_OPTIONS의 옵션 값들이 MODIFIERS에도 존재해야 함"""
        for cat, opt_info in MODIFIER_OPTIONS.items():
            self.assertIn(cat, MODIFIERS)
            self.assertIn('label', opt_info)
            self.assertIn('options', opt_info)
            for value, _label in opt_info['options']:
                with self.subTest(category=cat, value=value):
                    self.assertIn(value, MODIFIERS[cat])

    def test_modifier_texts_are_non_empty_strings(self):
        for cat, values in MODIFIERS.items():
            for v, text in values.items():
                with self.subTest(category=cat, value=v):
                    self.assertIsInstance(text, str)
                    self.assertGreater(len(text.strip()), 0)


class TestBuildModifierText(unittest.TestCase):

    def test_single_modifier(self):
        result = build_modifier_text({'length': 'short'})
        self.assertIn('500~800', result)

    def test_multiple_modifiers_joined(self):
        result = build_modifier_text({
            'length': 'medium',
            'writing_style': 'expert',
        })
        # 두 모디파이어 모두 포함
        self.assertIn('1000~1500', result)
        self.assertIn('전문가', result)
        # 구분자(\n) 존재
        self.assertIn('\n', result)

    def test_invalid_category_silently_skipped(self):
        result = build_modifier_text({
            'length': 'short',
            'invalid_category': 'value',
        })
        self.assertIn('500~800', result)

    def test_invalid_value_silently_skipped(self):
        result = build_modifier_text({
            'length': 'unknown_length',
        })
        self.assertEqual(result, '')

    def test_empty_input(self):
        self.assertEqual(build_modifier_text({}), '')


class TestGetModifierText(unittest.TestCase):

    def test_valid(self):
        result = get_modifier_text('length', 'short')
        self.assertIsNotNone(result)
        self.assertIn('500~800', result)

    def test_invalid_category(self):
        self.assertIsNone(get_modifier_text('nope', 'short'))

    def test_invalid_value(self):
        self.assertIsNone(get_modifier_text('length', 'nope'))

    def test_language_ko(self):
        self.assertEqual(get_modifier_text('language', 'ko'), '결과는 반드시 한국어로 작성해주세요.')


if __name__ == '__main__':
    unittest.main()
