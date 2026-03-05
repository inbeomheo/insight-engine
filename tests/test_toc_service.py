"""toc_service 단위 테스트"""
import unittest

from services.toc_service import generate_toc, _parse_headings, _slugify


class TestSlugify(unittest.TestCase):

    def test_english(self):
        self.assertEqual(_slugify('Hello World'), 'hello-world')

    def test_korean(self):
        slug = _slugify('한국어 제목')
        self.assertEqual(slug, '한국어-제목')

    def test_special_chars_removed(self):
        slug = _slugify('Hello! World?')
        self.assertNotIn('!', slug)
        self.assertNotIn('?', slug)


class TestParseHeadings(unittest.TestCase):

    def test_basic(self):
        md = '# Title\n## Sub\n### Deep'
        headings = _parse_headings(md)
        self.assertEqual(len(headings), 3)
        self.assertEqual(headings[0], (1, 'Title'))
        self.assertEqual(headings[1], (2, 'Sub'))

    def test_inline_formatting_removed(self):
        md = '## **Bold** Title'
        headings = _parse_headings(md)
        self.assertEqual(headings[0][1], 'Bold Title')

    def test_no_headings(self):
        self.assertEqual(_parse_headings('just text'), [])


class TestGenerateToc(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(generate_toc(''), '')

    def test_basic_toc(self):
        md = '# Intro\n## Methods\n## Results\n### Details'
        toc = generate_toc(md)
        self.assertIn('## 목차', toc)
        self.assertIn('[Intro]', toc)
        self.assertIn('[Methods]', toc)
        self.assertIn('[Results]', toc)
        self.assertIn('[Details]', toc)
        self.assertIn('#', toc)  # 앵커 링크

    def test_max_depth(self):
        md = '# H1\n## H2\n### H3\n#### H4'
        toc = generate_toc(md, max_depth=2)
        self.assertIn('H1', toc)
        self.assertIn('H2', toc)
        self.assertNotIn('H3', toc)
        self.assertNotIn('H4', toc)

    def test_duplicate_headings(self):
        md = '## FAQ\n## FAQ'
        toc = generate_toc(md)
        # 두 번째 FAQ는 다른 앵커를 가져야 함
        self.assertIn('faq', toc)
        self.assertIn('faq-1', toc)

    def test_indentation(self):
        md = '## Level2\n### Level3'
        toc = generate_toc(md)
        lines = [l for l in toc.split('\n') if l.strip().startswith('-')]
        # Level3은 들여쓰기
        self.assertTrue(lines[1].startswith('  '))


if __name__ == '__main__':
    unittest.main()
