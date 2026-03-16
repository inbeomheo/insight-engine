"""R151: cache_service.get_stats에 usage_percent 필드 추가 테스트."""
import os
import tempfile
import unittest
from services.core.cache_service import AICacheService


class TestCacheUsagePercent(unittest.TestCase):
    """캐시 통계의 usage_percent 필드 검증."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self._tmpdir, 'test_cache.db')
        self.cache = AICacheService(db_path, ttl_days=1, max_size_mb=1)

    def test_usage_percent_empty(self):
        """빈 캐시의 usage_percent는 0.0."""
        stats = self.cache.get_stats()
        self.assertIn('usage_percent', stats)
        self.assertEqual(stats['usage_percent'], 0.0)

    def test_usage_percent_with_data(self):
        """데이터 저장 후 usage_percent가 0보다 큰지 확인."""
        key = self.cache.make_key('vid1', 'blog_seo', 'gemini', 'medium', 'conversational')
        self.cache.put(key, 'vid1', 'blog_seo', 'gemini', 'medium', 'conversational',
                       {'title': 'test', 'content': 'x' * 1000})
        stats = self.cache.get_stats()
        self.assertGreater(stats['usage_percent'], 0.0)
        self.assertLessEqual(stats['usage_percent'], 100.0)

    def test_usage_percent_is_float(self):
        """usage_percent는 float 타입."""
        stats = self.cache.get_stats()
        self.assertIsInstance(stats['usage_percent'], float)


if __name__ == '__main__':
    unittest.main()
