"""R138: truncate_string 유틸리티 테스트"""
import unittest

from utils.responses import truncate_string


class TestTruncateString(unittest.TestCase):

    def test_short_string_unchanged(self):
        self.assertEqual(truncate_string('hello', 10), 'hello')

    def test_exact_length_unchanged(self):
        self.assertEqual(truncate_string('12345', 5), '12345')

    def test_long_string_truncated(self):
        result = truncate_string('a' * 300, 200)
        self.assertEqual(len(result), 200)
        self.assertTrue(result.endswith('...'))

    def test_custom_suffix(self):
        result = truncate_string('abcdefghij', 8, suffix='…')
        self.assertEqual(len(result), 8)
        self.assertTrue(result.endswith('…'))

    def test_unicode_string(self):
        text = '한글테스트입니다' * 50
        result = truncate_string(text, 20)
        self.assertEqual(len(result), 20)

    def test_empty_string(self):
        self.assertEqual(truncate_string('', 10), '')

    def test_none_input(self):
        self.assertEqual(truncate_string(None, 10), '')

    def test_very_small_max_length(self):
        result = truncate_string('hello world', 3)
        self.assertEqual(len(result), 3)

    def test_max_length_equals_suffix_length(self):
        result = truncate_string('hello world', 3, suffix='...')
        self.assertEqual(result, '...')

    def test_emoji_string(self):
        """이모지(4바이트 유니코드)가 포함된 문자열도 깨지지 않아야 한다"""
        text = '🎉' * 100
        result = truncate_string(text, 50)
        self.assertEqual(len(result), 50)


if __name__ == '__main__':
    unittest.main()
