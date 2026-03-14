"""interactive_report_service 단위 테스트"""
import unittest

from services.content.interactive_report_service import (
    generate_interactive_report,
    _extract_headings,
    _build_toc,
)


class TestExtractHeadings(unittest.TestCase):

    def test_basic_headings(self):
        content = "# Title\n## Section 1\n### Sub\n## Section 2"
        headings = _extract_headings(content)
        self.assertEqual(len(headings), 4)
        self.assertEqual(headings[0][0], 1)  # level
        self.assertEqual(headings[1][0], 2)

    def test_no_headings(self):
        headings = _extract_headings("Just regular text")
        self.assertEqual(len(headings), 0)


class TestBuildToc(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_build_toc([]), '')

    def test_links_generated(self):
        headings = [(1, 'title', 'Title'), (2, 'sub', 'Sub')]
        toc = _build_toc(headings)
        self.assertIn('href="#title"', toc)
        self.assertIn('href="#sub"', toc)


class TestGenerateInteractiveReport(unittest.TestCase):

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            generate_interactive_report('')

    def test_basic_report(self):
        content = "## Introduction\n\nHello world\n\n## Conclusion\n\nBye"
        html = generate_interactive_report(content, 'Test Report')
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Test Report', html)
        self.assertIn('Introduction', html)
        self.assertIn('Conclusion', html)
        self.assertIn('<details', html)  # 접기 가능 섹션
        self.assertIn('searchInput', html)  # 검색 기능

    def test_search_script_included(self):
        html = generate_interactive_report('## Test\nContent', 'Test')
        self.assertIn('<script>', html)
        self.assertIn('searchInput', html)


if __name__ == '__main__':
    unittest.main()
