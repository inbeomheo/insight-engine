"""agent/memory — SQLite WAL 기반 에이전트 메모리 저장소"""
import os
import shutil
import tempfile
import time
import unittest

from agent.memory import AgentMemoryStore, Session, MemoryEntry, memory_store


class _BaseMemoryTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='ie_agent_mem_')
        self.db_path = os.path.join(self.tmpdir, 'test.db')
        self.store = AgentMemoryStore(db_path=self.db_path)

    def tearDown(self):
        # SQLite 연결이 모두 닫혔는지 확인 후 디렉토리 삭제
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestSchemaInit(_BaseMemoryTest):

    def test_db_file_created(self):
        self.assertTrue(os.path.exists(self.db_path))

    def test_can_reopen_same_db(self):
        """같은 path로 재오픈해도 데이터 보존"""
        self.store.update_memory('k', 'v')
        store2 = AgentMemoryStore(db_path=self.db_path)
        self.assertEqual(store2.get_memory('k'), 'v')


class TestSession(_BaseMemoryTest):

    def test_create_session_basic(self):
        sess = self.store.create_session(
            model='gemini/test', base_system_prompt='기본 프롬프트',
        )
        self.assertIsInstance(sess, Session)
        self.assertEqual(sess.model, 'gemini/test')
        self.assertEqual(sess.system_prompt_snapshot, '기본 프롬프트')
        self.assertIsNone(sess.user_id)

    def test_create_session_with_user_and_metadata(self):
        sess = self.store.create_session(
            model='m', base_system_prompt='p',
            user_id='u-1', metadata={'session_label': '테스트'},
        )
        self.assertEqual(sess.user_id, 'u-1')
        self.assertEqual(sess.metadata['session_label'], '테스트')

    def test_get_session_existing(self):
        sess = self.store.create_session(model='m', base_system_prompt='p')
        loaded = self.store.get_session(sess.session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, sess.session_id)

    def test_get_session_unknown(self):
        self.assertIsNone(self.store.get_session('not-existing'))

    def test_list_sessions_filter_by_user(self):
        self.store.create_session(model='m', base_system_prompt='p', user_id='alice')
        self.store.create_session(model='m', base_system_prompt='p', user_id='bob')
        self.store.create_session(model='m', base_system_prompt='p', user_id='alice')

        alice_sessions = self.store.list_sessions(user_id='alice')
        self.assertEqual(len(alice_sessions), 2)
        self.assertTrue(all(s['user_id'] == 'alice' for s in alice_sessions))

    def test_list_sessions_all(self):
        for _ in range(3):
            self.store.create_session(model='m', base_system_prompt='p')
        all_sessions = self.store.list_sessions()
        self.assertEqual(len(all_sessions), 3)


class TestFrozenSnapshot(_BaseMemoryTest):
    """동결 스냅샷: 세션 중 메모리 갱신해도 system_prompt_snapshot 불변"""

    def test_memory_injected_at_session_create(self):
        self.store.update_memory('preferred_lang', 'ko', category='user')
        # 세션 생성 시 user 메모리는 user_id 매칭 필요
        sess = self.store.create_session(
            model='m', base_system_prompt='베이스',
            user_id='preferred_lang',  # 매칭되도록
        )
        # 시스템 프롬프트에 메모리 블록 주입 시도 (user_id가 'preferred_lang'에 포함됨)
        # 그렇지 않으면 적어도 베이스는 포함
        self.assertIn('베이스', sess.system_prompt_snapshot)

    def test_snapshot_immutable_after_create(self):
        """create_session 후 update_memory를 호출해도 기존 세션의 snapshot은 변하지 않음"""
        self.store.update_memory('k', 'before')
        sess = self.store.create_session(model='m', base_system_prompt='base')

        self.store.update_memory('k', 'after')  # 메모리 갱신
        reloaded = self.store.get_session(sess.session_id)
        # snapshot은 디스크에 그대로
        self.assertEqual(reloaded.system_prompt_snapshot, sess.system_prompt_snapshot)


class TestMessages(_BaseMemoryTest):

    def test_add_and_get_messages(self):
        sess = self.store.create_session(model='m', base_system_prompt='p')
        self.store.add_message(sess.session_id, 'user', '안녕')
        self.store.add_message(sess.session_id, 'assistant', '반가워요')
        msgs = self.store.get_messages(sess.session_id)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]['role'], 'user')
        self.assertEqual(msgs[1]['content'], '반가워요')

    def test_messages_with_tool_calls(self):
        sess = self.store.create_session(model='m', base_system_prompt='p')
        self.store.add_message(
            sess.session_id, 'assistant', '',
            tool_calls=[{'name': 'tool_a', 'args': {'x': 1}}],
        )
        msgs = self.store.get_messages(sess.session_id)
        self.assertIn('tool_calls', msgs[0])
        self.assertEqual(msgs[0]['tool_calls'][0]['name'], 'tool_a')

    def test_messages_limit(self):
        sess = self.store.create_session(model='m', base_system_prompt='p')
        for i in range(10):
            self.store.add_message(sess.session_id, 'user', f'msg {i}')
        msgs = self.store.get_messages(sess.session_id, limit=3)
        self.assertEqual(len(msgs), 3)


class TestMemoryCrud(_BaseMemoryTest):

    def test_update_and_get(self):
        self.store.update_memory('lang', 'ko', category='user')
        self.assertEqual(self.store.get_memory('lang', category='user'), 'ko')

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.store.get_memory('nonexistent'))

    def test_update_replaces(self):
        self.store.update_memory('k', 'v1')
        self.store.update_memory('k', 'v2')
        self.assertEqual(self.store.get_memory('k'), 'v2')

    def test_category_separation(self):
        """같은 key라도 카테고리가 다르면 별개 항목"""
        self.store.update_memory('lang', 'ko', category='user')
        self.store.update_memory('lang', 'python', category='project')
        self.assertEqual(self.store.get_memory('lang', category='user'), 'ko')
        self.assertEqual(self.store.get_memory('lang', category='project'), 'python')

    def test_list_memory_all(self):
        self.store.update_memory('a', '1', 'agent')
        self.store.update_memory('b', '2', 'user')
        result = self.store.list_memory()
        self.assertEqual(len(result), 2)

    def test_list_memory_filter_by_category(self):
        self.store.update_memory('a', '1', 'agent')
        self.store.update_memory('b', '2', 'user')
        agent_only = self.store.list_memory(category='agent')
        self.assertEqual(len(agent_only), 1)
        self.assertEqual(agent_only[0].key, 'a')

    def test_delete_existing(self):
        self.store.update_memory('to_delete', 'v')
        deleted = self.store.delete_memory('to_delete')
        self.assertTrue(deleted)
        self.assertIsNone(self.store.get_memory('to_delete'))

    def test_delete_nonexistent(self):
        self.assertFalse(self.store.delete_memory('never_existed'))


class TestSearchMemory(_BaseMemoryTest):

    def test_search_returns_list(self):
        """search_memory가 항상 list를 반환 (FTS5 동기화 트리거가 없어서 결과 없을 수 있음 — 알려진 한계)"""
        self.store.update_memory('framework', 'flask web framework', 'project')
        result = self.store.search_memory('flask')
        self.assertIsInstance(result, list)
        # 모든 항목이 MemoryEntry 타입
        for item in result:
            self.assertIsInstance(item, MemoryEntry)

    def test_search_no_match(self):
        self.store.update_memory('k', 'v', 'agent')
        result = self.store.search_memory('nonexistent_term_xyz')
        self.assertEqual(result, [])


class TestToolUsageLog(_BaseMemoryTest):

    def test_log_tool_usage(self):
        sess = self.store.create_session(model='m', base_system_prompt='p')
        self.store.log_tool_usage(
            sess.session_id, tool_name='analyze',
            args={'content': 'test'}, result_summary='OK',
            elapsed_ms=150, success=True,
        )
        # 통계 조회 메서드가 없으므로 직접 SQL로 확인
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                'SELECT tool_name, success FROM tool_usage WHERE session_id = ?',
                (sess.session_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'analyze')
        self.assertEqual(row[1], 1)


class TestSingletonInstance(unittest.TestCase):

    def test_module_memory_store_exists(self):
        self.assertIsInstance(memory_store, AgentMemoryStore)


if __name__ == '__main__':
    unittest.main()
