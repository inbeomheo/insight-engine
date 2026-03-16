"""R47: 캐시 히트 시 cache_age_seconds 필드 테스트."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from services.core.cache_service import AICacheService


class TestCacheServiceCachedAt(unittest.TestCase):
    """AICacheService.get()이 _cached_at을 포함하는지 테스트."""

    def setUp(self):
        self.db_path = os.path.join(tempfile.mkdtemp(), 'test_cache.db')
        self.cache = AICacheService(db_path=self.db_path, ttl_days=1)

    def test_get_includes_cached_at(self):
        """캐시 조회 시 _cached_at 필드가 결과에 포함된다."""
        self.cache.put('k1', 'vid1', 'blog_seo', 'gemini', 'medium', 'conversational',
                       {'title': 'test', 'content': 'hello'})
        result = self.cache.get('k1')
        self.assertIsNotNone(result)
        self.assertIn('_cached_at', result)
        self.assertIsInstance(result['_cached_at'], float)
        self.assertAlmostEqual(result['_cached_at'], time.time(), delta=5)

    def test_cached_at_not_in_miss(self):
        """캐시 미스 시 None 반환."""
        result = self.cache.get('nonexistent')
        self.assertIsNone(result)

    def test_cached_at_reflects_creation_time(self):
        """_cached_at은 put 시점의 시각을 반영한다."""
        before = time.time()
        self.cache.put('k2', 'vid2', 'summary', 'deepseek', 'short', 'expert',
                       {'title': 't', 'content': 'c'})
        after = time.time()
        result = self.cache.get('k2')
        self.assertGreaterEqual(result['_cached_at'], before)
        self.assertLessEqual(result['_cached_at'], after)

    def test_cached_at_not_persisted_in_json(self):
        """_cached_at은 DB의 result_json에 저장되지 않고 get 시 동적으로 추가된다."""
        self.cache.put('k3', 'vid3', 'blog_seo', 'gemini', 'medium', 'conversational',
                       {'title': 'test', 'content': 'hello'})
        # DB에서 직접 result_json 확인
        import json
        with self.cache._get_conn() as conn:
            row = conn.execute(
                "SELECT result_json FROM ai_cache WHERE cache_key = ?", ('k3',)
            ).fetchone()
        stored = json.loads(row['result_json'])
        self.assertNotIn('_cached_at', stored)


if __name__ == '__main__':
    unittest.main()
