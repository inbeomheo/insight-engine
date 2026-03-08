"""Trend Monitor Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.analytics.trend_monitor_service import TrendMonitorService


class TestTrendMonitorService(unittest.TestCase):

    def setUp(self):
        self.svc = TrendMonitorService()

    def test_add_keyword(self):
        self.svc.add_keyword('AI')
        self.assertIn('AI', self.svc.get_keywords())

    def test_add_keyword_no_duplicate(self):
        self.svc.add_keyword('AI')
        self.svc.add_keyword('AI')
        self.assertEqual(self.svc.get_keywords().count('AI'), 1)

    def test_remove_keyword(self):
        self.svc.add_keyword('AI')
        self.svc.remove_keyword('AI')
        self.assertNotIn('AI', self.svc.get_keywords())

    def test_remove_keyword_nonexistent(self):
        self.svc.remove_keyword('nonexistent')
        self.assertEqual(len(self.svc.get_keywords()), 0)

    def test_get_keywords_returns_copy(self):
        self.svc.add_keyword('AI')
        keywords = self.svc.get_keywords()
        keywords.append('extra')
        self.assertEqual(len(self.svc.get_keywords()), 1)

    def test_fetch_trends_no_keywords(self):
        result = self.svc.fetch_trends()
        self.assertIn('error', result)

    def test_fetch_trends_no_pytrends(self):
        self.svc.add_keyword('Python')
        with patch.dict('sys.modules', {'pytrends': None, 'pytrends.request': None}):
            result = self.svc.fetch_trends()
            # pytrends 미설치 시 에러 반환
            self.assertTrue('error' in result or 'stub' in result)

    def test_get_cached_empty(self):
        result = self.svc.get_cached()
        self.assertIsNone(result['updated_at'])
        self.assertEqual(result['data'], {})

    def test_get_cached_after_manual_update(self):
        self.svc._cache = {'AI': [{'date': '2026-01-01', 'value': 80}]}
        self.svc._cache_updated = '2026-01-01T00:00:00+00:00'
        result = self.svc.get_cached()
        self.assertIn('AI', result['data'])
        self.assertEqual(result['updated_at'], '2026-01-01T00:00:00+00:00')

    def test_get_rising_keywords_no_keywords(self):
        result = self.svc.get_rising_keywords()
        self.assertIn('error', result)

    def test_get_rising_keywords_no_pytrends(self):
        result = self.svc.get_rising_keywords(keywords=['Python'])
        self.assertTrue('error' in result or 'stub' in result)

    def test_fetch_trends_with_explicit_keywords(self):
        result = self.svc.fetch_trends(keywords=['Python', 'AI'])
        # pytrends 미설치 시에도 키워드 목록은 반환
        if 'stub' in result:
            self.assertEqual(result['keywords'], ['Python', 'AI'])


if __name__ == '__main__':
    unittest.main()
