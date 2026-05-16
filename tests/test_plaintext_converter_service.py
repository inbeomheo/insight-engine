"""plaintext_converter_service 단위 테스트"""
import unittest

from services.content.plaintext_converter_service import (
    convert_to_plaintext,
    _extract_code_content,
)


class TestConvertToPlaintext(unittest.TestCase):

    def test_empty_content(self):
        result = convert_to_plaintext('')
        self.assertEqual(result['text'], '')
        self.assertEqual(result['char_count'], 0)

    def test_none_content(self):
        result = convert_to_plaintext(None)
        self.assertEqual(result['text'], '')

    def test_plain_text_unchanged(self):
        text = '순수 텍스트입니다.'
        result = convert_to_plaintext(text)
        self.assertEqual(result['text'], text)

    def test_heading_removed(self):
        result = convert_to_plaintext('# 제목\n본문')
        self.assertNotIn('#', result['text'])
        self.assertIn('제목', result['text'])

    def test_bold_removed(self):
        result = convert_to_plaintext('**볼드** 텍스트')
        self.assertNotIn('**', result['text'])
        self.assertIn('볼드', result['text'])

    def test_italic_removed(self):
        result = convert_to_plaintext('*이탤릭* 텍스트')
        self.assertNotIn('*', result['text'])
        self.assertIn('이탤릭', result['text'])

    def test_link_to_text(self):
        result = convert_to_plaintext('[링크](https://example.com)')
        self.assertIn('링크', result['text'])
        self.assertNotIn('http', result['text'])

    def test_image_to_alt(self):
        result = convert_to_plaintext('![대체텍스트](img.png)')
        self.assertIn('대체텍스트', result['text'])
        self.assertNotIn('img.png', result['text'])

    def test_code_block_content_preserved(self):
        md = '텍스트\n```python\nprint("hello")\n```\n더 텍스트'
        result = convert_to_plaintext(md)
        self.assertIn('print', result['text'])
        self.assertNotIn('```', result['text'])

    def test_inline_code_to_text(self):
        result = convert_to_plaintext('`코드` 텍스트')
        self.assertNotIn('`', result['text'])
        self.assertIn('코드', result['text'])

    def test_blockquote_removed(self):
        result = convert_to_plaintext('> 인용문입니다.')
        self.assertNotIn('>', result['text'])
        self.assertIn('인용문', result['text'])

    def test_html_removed(self):
        result = convert_to_plaintext('<strong>강조</strong> 텍스트')
        self.assertNotIn('<strong>', result['text'])

    def test_removed_elements_count(self):
        md = '![img](a.png)\n[link](url)\n```\ncode\n```'
        result = convert_to_plaintext(md)
        self.assertEqual(result['removed_elements']['images'], 1)
        # 이미지 마크다운이 링크 패턴에도 매칭될 수 있음
        self.assertGreaterEqual(result['removed_elements']['links'], 1)
        self.assertEqual(result['removed_elements']['code_blocks'], 1)

    def test_preserve_structure_true(self):
        md = '- 항목 1\n- 항목 2'
        result = convert_to_plaintext(md, preserve_structure=True)
        self.assertIn('- ', result['text'])

    def test_preserve_structure_false(self):
        md = '- 항목 1\n- 항목 2'
        result = convert_to_plaintext(md, preserve_structure=False)
        self.assertNotIn('- ', result['text'])

    def test_line_count(self):
        result = convert_to_plaintext('줄1\n줄2\n줄3')
        self.assertGreaterEqual(result['line_count'], 3)

    def test_strikethrough_removed(self):
        result = convert_to_plaintext('~~취소선~~ 텍스트')
        self.assertNotIn('~~', result['text'])
        self.assertIn('취소선', result['text'])


if __name__ == '__main__':
    unittest.main()
