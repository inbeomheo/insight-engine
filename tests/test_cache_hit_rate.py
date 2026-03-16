"""캐시 hit_rate 필드 테스트 (R36)."""
import os
import tempfile
import unittest

from services.core.cache_service import AICacheService


class TestCacheHitRate(unittest.TestCase):
    """get_stats()에 hit_rate 필드가 포함되는지 검증."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache = AICacheService(
            db_path=os.path.join(self.tmpdir, 'test_cache.db'),
            ttl_days=1,
            max_size_mb=10,
        )

    def test_hit_rate_zero_when_no_requests(self):
        """요청이 없으면 hit_rate = 0.0."""
        stats = self.cache.get_stats()
        self.assertIn('hit_rate', stats)
        self.assertEqual(stats['hit_rate'], 0.0)
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['misses'], 0)

    def test_hit_rate_after_miss(self):
        """존재하지 않는 키 조회 → miss 증가."""
        self.cache.get('nonexistent')
        stats = self.cache.get_stats()
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['hit_rate'], 0.0)

    def test_hit_rate_after_hit(self):
        """캐시에 넣고 조회 → hit 증가, hit_rate = 1.0."""
        key = AICacheService.make_key('v1', 'blog_seo', 'gemini', 'medium', 'conversational')
        self.cache.put(key, 'v1', 'blog_seo', 'gemini', 'medium', 'conversational', {'title': 'test'})
        self.cache.get(key)
        stats = self.cache.get_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 0)
        self.assertEqual(stats['hit_rate'], 1.0)

    def test_hit_rate_mixed(self):
        """히트 1 + 미스 1 → hit_rate = 0.5."""
        key = AICacheService.make_key('v1', 'blog_seo', 'gemini', 'medium', 'conversational')
        self.cache.put(key, 'v1', 'blog_seo', 'gemini', 'medium', 'conversational', {'title': 'test'})
        self.cache.get(key)        # hit
        self.cache.get('missing')  # miss
        stats = self.cache.get_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hit_rate'], 0.5)

    def test_hit_rate_in_api_response(self):
        """API 응답에서도 hit_rate 필드 존재 검증."""
        from unittest.mock import patch
        from app import create_app

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            resp = client.get('/api/cache/stats', headers={'Origin': 'http://localhost:3000'})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn('hit_rate', data)
            self.assertIn('hits', data)
            self.assertIn('misses', data)
            self.assertIsInstance(data['hit_rate'], float)


if __name__ == '__main__':
    unittest.main()
