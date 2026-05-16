"""rss_feed_generator_service 단위 테스트"""
import unittest

from services.content.rss_feed_generator_service import (
    generate_rss,
    _extract_title,
    _make_description,
)


class TestGenerateRss(unittest.TestCase):

    def test_empty(self):
        result = generate_rss([])
        self.assertEqual(result['item_count'], 0)
        self.assertEqual(result['xml'], '')

    def test_rss_format(self):
        contents = [{'title': '제목1', 'content': '내용1'}]
        result = generate_rss(contents, format_type='rss')
        self.assertIn('<rss version="2.0">', result['xml'])
        self.assertIn('<title>제목1</title>', result['xml'])
        self.assertEqual(result['format'], 'rss')
        self.assertEqual(result['item_count'], 1)

    def test_atom_format(self):
        contents = [{'title': '제목1', 'content': '내용1'}]
        result = generate_rss(contents, format_type='atom')
        self.assertIn('<feed xmlns', result['xml'])
        self.assertIn('<entry>', result['xml'])
        self.assertEqual(result['format'], 'atom')

    def test_multiple_items(self):
        contents = [
            {'title': f'글{i}', 'content': f'내용{i}'}
            for i in range(3)
        ]
        result = generate_rss(contents)
        self.assertEqual(result['item_count'], 3)
        self.assertEqual(result['xml'].count('<item>'), 3)

    def test_feed_title(self):
        result = generate_rss([{'title': 'A', 'content': 'B'}], feed_title='My Blog')
        self.assertIn('My Blog', result['xml'])

    def test_author_included(self):
        contents = [{'title': '글', 'content': '내용', 'author': '작성자'}]
        result = generate_rss(contents)
        self.assertIn('작성자', result['xml'])

    def test_link_included(self):
        contents = [{'title': '글', 'content': '내용', 'link': 'https://example.com/1'}]
        result = generate_rss(contents)
        self.assertIn('example.com', result['xml'])

    def test_xml_declaration(self):
        result = generate_rss([{'title': 'T', 'content': 'C'}])
        self.assertTrue(result['xml'].startswith('<?xml'))

    def test_html_escaped(self):
        contents = [{'title': '<script>alert</script>', 'content': 'safe'}]
        result = generate_rss(contents)
        self.assertNotIn('<script>', result['xml'])
        self.assertIn('&lt;script&gt;', result['xml'])

    def test_title_from_content(self):
        contents = [{'content': '# 자동 제목\n본문'}]
        result = generate_rss(contents)
        self.assertIn('자동 제목', result['xml'])


class TestExtractTitle(unittest.TestCase):

    def test_heading(self):
        self.assertEqual(_extract_title('# 메인'), '메인')

    def test_no_heading(self):
        self.assertEqual(_extract_title('일반 텍스트'), '제목 없음')


class TestMakeDescription(unittest.TestCase):

    def test_short_content(self):
        desc = _make_description('짧은 설명')
        self.assertEqual(desc, '짧은 설명')

    def test_long_content_truncated(self):
        desc = _make_description('긴 내용 ' * 100, max_len=50)
        self.assertLessEqual(len(desc), 53)  # 50 + '...'

    def test_markdown_stripped(self):
        desc = _make_description('**볼드** [링크](url)')
        self.assertNotIn('**', desc)
        self.assertNotIn('[', desc)


if __name__ == '__main__':
    unittest.main()
