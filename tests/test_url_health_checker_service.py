"""URL Health Checker 서비스 테스트."""
import unittest
from services.seo.url_health_checker_service import check_url_health


class TestUrlHealthChecker(unittest.TestCase):

    def test_empty_content(self):
        result = check_url_health('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_urls'], 0)

    def test_none_content(self):
        result = check_url_health(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_urls(self):
        content = 'URL이 없는 일반 텍스트입니다.'
        result = check_url_health(content)
        self.assertEqual(result['summary']['total_urls'], 0)

    def test_healthy_https_url(self):
        content = '자세한 내용은 https://docs.python.org/3/ 를 참조하세요.'
        result = check_url_health(content)
        self.assertGreater(result['summary']['total_urls'], 0)
        self.assertEqual(result['summary']['healthy'], result['summary']['total_urls'])

    def test_http_warning(self):
        content = '링크: http://insecure-site.org/page'
        result = check_url_health(content)
        issues = result['url_results'][0]['issues']
        self.assertTrue(any('HTTP' in i for i in issues))

    def test_placeholder_domain(self):
        content = '예시: https://your-domain.com/api'
        result = check_url_health(content)
        issues = result['url_results'][0]['issues']
        self.assertTrue(any('플레이스홀더' in i for i in issues))

    def test_markdown_link_extraction(self):
        content = '[파이썬 문서](https://docs.python.org/3/)를 참조하세요.'
        result = check_url_health(content)
        self.assertGreater(result['summary']['total_urls'], 0)

    def test_html_link_extraction(self):
        content = '<a href="https://github.com/repo">GitHub</a>'
        result = check_url_health(content)
        self.assertGreater(result['summary']['total_urls'], 0)

    def test_suspicious_extension(self):
        content = 'Download: https://site.com/file.exe'
        result = check_url_health(content)
        issues = result['url_results'][0]['issues']
        self.assertTrue(any('의심스러운' in i for i in issues))

    def test_long_url(self):
        long_path = 'a' * 200
        content = f'https://site.com/{long_path}'
        result = check_url_health(content)
        issues = result['url_results'][0]['issues']
        self.assertTrue(any('길이' in i for i in issues))

    def test_health_rate(self):
        content = 'https://good-site.com/page http://bad-site.org/page'
        result = check_url_health(content)
        self.assertGreater(result['summary']['total_urls'], 0)
        self.assertLessEqual(result['summary']['health_rate'], 100.0)

    def test_score_range(self):
        content = 'https://valid-url.com/path'
        result = check_url_health(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_with_issues(self):
        content = 'http://insecure.org/page https://your-domain.com/api'
        result = check_url_health(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = 'https://test-site.com'
        result = check_url_health(content)
        self.assertIn('url_results', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_urls', result['summary'])
        self.assertIn('health_rate', result['summary'])


if __name__ == '__main__':
    unittest.main()
