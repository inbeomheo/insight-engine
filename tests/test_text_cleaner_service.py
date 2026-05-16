"""text_cleaner_service 단위 테스트"""
import unittest

from services.content.text_cleaner_service import clean_text


class TestCleanText(unittest.TestCase):

    def test_empty(self):
        result = clean_text('')
        self.assertEqual(result['cleaned'], '')
        self.assertEqual(result['total_changes'], 0)

    def test_none(self):
        result = clean_text(None)
        self.assertEqual(result['cleaned'], '')

    def test_clean_text_unchanged(self):
        text = '깨끗한 텍스트입니다.'
        result = clean_text(text)
        self.assertEqual(result['cleaned'], text)
        self.assertEqual(result['total_changes'], 0)

    def test_smart_quotes_replaced(self):
        text = '\u201c인용문\u201d'
        result = clean_text(text)
        self.assertIn('"', result['cleaned'])
        self.assertNotIn('\u201c', result['cleaned'])
        self.assertTrue(any(c['type'] == 'smart_quotes' for c in result['changes']))

    def test_dashes_replaced(self):
        text = '텍스트\u2014대시'
        result = clean_text(text)
        self.assertIn('-', result['cleaned'])
        self.assertNotIn('\u2014', result['cleaned'])

    def test_special_spaces(self):
        text = '공백\u00a0테스트'
        result = clean_text(text)
        self.assertNotIn('\u00a0', result['cleaned'])

    def test_double_spaces(self):
        text = '이중  공백  제거'
        result = clean_text(text)
        self.assertNotIn('  ', result['cleaned'])

    def test_invisible_chars(self):
        text = '보이지\u200b않는\u200c문자'
        result = clean_text(text)
        self.assertNotIn('\u200b', result['cleaned'])
        self.assertNotIn('\u200c', result['cleaned'])

    def test_trailing_whitespace(self):
        text = '줄 끝 공백   \n다음 줄'
        result = clean_text(text)
        for line in result['cleaned'].split('\n'):
            self.assertEqual(line, line.rstrip())

    def test_selective_options(self):
        text = '\u201c인용\u201d  이중공백'
        result = clean_text(text, options={'smart_quotes': True, 'double_spaces': False})
        # 따옴표는 변환, 이중공백은 유지
        self.assertNotIn('\u201c', result['cleaned'])
        self.assertIn('  ', result['cleaned'])

    def test_char_diff(self):
        text = '보이지\u200b않는\u200c문자'
        result = clean_text(text)
        self.assertLess(result['char_diff'], 0)  # 문자 제거 → 음수

    def test_total_changes(self):
        text = '\u201c인용\u201d  공백\u200b보이지않는'
        result = clean_text(text)
        self.assertGreater(result['total_changes'], 0)

    def test_fullwidth_space(self):
        text = '전각\u3000공백'
        result = clean_text(text)
        self.assertNotIn('\u3000', result['cleaned'])


if __name__ == '__main__':
    unittest.main()
