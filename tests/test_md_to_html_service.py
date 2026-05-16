"""md_to_html_service 단위 테스트"""
import unittest

from services.content.md_to_html_service import (
    convert_to_html,
    _markdown_to_html_body,
)


class TestConvertToHtml(unittest.TestCase):

    def test_empty_content(self):
        result = convert_to_html('')
        self.assertEqual(result['html'], '')

    def test_none_content(self):
        result = convert_to_html(None)
        self.assertEqual(result['html'], '')

    def test_standalone_structure(self):
        result = convert_to_html('# 제목\n본문', title='테스트', standalone=True)
        self.assertIn('<!DOCTYPE html>', result['html'])
        self.assertIn('<title>테스트</title>', result['html'])
        self.assertTrue(result['standalone'])

    def test_fragment_mode(self):
        result = convert_to_html('**볼드**', standalone=False)
        self.assertNotIn('<!DOCTYPE', result['html'])
        self.assertFalse(result['standalone'])

    def test_css_included(self):
        result = convert_to_html('텍스트', include_css=True, standalone=True)
        self.assertIn('<style>', result['html'])
        self.assertTrue(result['has_css'])

    def test_css_excluded(self):
        result = convert_to_html('텍스트', include_css=False, standalone=True)
        self.assertNotIn('<style>', result['html'])

    def test_heading_converted(self):
        result = convert_to_html('# 제목', standalone=False)
        self.assertIn('<h1>제목</h1>', result['html'])

    def test_bold_converted(self):
        result = convert_to_html('**굵게**', standalone=False)
        self.assertIn('<strong>굵게</strong>', result['html'])

    def test_link_converted(self):
        result = convert_to_html('[링크](https://example.com)', standalone=False)
        self.assertIn('href="https://example.com"', result['html'])
        self.assertIn('링크', result['html'])

    def test_image_converted(self):
        result = convert_to_html('![alt](img.png)', standalone=False)
        self.assertIn('<img', result['html'])
        self.assertIn('alt="alt"', result['html'])

    def test_code_block_converted(self):
        md = '```python\nprint("hi")\n```'
        result = convert_to_html(md, standalone=False)
        self.assertIn('<pre>', result['html'])
        self.assertIn('<code', result['html'])

    def test_inline_code(self):
        result = convert_to_html('`코드`', standalone=False)
        self.assertIn('<code>', result['html'])

    def test_blockquote(self):
        result = convert_to_html('> 인용문', standalone=False)
        self.assertIn('<blockquote>', result['html'])

    def test_char_count(self):
        result = convert_to_html('테스트')
        self.assertEqual(result['char_count'], len(result['html']))

    def test_title_escaped(self):
        result = convert_to_html('내용', title='<script>alert(1)</script>')
        self.assertNotIn('<script>', result['html'])
        self.assertIn('&lt;script&gt;', result['html'])


class TestMarkdownToHtmlBody(unittest.TestCase):

    def test_paragraph(self):
        html_body = _markdown_to_html_body('일반 텍스트')
        self.assertIn('<p>', html_body)

    def test_hr(self):
        html_body = _markdown_to_html_body('---')
        self.assertIn('<hr>', html_body)

    def test_strikethrough(self):
        html_body = _markdown_to_html_body('~~취소~~')
        self.assertIn('<del>취소</del>', html_body)

    def test_list_items(self):
        html_body = _markdown_to_html_body('- 항목1\n- 항목2')
        self.assertIn('<li>', html_body)
        self.assertIn('<ul>', html_body)


if __name__ == '__main__':
    unittest.main()
