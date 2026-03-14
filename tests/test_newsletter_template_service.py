"""newsletter_template_service 단위 테스트"""
import unittest

from services.content.newsletter_template_service import convert_to_newsletter, _inline_format


class TestInlineFormat(unittest.TestCase):

    def test_bold(self):
        self.assertIn('<strong>', _inline_format('**bold**'))

    def test_italic(self):
        self.assertIn('<em>', _inline_format('*italic*'))

    def test_link(self):
        result = _inline_format('[text](http://example.com)')
        self.assertIn('href="http://example.com"', result)

    def test_inline_code(self):
        result = _inline_format('use `pip install`')
        self.assertIn('<code', result)


class TestConvertToNewsletter(unittest.TestCase):

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            convert_to_newsletter('', 'Test')

    def test_basic_conversion(self):
        html = convert_to_newsletter('## Hello\n\nWorld', 'Test Newsletter')
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Test Newsletter', html)
        self.assertIn('Hello', html)
        self.assertIn('World', html)

    def test_heading_styles(self):
        html = convert_to_newsletter('# H1\n## H2\n### H3', 'Test')
        self.assertIn('<h1', html)
        self.assertIn('<h2', html)
        self.assertIn('<h3', html)

    def test_list_items(self):
        html = convert_to_newsletter('- item1\n- item2', 'Test')
        self.assertIn('<ul', html)
        self.assertIn('<li', html)

    def test_ordered_list(self):
        html = convert_to_newsletter('1. first\n2. second', 'Test')
        self.assertIn('<ol', html)

    def test_blockquote(self):
        html = convert_to_newsletter('> quote here', 'Test')
        self.assertIn('<blockquote', html)

    def test_table_layout(self):
        """이메일 호환: 테이블 레이아웃 사용"""
        html = convert_to_newsletter('content', 'Test')
        self.assertIn('role="presentation"', html)

    def test_inline_css(self):
        """이메일 호환: 인라인 CSS"""
        html = convert_to_newsletter('## Title', 'Test')
        self.assertIn('style=', html)


if __name__ == '__main__':
    unittest.main()
