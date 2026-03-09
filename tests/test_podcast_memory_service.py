"""
PodcastMemoryService 단위 테스트 (T12.4)
"""
import unittest
from services.podcast_memory_service import (
    PodcastMemoryService,
    EpisodeMemory,
    MemoryResult,
    _split_sentences,
    _extract_keywords,
)


class TestSplitSentences(unittest.TestCase):
    """문장 분할 테스트"""

    def test_period_split(self):
        result = _split_sentences("첫째. 둘째. 셋째.")
        self.assertEqual(len(result), 3)

    def test_question_mark(self):
        result = _split_sentences("이건 뭐죠? 그건 뭔가요?")
        self.assertEqual(len(result), 2)

    def test_empty_text(self):
        self.assertEqual(_split_sentences(''), [])
        self.assertEqual(_split_sentences('   '), [])

    def test_single_char_excluded(self):
        """1글자 문장은 제외"""
        result = _split_sentences("A. 긴 문장입니다.")
        # 'A'는 len > 1 조건 미충족으로 제외될 수 있음
        for s in result:
            self.assertGreater(len(s), 1)


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 테스트"""

    def test_basic_extraction(self):
        keywords = _extract_keywords("인공지능 머신러닝 딥러닝")
        self.assertIn("인공지능", keywords)
        self.assertIn("머신러닝", keywords)

    def test_stopwords_excluded(self):
        """불용어 제외"""
        keywords = _extract_keywords("the is are 인공지능")
        self.assertNotIn("the", keywords)
        self.assertIn("인공지능", keywords)

    def test_empty_text(self):
        self.assertEqual(_extract_keywords(''), [])

    def test_duplicates_removed(self):
        keywords = _extract_keywords("인공지능 인공지능 인공지능")
        self.assertEqual(keywords.count("인공지능"), 1)

    def test_short_words_excluded(self):
        """2글자 미만 제외"""
        keywords = _extract_keywords("a 인공지능")
        self.assertNotIn("a", keywords)


class TestStoreEpisode(unittest.TestCase):
    """에피소드 저장 테스트"""

    def setUp(self):
        self.svc = PodcastMemoryService()

    def test_basic_store(self):
        """기본 저장"""
        mem = self.svc.store_episode("ep-001", "인공지능에 대한 이야기입니다.")
        self.assertIsInstance(mem, EpisodeMemory)
        self.assertEqual(mem.episode_id, "ep-001")
        self.assertGreater(len(mem.keywords), 0)

    def test_store_with_metadata(self):
        """메타데이터 포함 저장"""
        meta = {"title": "AI 특집", "date": "2026-01-01"}
        mem = self.svc.store_episode("ep-002", "테스트 콘텐츠입니다.", metadata=meta)
        self.assertEqual(mem.metadata["title"], "AI 특집")

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.svc.store_episode("", "내용")

    def test_empty_content_raises(self):
        with self.assertRaises(ValueError):
            self.svc.store_episode("ep-001", "")

    def test_overwrite_existing(self):
        """같은 ID로 재저장 시 덮어쓰기"""
        self.svc.store_episode("ep-001", "첫 번째 내용입니다.")
        self.svc.store_episode("ep-001", "두 번째 내용입니다.")
        mem = self.svc.get_episode("ep-001")
        self.assertIn("두 번째", mem.content)

    def test_stored_at_set(self):
        """stored_at 필드 설정"""
        mem = self.svc.store_episode("ep-001", "테스트.")
        self.assertGreater(len(mem.stored_at), 0)


class TestSearchPodcastMemory(unittest.TestCase):
    """검색 테스트"""

    def setUp(self):
        self.svc = PodcastMemoryService()
        self.svc.store_episode(
            "ep-001",
            "인공지능과 머신러닝은 현대 기술의 핵심입니다. 딥러닝은 인공지능의 하위 분야입니다."
        )
        self.svc.store_episode(
            "ep-002",
            "요리 레시피와 건강한 식단에 대해 알아봅니다. 채소를 많이 먹는 것이 중요합니다."
        )

    def test_basic_search(self):
        """기본 검색"""
        results = self.svc.search_podcast_memory("인공지능 딥러닝")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].episode_id, "ep-001")

    def test_search_result_type(self):
        """검색 결과 타입 확인"""
        results = self.svc.search_podcast_memory("인공지능")
        for r in results:
            self.assertIsInstance(r, MemoryResult)

    def test_relevance_score(self):
        """관련도 점수 범위"""
        results = self.svc.search_podcast_memory("인공지능 머신러닝")
        for r in results:
            self.assertGreaterEqual(r.relevance, 0.0)
            self.assertLessEqual(r.relevance, 1.0)

    def test_no_match(self):
        """매칭되지 않는 쿼리 → 빈 결과"""
        results = self.svc.search_podcast_memory("양자역학 초끈이론")
        self.assertEqual(len(results), 0)

    def test_empty_query_raises(self):
        with self.assertRaises(ValueError):
            self.svc.search_podcast_memory("")

    def test_results_sorted_by_relevance(self):
        """결과가 관련도 내림차순"""
        self.svc.store_episode(
            "ep-003",
            "인공지능 기술이 발전하고 있습니다."
        )
        results = self.svc.search_podcast_memory("인공지능 머신러닝 딥러닝")
        if len(results) >= 2:
            self.assertGreaterEqual(results[0].relevance, results[1].relevance)

    def test_matched_text_not_empty(self):
        """matched_text가 비어있지 않음"""
        results = self.svc.search_podcast_memory("인공지능")
        for r in results:
            self.assertGreater(len(r.matched_text), 0)


class TestPodcastMemoryManagement(unittest.TestCase):
    """메모리 관리 테스트"""

    def setUp(self):
        self.svc = PodcastMemoryService()

    def test_get_episode(self):
        self.svc.store_episode("ep-001", "테스트 내용입니다.")
        mem = self.svc.get_episode("ep-001")
        self.assertIsNotNone(mem)
        self.assertEqual(mem.episode_id, "ep-001")

    def test_get_nonexistent(self):
        self.assertIsNone(self.svc.get_episode("nonexistent"))

    def test_list_episodes(self):
        self.svc.store_episode("ep-001", "내용1.")
        self.svc.store_episode("ep-002", "내용2.")
        ids = self.svc.list_episodes()
        self.assertEqual(len(ids), 2)
        self.assertIn("ep-001", ids)
        self.assertIn("ep-002", ids)

    def test_delete_episode(self):
        self.svc.store_episode("ep-001", "내용.")
        result = self.svc.delete_episode("ep-001")
        self.assertTrue(result)
        self.assertIsNone(self.svc.get_episode("ep-001"))

    def test_delete_nonexistent(self):
        result = self.svc.delete_episode("nonexistent")
        self.assertFalse(result)

    def test_clear(self):
        self.svc.store_episode("ep-001", "내용1.")
        self.svc.store_episode("ep-002", "내용2.")
        count = self.svc.clear()
        self.assertEqual(count, 2)
        self.assertEqual(len(self.svc.list_episodes()), 0)


if __name__ == '__main__':
    unittest.main()
