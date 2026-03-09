"""번역 메모리 서비스 테스트."""
import unittest

from services.translation_memory_service import (
    TranslationEntry,
    TranslationMatch,
    store_translation,
    lookup_memory,
    get_memory_stats,
    clear_memory,
    _jaccard_similarity,
    _memory_store,
)


class TestJaccardSimilarity(unittest.TestCase):
    """Jaccard 유사도 계산 테스트."""

    def test_identical_texts(self):
        """동일한 텍스트는 유사도 1.0."""
        self.assertEqual(_jaccard_similarity('hello world', 'hello world'), 1.0)

    def test_completely_different(self):
        """완전히 다른 텍스트는 유사도 0.0."""
        self.assertEqual(_jaccard_similarity('hello world', '안녕 세상'), 0.0)

    def test_partial_overlap(self):
        """부분 겹침 유사도."""
        # {"hello", "world"} ∩ {"hello", "earth"} = {"hello"} → 1/3
        sim = _jaccard_similarity('hello world', 'hello earth')
        self.assertAlmostEqual(sim, 1 / 3, places=2)

    def test_empty_texts(self):
        """빈 텍스트 쌍은 유사도 1.0."""
        self.assertEqual(_jaccard_similarity('', ''), 1.0)

    def test_one_empty(self):
        """한쪽만 빈 텍스트는 유사도 0.0."""
        self.assertEqual(_jaccard_similarity('hello', ''), 0.0)
        self.assertEqual(_jaccard_similarity('', 'hello'), 0.0)

    def test_case_insensitive(self):
        """대소문자 무시."""
        self.assertEqual(_jaccard_similarity('Hello World', 'hello world'), 1.0)


class TestStoreTranslation(unittest.TestCase):
    """번역 저장 테스트."""

    def setUp(self):
        clear_memory()

    def test_store_basic(self):
        """기본 번역 저장."""
        entry = store_translation('안녕하세요', 'Hello', 'ko', 'en')
        self.assertIsInstance(entry, TranslationEntry)
        self.assertEqual(entry.source, '안녕하세요')
        self.assertEqual(entry.target, 'Hello')
        self.assertEqual(entry.source_lang, 'ko')
        self.assertEqual(entry.target_lang, 'en')
        self.assertEqual(entry.use_count, 0)
        self.assertTrue(len(entry.entry_id) > 0)

    def test_store_strips_whitespace(self):
        """공백 제거."""
        entry = store_translation('  인사말  ', '  greeting  ', 'ko', 'en')
        self.assertEqual(entry.source, '인사말')
        self.assertEqual(entry.target, 'greeting')

    def test_store_normalizes_lang(self):
        """언어 코드 소문자 정규화."""
        entry = store_translation('test', 'テスト', 'EN', 'JA')
        self.assertEqual(entry.source_lang, 'en')
        self.assertEqual(entry.target_lang, 'ja')

    def test_store_increments_count(self):
        """저장할 때마다 메모리 크기 증가."""
        store_translation('a', 'A', 'ko', 'en')
        store_translation('b', 'B', 'ko', 'en')
        self.assertEqual(len(_memory_store), 2)

    def test_created_at_populated(self):
        """생성 시각이 자동 설정."""
        entry = store_translation('test', 'test', 'ko', 'en')
        self.assertTrue(len(entry.created_at) > 0)


class TestLookupMemory(unittest.TestCase):
    """번역 메모리 검색 테스트."""

    def setUp(self):
        clear_memory()

    def test_exact_match(self):
        """정확 매치 검색."""
        store_translation('인공지능은 미래를 변화시킵니다', 'AI changes the future', 'ko', 'en')
        result = lookup_memory('인공지능은 미래를 변화시킵니다', 'en')
        self.assertIsNotNone(result)
        self.assertTrue(result.exact)
        self.assertEqual(result.similarity, 1.0)
        self.assertEqual(result.entry.target, 'AI changes the future')

    def test_fuzzy_match(self):
        """유사 매치 검색 (Jaccard >= 0.7)."""
        store_translation(
            '인공지능 기술은 미래를 크게 변화시킵니다',
            'AI technology will greatly change the future',
            'ko', 'en'
        )
        # 유사한 문장으로 검색
        result = lookup_memory('인공지능 기술은 미래를 변화시킵니다', 'en')
        if result:
            self.assertFalse(result.exact)
            self.assertGreaterEqual(result.similarity, 0.7)

    def test_no_match(self):
        """매치 없는 경우 None 반환."""
        store_translation('안녕하세요', 'Hello', 'ko', 'en')
        result = lookup_memory('완전히 다른 문장입니다', 'en')
        self.assertIsNone(result)

    def test_wrong_target_lang(self):
        """목표 언어가 다르면 매치 안 됨."""
        store_translation('테스트', 'test', 'ko', 'en')
        result = lookup_memory('테스트', 'ja')
        self.assertIsNone(result)

    def test_empty_sentence(self):
        """빈 문장 검색."""
        result = lookup_memory('', 'en')
        self.assertIsNone(result)

    def test_use_count_increment(self):
        """매치 시 사용 횟수 증가."""
        store_translation('감사합니다', 'Thank you', 'ko', 'en')
        lookup_memory('감사합니다', 'en')
        lookup_memory('감사합니다', 'en')
        stats = get_memory_stats()
        self.assertEqual(stats['most_used']['use_count'], 2)

    def test_exact_match_priority(self):
        """정확 매치가 유사 매치보다 우선."""
        store_translation('데이터 분석 결과', 'Data analysis results', 'ko', 'en')
        store_translation('데이터 분석 결과', 'Exact data analysis results', 'ko', 'en')
        result = lookup_memory('데이터 분석 결과', 'en')
        self.assertIsNotNone(result)
        self.assertTrue(result.exact)


class TestGetMemoryStats(unittest.TestCase):
    """메모리 통계 테스트."""

    def setUp(self):
        clear_memory()

    def test_empty_stats(self):
        """빈 메모리 통계."""
        stats = get_memory_stats()
        self.assertEqual(stats['total_entries'], 0)
        self.assertEqual(stats['language_pairs'], {})
        self.assertIsNone(stats['most_used'])
        self.assertEqual(stats['avg_use_count'], 0.0)

    def test_populated_stats(self):
        """데이터 있는 통계."""
        store_translation('안녕', 'Hello', 'ko', 'en')
        store_translation('감사', 'Thanks', 'ko', 'en')
        store_translation('テスト', 'test', 'ja', 'en')

        stats = get_memory_stats()
        self.assertEqual(stats['total_entries'], 3)
        self.assertEqual(stats['language_pairs']['ko->en'], 2)
        self.assertEqual(stats['language_pairs']['ja->en'], 1)
        self.assertIsNotNone(stats['most_used'])

    def test_most_used_tracking(self):
        """가장 많이 사용된 항목 추적."""
        store_translation('자주 쓰는 문장', 'Frequently used', 'ko', 'en')
        store_translation('가끔 쓰는 문장', 'Rarely used', 'ko', 'en')

        # 첫 번째 항목을 3번 조회
        for _ in range(3):
            lookup_memory('자주 쓰는 문장', 'en')

        stats = get_memory_stats()
        self.assertEqual(stats['most_used']['source'], '자주 쓰는 문장')
        self.assertEqual(stats['most_used']['use_count'], 3)


class TestClearMemory(unittest.TestCase):
    """메모리 초기화 테스트."""

    def setUp(self):
        clear_memory()

    def test_clear_returns_count(self):
        """초기화 시 삭제된 항목 수 반환."""
        store_translation('a', 'A', 'ko', 'en')
        store_translation('b', 'B', 'ko', 'en')
        count = clear_memory()
        self.assertEqual(count, 2)

    def test_clear_empty(self):
        """빈 메모리 초기화."""
        count = clear_memory()
        self.assertEqual(count, 0)

    def test_clear_resets_store(self):
        """초기화 후 검색 불가."""
        store_translation('테스트', 'test', 'ko', 'en')
        clear_memory()
        result = lookup_memory('테스트', 'en')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
