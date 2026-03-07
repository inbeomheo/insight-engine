"""External Source Diversity Auditor 서비스 테스트."""
import unittest
from services.external_source_diversity_service import audit_external_source_diversity


class TestExternalSourceDiversity(unittest.TestCase):
    """audit_external_source_diversity 함수 테스트."""

    def test_empty_content(self):
        result = audit_external_source_diversity('')
        self.assertEqual(result['summary']['total_sources'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_none_content(self):
        result = audit_external_source_diversity(None)
        self.assertEqual(result['summary']['total_sources'], 0)

    def test_no_urls(self):
        content = '외부 링크가 없는 일반 텍스트입니다.'
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['total_sources'], 0)
        self.assertGreater(len(result['suggestions']), 0)

    def test_single_domain(self):
        content = """
참고: https://developer.mozilla.org/docs/html
참조: https://developer.mozilla.org/docs/css
"""
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['unique_domains'], 1)
        self.assertGreater(result['summary']['total_sources'], 0)

    def test_multiple_domains(self):
        content = """
https://developer.mozilla.org/docs
https://docs.python.org/3/tutorial
https://react.dev/learn
"""
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['unique_domains'], 3)

    def test_markdown_links(self):
        content = '[MDN](https://developer.mozilla.org/docs) 참고'
        result = audit_external_source_diversity(content)
        self.assertGreater(result['summary']['total_sources'], 0)

    def test_www_normalization(self):
        content = 'https://www.google.com/search https://google.com/maps'
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['unique_domains'], 1)

    def test_cdn_excluded(self):
        content = 'https://cdn.jsdelivr.net/npm/react https://fonts.googleapis.com/css'
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['total_sources'], 0)

    def test_citation_count_korean(self):
        content = 'Google에 따르면 검색 순위가 변경되었습니다. https://google.com/blog'
        result = audit_external_source_diversity(content)
        self.assertGreater(result['summary']['citation_count'], 0)

    def test_citation_count_english(self):
        content = 'According to Google the ranking changed. https://google.com/blog'
        result = audit_external_source_diversity(content)
        self.assertGreater(result['summary']['citation_count'], 0)

    def test_high_diversity_score(self):
        content = """
https://mozilla.org/docs
https://python.org/docs
https://react.dev/learn
https://github.com/repo
"""
        result = audit_external_source_diversity(content)
        self.assertGreater(result['score'], 60.0)

    def test_low_diversity_single_domain(self):
        content = """
https://techblog.com/page1
https://techblog.com/page2
https://techblog.com/page3
https://techblog.com/page4
https://techblog.com/page5
"""
        result = audit_external_source_diversity(content)
        self.assertEqual(result['summary']['unique_domains'], 1)

    def test_domain_distribution(self):
        content = """
https://google.com/a
https://google.com/b
https://mozilla.org/c
"""
        result = audit_external_source_diversity(content)
        self.assertGreater(len(result['domain_distribution']), 0)
        self.assertEqual(result['domain_distribution'][0]['domain'], 'google.com')

    def test_suggestions_single_domain(self):
        content = 'https://google.com/a https://google.com/b'
        result = audit_external_source_diversity(content)
        self.assertTrue(any('단일' in s or '다양' in s for s in result['suggestions']))

    def test_suggestions_good_diversity(self):
        content = """
https://mozilla.org/a
https://python.org/b
https://react.dev/c
"""
        result = audit_external_source_diversity(content)
        self.assertTrue(any('양호' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = 'https://example.com/test'
        result = audit_external_source_diversity(content)
        self.assertIn('sources', result)
        self.assertIn('domain_distribution', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sources', result['summary'])
        self.assertIn('unique_domains', result['summary'])
        self.assertIn('diversity_score', result['summary'])
        self.assertIn('citation_count', result['summary'])


if __name__ == '__main__':
    unittest.main()
