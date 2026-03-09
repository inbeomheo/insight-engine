"""메모리 컨트롤 서비스 테스트"""
import unittest
from datetime import datetime, timedelta
from services.memory_control_service import (
    MemoryEntry, MemoryStore,
    add_memory, recall, compress_memories,
    expire_memories, summarize_store,
)


class TestAddMemory(unittest.TestCase):
    """메모리 추가 테스트"""

    def setUp(self):
        self.store = MemoryStore(store_id='s1', entries=[], max_entries=10)

    def test_basic_add(self):
        result = add_memory(self.store, '테스트 내용', importance=0.8)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].content, '테스트 내용')
        self.assertEqual(result.entries[0].importance, 0.8)

    def test_tags(self):
        result = add_memory(self.store, '내용', tags=['태그1', '태그2'])
        self.assertEqual(result.entries[0].tags, ['태그1', '태그2'])

    def test_ttl(self):
        result = add_memory(self.store, '내용', ttl_hours=24)
        self.assertIsNotNone(result.entries[0].expires_at)

    def test_no_ttl(self):
        result = add_memory(self.store, '내용')
        self.assertIsNone(result.entries[0].expires_at)

    def test_importance_clamp(self):
        """중요도 범위 제한 (0~1)"""
        result = add_memory(self.store, '내용', importance=1.5)
        self.assertEqual(result.entries[0].importance, 1.0)
        result = add_memory(self.store, '내용', importance=-0.5)
        self.assertEqual(result.entries[0].importance, 0.0)

    def test_max_entries_overflow(self):
        """최대 항목 초과 시 중요도 낮은 것 제거"""
        store = MemoryStore(store_id='s1', entries=[], max_entries=3)
        for i in range(4):
            store = add_memory(store, f'내용{i}', importance=i * 0.25)
        self.assertEqual(len(store.entries), 3)
        # 가장 중요도 높은 3개만 남아야 함
        importances = [e.importance for e in store.entries]
        self.assertNotIn(0.0, importances)

    def test_created_at_set(self):
        result = add_memory(self.store, '내용')
        self.assertTrue(len(result.entries[0].created_at) > 0)

    def test_entry_id_generated(self):
        result = add_memory(self.store, '내용')
        self.assertTrue(len(result.entries[0].entry_id) > 0)


class TestRecall(unittest.TestCase):
    """메모리 회상 테스트"""

    def setUp(self):
        self.store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '파이썬 프로그래밍 기초', 0.9, '2024-01-01', None, ['프로그래밍']),
            MemoryEntry('e2', '자바 웹 개발', 0.7, '2024-01-02', None, ['개발']),
            MemoryEntry('e3', '데이터베이스 설계', 0.5, '2024-01-03', None, ['설계']),
            MemoryEntry('e4', '파이썬 머신러닝', 0.8, '2024-01-04', None, ['AI', '프로그래밍']),
        ])

    def test_keyword_recall(self):
        results = recall(self.store, '파이썬')
        self.assertGreater(len(results), 0)
        # 파이썬 관련 항목이 상위에
        self.assertTrue(any('파이썬' in e.content for e in results[:2]))

    def test_tag_recall(self):
        """태그 매칭 회상"""
        results = recall(self.store, '프로그래밍')
        self.assertGreater(len(results), 0)

    def test_top_k(self):
        results = recall(self.store, '파이썬', top_k=1)
        self.assertEqual(len(results), 1)

    def test_empty_query(self):
        results = recall(self.store, '')
        self.assertEqual(len(results), 0)

    def test_empty_store(self):
        empty = MemoryStore(store_id='e', entries=[], max_entries=10)
        results = recall(empty, '테스트')
        self.assertEqual(len(results), 0)


class TestCompressMemories(unittest.TestCase):
    """메모리 압축 테스트"""

    def test_compress(self):
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '내용1', 0.9, '', None, []),
            MemoryEntry('e2', '내용2', 0.3, '', None, []),
            MemoryEntry('e3', '내용3', 0.7, '', None, []),
        ], max_entries=10)

        result = compress_memories(store, target_count=2)
        self.assertEqual(len(result.entries), 2)
        # 중요도 높은 것만 남음
        importances = {e.importance for e in result.entries}
        self.assertIn(0.9, importances)
        self.assertNotIn(0.3, importances)

    def test_no_compression_needed(self):
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '내용', 0.5, '', None, []),
        ], max_entries=10)
        result = compress_memories(store, target_count=5)
        self.assertEqual(len(result.entries), 1)

    def test_target_zero(self):
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '내용', 0.5, '', None, []),
        ], max_entries=10)
        result = compress_memories(store, target_count=0)
        self.assertEqual(len(result.entries), 0)


class TestExpireMemories(unittest.TestCase):
    """만료 메모리 제거 테스트"""

    def test_expire_old(self):
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '만료됨', 0.5, '', past, []),
            MemoryEntry('e2', '유효함', 0.5, '', future, []),
            MemoryEntry('e3', '영구', 0.5, '', None, []),
        ], max_entries=10)

        result = expire_memories(store)
        self.assertEqual(len(result.entries), 2)
        ids = {e.entry_id for e in result.entries}
        self.assertNotIn('e1', ids)
        self.assertIn('e2', ids)
        self.assertIn('e3', ids)

    def test_all_expired(self):
        past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '만료1', 0.5, '', past, []),
            MemoryEntry('e2', '만료2', 0.5, '', past, []),
        ], max_entries=10)
        result = expire_memories(store)
        self.assertEqual(len(result.entries), 0)

    def test_custom_current_time(self):
        """커스텀 현재 시각"""
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '내용', 0.5, '', '2024-06-01T00:00:00', []),
        ], max_entries=10)
        result = expire_memories(store, current_time='2024-07-01T00:00:00')
        self.assertEqual(len(result.entries), 0)

    def test_no_expiry(self):
        """만료 없는 항목만"""
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '영구', 0.5, '', None, []),
        ], max_entries=10)
        result = expire_memories(store)
        self.assertEqual(len(result.entries), 1)


class TestSummarizeStore(unittest.TestCase):
    """스토어 요약 테스트"""

    def test_basic_summary(self):
        store = MemoryStore(store_id='s1', entries=[
            MemoryEntry('e1', '내용1', 0.8, '', None, ['태그A']),
            MemoryEntry('e2', '내용2', 0.6, '', None, ['태그A', '태그B']),
        ], max_entries=10)

        summary = summarize_store(store)
        self.assertEqual(summary['total_entries'], 2)
        self.assertEqual(summary['tag_distribution']['태그A'], 2)
        self.assertEqual(summary['tag_distribution']['태그B'], 1)
        self.assertAlmostEqual(summary['avg_importance'], 0.7, places=2)

    def test_empty_store(self):
        store = MemoryStore(store_id='e', entries=[], max_entries=10)
        summary = summarize_store(store)
        self.assertEqual(summary['total_entries'], 0)
        self.assertEqual(summary['avg_importance'], 0.0)


if __name__ == '__main__':
    unittest.main()
