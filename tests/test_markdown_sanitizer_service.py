"""markdown_sanitizer_service 단위 테스트"""
import unittest

from services.content.markdown_sanitizer_service import (
    sanitize_markdown,
    _normalize_heading_levels,
    _fix_unclosed_formatting,
)


class TestSanitizeMarkdown(unittest.TestCase):

    def test_empty_content(self):
        result = sanitize_markdown('')
        self.assertEqual(result['sanitized'], '')
        self.assertEqual(result['fix_count'], 0)

    def test_none_content(self):
        result = sanitize_markdown(None)
        self.assertEqual(result['fix_count'], 0)

    def test_clean_content_unchanged(self):
        text = '# 제목\n\n본문 내용입니다.'
        result = sanitize_markdown(text)
        self.assertEqual(result['sanitized'], text)

    def test_heading_normalization(self):
        text = '### 제목\n\n#### 소제목'
        result = sanitize_markdown(text)
        self.assertIn('# 제목', result['sanitized'])
        self.assertIn('## 소제목', result['sanitized'])
        self.assertTrue(any(f['type'] == 'heading_level' for f in result['fixes']))

    def test_empty_image_removed(self):
        text = '본문 ![이미지]() 텍스트'
        result = sanitize_markdown(text)
        self.assertNotIn('![', result['sanitized'])

    def test_empty_link_to_text(self):
        text = '본문 [링크텍스트]() 텍스트'
        result = sanitize_markdown(text)
        self.assertIn('링크텍스트', result['sanitized'])
        self.assertNotIn(']()', result['sanitized'])

    def test_multi_blank_lines(self):
        text = '첫째\n\n\n\n\n둘째'
        result = sanitize_markdown(text)
        self.assertNotIn('\n\n\n', result['sanitized'])

    def test_trailing_spaces(self):
        text = '줄 끝 공백   \n다음 줄'
        result = sanitize_markdown(text)
        lines = result['sanitized'].split('\n')
        for line in lines:
            self.assertEqual(line, line.rstrip())

    def test_unclosed_bold(self):
        text = '**열린 볼드\n다음 줄'
        result = sanitize_markdown(text)
        # 볼드가 닫혀야 함
        self.assertTrue(any(f['type'] == 'unclosed_bold' for f in result['fixes']))

    def test_fix_count(self):
        text = '### 제목\n\n\n\n\n![]()\n텍스트   '
        result = sanitize_markdown(text)
        self.assertGreater(result['fix_count'], 0)

    def test_char_diff(self):
        text = '# 제목\n\n\n\n\n본문'
        result = sanitize_markdown(text)
        self.assertIsInstance(result['char_diff'], int)


class TestNormalizeHeadingLevels(unittest.TestCase):

    def test_already_h1(self):
        text, fixes = _normalize_heading_levels('# 제목')
        self.assertEqual(fixes, [])

    def test_h3_to_h1(self):
        text, fixes = _normalize_heading_levels('### 제목\n#### 소제목')
        self.assertIn('# 제목', text)
        self.assertIn('## 소제목', text)

    def test_no_headings(self):
        text, fixes = _normalize_heading_levels('일반 텍스트')
        self.assertEqual(fixes, [])


class TestFixUnclosedFormatting(unittest.TestCase):

    def test_closed_bold_unchanged(self):
        text, count = _fix_unclosed_formatting('**볼드**', '**')
        self.assertEqual(count, 0)

    def test_unclosed_fixed(self):
        text, count = _fix_unclosed_formatting('**열린 볼드', '**')
        self.assertEqual(count, 1)
        self.assertIn('**', text[text.index('열린'):])

    def test_multiple_lines(self):
        text, count = _fix_unclosed_formatting('**ok**\n**열린\n**닫힌**', '**')
        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
