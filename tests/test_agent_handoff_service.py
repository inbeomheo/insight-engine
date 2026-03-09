"""
에이전트 핸드오프 서비스 테스트
"""

import unittest

from services.agent_handoff_service import (
    AgentContext,
    AgentHandoffService,
    HandoffResult,
)


class TestAgentHandoffService(unittest.TestCase):
    """AgentHandoffService 단위 테스트"""

    def setUp(self):
        self.service = AgentHandoffService()
        self.valid_context = {"task": "번역", "progress": "50%"}

    # ── handoff 기본 동작 ──

    def test_handoff_returns_handoff_result(self):
        """핸드오프 결과가 HandoffResult 타입이어야 한다"""
        result = self.service.handoff("agent_a", "agent_b", self.valid_context)
        self.assertIsInstance(result, HandoffResult)

    def test_handoff_assigns_unique_id(self):
        """각 핸드오프에 고유 ID가 부여된다"""
        r1 = self.service.handoff("a", "b", self.valid_context)
        r2 = self.service.handoff("a", "b", self.valid_context)
        self.assertNotEqual(r1.handoff_id, r2.handoff_id)

    def test_handoff_stores_agents_and_context(self):
        """핸드오프 결과에 에이전트명과 컨텍스트가 저장된다"""
        ctx = {"task": "요약", "progress": "0%", "extra": "data"}
        result = self.service.handoff("writer", "reviewer", ctx)
        self.assertEqual(result.current_agent, "writer")
        self.assertEqual(result.next_agent, "reviewer")
        self.assertEqual(result.context["task"], "요약")
        self.assertEqual(result.context["extra"], "data")

    def test_handoff_status_is_completed(self):
        """정상 핸드오프의 status는 completed"""
        result = self.service.handoff("a", "b", self.valid_context)
        self.assertEqual(result.status, "completed")

    def test_handoff_auto_generates_session_id(self):
        """session_id 미지정 시 자동 생성"""
        result = self.service.handoff("a", "b", self.valid_context)
        self.assertTrue(result.session_id.startswith("session_"))

    def test_handoff_uses_provided_session_id(self):
        """session_id 지정 시 해당 값 사용"""
        result = self.service.handoff("a", "b", self.valid_context, session_id="my_session")
        self.assertEqual(result.session_id, "my_session")

    def test_handoff_defensive_copy_context(self):
        """context 수정이 저장된 결과에 영향 주지 않음"""
        ctx = {"task": "원본", "progress": "0%"}
        result = self.service.handoff("a", "b", ctx)
        ctx["task"] = "변경됨"
        self.assertEqual(result.context["task"], "원본")

    # ── handoff 검증 ──

    def test_handoff_raises_on_empty_current_agent(self):
        """current_agent가 비어있으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("", "b", self.valid_context)

    def test_handoff_raises_on_whitespace_current_agent(self):
        """current_agent가 공백만 있으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("   ", "b", self.valid_context)

    def test_handoff_raises_on_empty_next_agent(self):
        """next_agent가 비어있으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("a", "", self.valid_context)

    def test_handoff_raises_on_same_agents(self):
        """current_agent와 next_agent가 같으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("same", "same", self.valid_context)

    def test_handoff_raises_on_missing_required_keys(self):
        """context에 필수 키(task, progress) 누락 시 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("a", "b", {"task": "번역"})  # progress 누락

    def test_handoff_raises_on_non_dict_context(self):
        """context가 dict가 아니면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.handoff("a", "b", "not a dict")

    # ── get_handoff_history ──

    def test_get_history_empty_session(self):
        """존재하지 않는 세션의 이력은 빈 리스트"""
        result = self.service.get_handoff_history("nonexistent")
        self.assertEqual(result, [])

    def test_get_history_returns_correct_order(self):
        """이력이 시간순으로 반환된다"""
        sid = "test_session"
        self.service.handoff("a", "b", self.valid_context, session_id=sid)
        self.service.handoff("b", "c", self.valid_context, session_id=sid)
        self.service.handoff("c", "d", self.valid_context, session_id=sid)
        history = self.service.get_handoff_history(sid)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].current_agent, "a")
        self.assertEqual(history[1].current_agent, "b")
        self.assertEqual(history[2].current_agent, "c")

    def test_get_history_isolates_sessions(self):
        """다른 세션의 이력이 섞이지 않는다"""
        self.service.handoff("a", "b", self.valid_context, session_id="s1")
        self.service.handoff("x", "y", self.valid_context, session_id="s2")
        h1 = self.service.get_handoff_history("s1")
        h2 = self.service.get_handoff_history("s2")
        self.assertEqual(len(h1), 1)
        self.assertEqual(len(h2), 1)
        self.assertEqual(h1[0].current_agent, "a")
        self.assertEqual(h2[0].current_agent, "x")

    # ── get_handoff_by_id ──

    def test_get_by_id_found(self):
        """핸드오프 ID로 조회 가능"""
        result = self.service.handoff("a", "b", self.valid_context)
        found = self.service.get_handoff_by_id(result.handoff_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.handoff_id, result.handoff_id)

    def test_get_by_id_not_found(self):
        """존재하지 않는 ID는 None 반환"""
        self.assertIsNone(self.service.get_handoff_by_id("nonexistent"))

    # ── 에이전트 등록/해제 ──

    def test_register_and_get_agent(self):
        """에이전트 등록 후 조회"""
        ctx = AgentContext(agent_name="translator", capabilities=["ko", "en"])
        self.service.register_agent(ctx)
        found = self.service.get_agent("translator")
        self.assertIsNotNone(found)
        self.assertEqual(found.capabilities, ["ko", "en"])

    def test_register_raises_on_empty_name(self):
        """빈 이름의 에이전트 등록 시 ValueError"""
        with self.assertRaises(ValueError):
            self.service.register_agent(AgentContext(agent_name=""))

    def test_unregister_agent(self):
        """에이전트 해제 후 조회 불가"""
        self.service.register_agent(AgentContext(agent_name="temp"))
        self.assertTrue(self.service.unregister_agent("temp"))
        self.assertIsNone(self.service.get_agent("temp"))

    def test_unregister_nonexistent_returns_false(self):
        """없는 에이전트 해제 시 False"""
        self.assertFalse(self.service.unregister_agent("ghost"))

    def test_list_agents(self):
        """등록된 에이전트 목록 조회"""
        self.service.register_agent(AgentContext(agent_name="a1"))
        self.service.register_agent(AgentContext(agent_name="a2"))
        agents = self.service.list_agents()
        names = {a.agent_name for a in agents}
        self.assertEqual(names, {"a1", "a2"})

    # ── 세션 관리 ──

    def test_get_session_ids(self):
        """세션 ID 목록 조회"""
        self.service.handoff("a", "b", self.valid_context, session_id="s1")
        self.service.handoff("a", "b", self.valid_context, session_id="s2")
        ids = self.service.get_session_ids()
        self.assertIn("s1", ids)
        self.assertIn("s2", ids)

    def test_clear_session(self):
        """세션 이력 삭제"""
        sid = "to_clear"
        self.service.handoff("a", "b", self.valid_context, session_id=sid)
        self.service.handoff("b", "c", self.valid_context, session_id=sid)
        count = self.service.clear_session(sid)
        self.assertEqual(count, 2)
        self.assertEqual(self.service.get_handoff_history(sid), [])

    def test_clear_nonexistent_session(self):
        """없는 세션 삭제 시 0 반환"""
        self.assertEqual(self.service.clear_session("ghost"), 0)


if __name__ == "__main__":
    unittest.main()
