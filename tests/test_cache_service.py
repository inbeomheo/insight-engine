"""
AI 결과 캐시 서비스 테스트
"""
import os
import tempfile
import time
import unittest

from services.cache_service import AICacheService


class TestAICacheService(unittest.TestCase):
    """AICacheService 단위 테스트"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, 'test_cache.db')
        self.cache = AICacheService(self.db_path, ttl_days=1, max_size_mb=1)

    def tearDown(self):
        try:
            os.remove(self.db_path)
            # WAL 파일도 정리
            for suffix in ['-wal', '-shm']:
                path = self.db_path + suffix
                if os.path.exists(path):
                    os.remove(path)
            os.rmdir(self.tmp_dir)
        except OSError:
            pass

    def test_make_key_deterministic(self):
        """동일 입력이면 같은 키 반환"""
        key1 = AICacheService.make_key('abc', 'summary', 'gemini/flash', 'medium', 'conversational')
        key2 = AICacheService.make_key('abc', 'summary', 'gemini/flash', 'medium', 'conversational')
        self.assertEqual(key1, key2)

    def test_make_key_differs(self):
        """다른 입력이면 다른 키 반환"""
        key1 = AICacheService.make_key('abc', 'summary', 'gemini/flash')
        key2 = AICacheService.make_key('abc', 'blog_seo', 'gemini/flash')
        self.assertNotEqual(key1, key2)

    def test_put_and_get(self):
        """저장 후 조회"""
        key = AICacheService.make_key('v1', 'summary', 'model1')
        result = {'title': '테스트', 'content': '내용'}
        self.cache.put(key, 'v1', 'summary', 'model1', 'medium', 'conversational', result)

        cached = self.cache.get(key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['title'], '테스트')

    def test_get_miss(self):
        """없는 키 조회 시 None"""
        self.assertIsNone(self.cache.get('nonexistent'))

    def test_ttl_expiry(self):
        """TTL 만료 시 None 반환"""
        cache = AICacheService(self.db_path, ttl_days=0, max_size_mb=1)  # 0일 = 즉시 만료
        key = AICacheService.make_key('v1', 's', 'm')
        cache.put(key, 'v1', 's', 'm', 'medium', 'conv', {'data': 1})
        # ttl_days=0이면 ttl_seconds=0, 저장 즉시 만료
        time.sleep(0.01)
        self.assertIsNone(cache.get(key))

    def test_clear_by_video_id(self):
        """특정 video_id만 삭제"""
        key1 = AICacheService.make_key('v1', 's', 'm')
        key2 = AICacheService.make_key('v2', 's', 'm')
        self.cache.put(key1, 'v1', 's', 'm', 'medium', 'conv', {'a': 1})
        self.cache.put(key2, 'v2', 's', 'm', 'medium', 'conv', {'b': 2})

        deleted = self.cache.clear('v1')
        self.assertEqual(deleted, 1)
        self.assertIsNone(self.cache.get(key1))
        self.assertIsNotNone(self.cache.get(key2))

    def test_clear_all(self):
        """전체 삭제"""
        key1 = AICacheService.make_key('v1', 's', 'm')
        key2 = AICacheService.make_key('v2', 's', 'm')
        self.cache.put(key1, 'v1', 's', 'm', 'medium', 'conv', {'a': 1})
        self.cache.put(key2, 'v2', 's', 'm', 'medium', 'conv', {'b': 2})

        deleted = self.cache.clear()
        self.assertEqual(deleted, 2)

    def test_stats(self):
        """통계 반환"""
        key = AICacheService.make_key('v1', 's', 'm')
        self.cache.put(key, 'v1', 's', 'm', 'medium', 'conv', {'data': 'x' * 100})

        stats = self.cache.get_stats()
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['total_bytes'], 0)

    def test_eviction(self):
        """용량 초과 시 LRU eviction 동작"""
        # 1KB 캐시로 설정
        tiny_cache = AICacheService(self.db_path, ttl_days=1, max_size_mb=0.001)  # ~1KB
        large_data = {'content': 'x' * 500}

        # 여러 항목 추가하면 오래된 것이 삭제되어야 함
        for i in range(5):
            key = AICacheService.make_key(f'v{i}', 's', 'm')
            tiny_cache.put(key, f'v{i}', 's', 'm', 'medium', 'conv', large_data)

        stats = tiny_cache.get_stats()
        # 일부가 삭제되어 5개보다 적어야 함
        self.assertLess(stats['count'], 5)

    def test_purge_expired(self):
        """만료 항목 정리"""
        cache = AICacheService(self.db_path, ttl_days=0, max_size_mb=1)
        key = AICacheService.make_key('v1', 's', 'm')
        cache.put(key, 'v1', 's', 'm', 'medium', 'conv', {'data': 1})
        time.sleep(0.01)

        purged = cache.purge_expired()
        self.assertEqual(purged, 1)


if __name__ == '__main__':
    unittest.main()
