"""의미 캐시 서비스 테스트"""

import unittest

from services.semantic_cache_service import (
    CacheEntry,
    SemanticCache,
    put,
    get,
    evict_lru,
    get_stats,
    _extract_keywords,
    _jaccard_similarity,
)


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 테스트"""

    def test_영문_키워드(self):
        keywords = _extract_keywords("machine learning model training")
        self.assertIn("machine", keywords)
        self.assertIn("learning", keywords)

    def test_한글_키워드(self):
        keywords = _extract_keywords("인공지능 모델 훈련 방법")
        self.assertIn("인공지능", keywords)
        self.assertIn("모델", keywords)

    def test_불용어_제거(self):
        keywords = _extract_keywords("the model is good")
        self.assertNotIn("the", keywords)
        self.assertNotIn("is", keywords)

    def test_빈_텍스트(self):
        keywords = _extract_keywords("")
        self.assertEqual(len(keywords), 0)


class TestJaccardSimilarity(unittest.TestCase):
    """Jaccard 유사도 테스트"""

    def test_완전_동일(self):
        sim = _jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
        self.assertEqual(sim, 1.0)

    def test_완전_다름(self):
        sim = _jaccard_similarity({"a", "b"}, {"c", "d"})
        self.assertEqual(sim, 0.0)

    def test_부분_겹침(self):
        sim = _jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        self.assertAlmostEqual(sim, 0.5)  # 2/4

    def test_빈_집합(self):
        sim = _jaccard_similarity(set(), {"a"})
        self.assertEqual(sim, 0.0)


class TestPut(unittest.TestCase):
    """put 함수 테스트"""

    def test_항목_추가(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        result = put(cache, "machine learning", "ML 설명")
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].query, "machine learning")

    def test_다중_항목(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "query 1", "response 1")
        cache = put(cache, "query 2", "response 2")
        self.assertEqual(len(cache.entries), 2)

    def test_max_size_초과_시_삭제(self):
        cache = SemanticCache(cache_id="c1", max_size=2)
        cache = put(cache, "query 1", "r1")
        cache = put(cache, "query 2", "r2")
        cache = put(cache, "query 3", "r3")
        self.assertEqual(len(cache.entries), 2)


class TestGet(unittest.TestCase):
    """get 함수 테스트"""

    def test_정확_매칭(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "machine learning model", "ML 모델 설명")
        result = get(cache, "machine learning model", 0.5)
        self.assertIsNotNone(result)
        self.assertEqual(result.response, "ML 모델 설명")

    def test_유사_쿼리_매칭(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "deep learning model training", "DL 학습")
        result = get(cache, "deep learning training", 0.3)
        self.assertIsNotNone(result)

    def test_미매칭(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "machine learning", "ML")
        result = get(cache, "cooking recipe", 0.5)
        self.assertIsNone(result)

    def test_빈_캐시(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        result = get(cache, "anything", 0.5)
        self.assertIsNone(result)

    def test_히트_카운트_증가(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "machine learning model", "ML")
        entry = get(cache, "machine learning model", 0.5)
        self.assertEqual(entry.hit_count, 1)
        entry2 = get(cache, "machine learning model", 0.5)
        self.assertEqual(entry2.hit_count, 2)


class TestEvictLru(unittest.TestCase):
    """evict_lru 함수 테스트"""

    def test_빈_캐시(self):
        cache = SemanticCache(cache_id="c1", entries=[], max_size=0)
        result = evict_lru(cache)
        self.assertEqual(len(result.entries), 0)

    def test_정상_삭제(self):
        cache = SemanticCache(cache_id="c1", max_size=1)
        cache = put(cache, "q1", "r1")
        cache = put(cache, "q2", "r2")
        self.assertEqual(len(cache.entries), 1)


class TestGetStats(unittest.TestCase):
    """get_stats 함수 테스트"""

    def test_빈_캐시_통계(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        stats = get_stats(cache)
        self.assertEqual(stats["entry_count"], 0)
        self.assertEqual(stats["total_hits"], 0)

    def test_항목_있는_캐시(self):
        cache = SemanticCache(cache_id="c1", max_size=10)
        cache = put(cache, "query test", "response")
        stats = get_stats(cache)
        self.assertEqual(stats["entry_count"], 1)
        self.assertGreater(stats["utilization"], 0)


if __name__ == "__main__":
    unittest.main()
