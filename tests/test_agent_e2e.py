"""
AIAgent E2E 테스트

ChatMock 또는 실제 LLM으로 에이전트 전체 루프를 검증합니다.
- 도구 디스커버리 → 에이전트 생성 → run() → 도구 호출 → 결과 반환
"""
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestToolRegistry(unittest.TestCase):
    """Tool Registry 단위 테스트."""

    def setUp(self):
        from agent.registry import ToolRegistry
        self.registry = ToolRegistry()
        self.registry.reset()

    def tearDown(self):
        self.registry.reset()

    def test_register_and_dispatch(self):
        """도구 등록 및 디스패치."""
        self.registry.register(
            name="test_upper",
            toolset="test",
            description="대문자 변환",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            handler=lambda args, **kw: json.dumps({"result": args["text"].upper()}),
        )

        self.assertEqual(self.registry.tool_count, 1)
        result = self.registry.dispatch("test_upper", {"text": "hello"})
        data = json.loads(result)
        self.assertEqual(data["result"], "HELLO")

    def test_unregistered_tool_raises(self):
        """미등록 도구 디스패치 시 KeyError."""
        with self.assertRaises(KeyError):
            self.registry.dispatch("nonexistent", {})

    def test_unavailable_tool_returns_error(self):
        """비가용 도구 디스패치 시 에러 JSON 반환."""
        self.registry.register(
            name="gated_tool",
            toolset="test",
            description="API 키 필요",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, **kw: "OK",
            check_fn=lambda: False,
            requires_env=["MISSING_KEY"],
        )

        result = self.registry.dispatch("gated_tool", {})
        data = json.loads(result)
        self.assertIn("error", data)

    def test_get_schemas(self):
        """스키마 반환 형식 검증."""
        self.registry.register(
            name="schema_test",
            toolset="test",
            description="테스트",
            parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
            handler=lambda args, **kw: "ok",
        )

        schemas = self.registry.get_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["type"], "function")
        self.assertEqual(schemas[0]["function"]["name"], "schema_test")

    def test_toolset_filtering(self):
        """Toolset 필터링."""
        for name, ts in [("a", "alpha"), ("b", "alpha"), ("c", "beta")]:
            self.registry.register(
                name=name, toolset=ts, description=name,
                parameters={"type": "object", "properties": {}},
                handler=lambda args, **kw: name,
            )

        alpha = self.registry.list_tools(toolsets=["alpha"])
        self.assertEqual(len(alpha), 2)

        beta = self.registry.list_tools(toolsets=["beta"])
        self.assertEqual(len(beta), 1)

    def test_handler_error_returns_json(self):
        """핸들러 예외 시 에러 JSON 반환."""
        self.registry.register(
            name="exploder",
            toolset="test",
            description="폭발",
            parameters={"type": "object", "properties": {}},
            handler=lambda args, **kw: (_ for _ in ()).throw(ValueError("boom")),
        )

        result = self.registry.dispatch("exploder", {})
        data = json.loads(result)
        self.assertIn("error", data)


class TestToolsets(unittest.TestCase):
    """Toolset 해석 테스트."""

    def test_resolve_leaf_toolset(self):
        from agent.toolsets import resolve_toolset
        tools = resolve_toolset("collector")
        self.assertIn("collect_youtube", tools)

    def test_resolve_composite_toolset(self):
        from agent.toolsets import resolve_toolset_names
        names = resolve_toolset_names(["role_writer"])
        self.assertIn("collector", names)
        self.assertIn("core", names)
        self.assertIn("agent_control", names)

    def test_full_includes_all(self):
        from agent.toolsets import resolve_toolset_names
        names = resolve_toolset_names(["full"])
        self.assertIn("analysis", names)
        self.assertIn("seo", names)
        self.assertIn("content", names)

    def test_circular_reference_safe(self):
        """순환 참조 방지."""
        from agent.toolsets import resolve_toolset
        # full이 자기 자신을 포함하지 않으므로 무한루프 없음
        tools = resolve_toolset("full")
        self.assertIsInstance(tools, list)


class TestMemoryStore(unittest.TestCase):
    """메모리 저장소 테스트."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        from agent.memory import AgentMemoryStore
        self.store = AgentMemoryStore(db_path=self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_memory_crud(self):
        """메모리 CRUD."""
        self.store.update_memory("key1", "value1", "agent")
        val = self.store.get_memory("key1", "agent")
        self.assertEqual(val, "value1")

        self.store.update_memory("key1", "updated", "agent")
        val = self.store.get_memory("key1", "agent")
        self.assertEqual(val, "updated")

        self.assertTrue(self.store.delete_memory("key1", "agent"))
        self.assertIsNone(self.store.get_memory("key1", "agent"))

    def test_session_frozen_snapshot(self):
        """세션 생성 시 메모리 동결 스냅샷."""
        self.store.update_memory("env_fact", "Python 3.11", "agent")

        session = self.store.create_session(
            model="test/model",
            base_system_prompt="Base prompt",
        )

        # 스냅샷에 메모리가 주입되어 있어야 함
        self.assertIn("Agent Memory", session.system_prompt_snapshot)
        self.assertIn("Python 3.11", session.system_prompt_snapshot)

        # 세션 생성 후 메모리를 변경해도 스냅샷은 불변
        self.store.update_memory("env_fact", "Python 3.12", "agent")
        reloaded = self.store.get_session(session.session_id)
        self.assertIn("Python 3.11", reloaded.system_prompt_snapshot)

    def test_message_history(self):
        """메시지 히스토리."""
        session = self.store.create_session(model="test", base_system_prompt="sys")
        self.store.add_message(session.session_id, "user", "hello")
        self.store.add_message(session.session_id, "assistant", "hi there")

        msgs = self.store.get_messages(session.session_id)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["content"], "hi there")


class TestToolDiscovery(unittest.TestCase):
    """도구 디스커버리 통합 테스트."""

    @classmethod
    def setUpClass(cls):
        """도구 디스커버리는 한 번만."""
        from agent.registry import registry
        if registry.tool_count == 0:
            from agent.tools import discover_tools
            discover_tools()

    def test_discover_registers_tools(self):
        """discover_tools()가 도구를 등록하는지."""
        from agent.registry import registry
        self.assertGreater(registry.tool_count, 50)

    def test_analysis_tools_registered(self):
        """analysis 도구가 대량 등록되는지."""
        from agent.registry import registry
        analysis = registry.list_tools(toolsets=["analysis"])
        self.assertGreater(len(analysis), 50)

    def test_role_writer_has_tools(self):
        """role_writer Toolset이 실제 도구를 갖는지."""
        from agent.registry import registry
        from agent.toolsets import resolve_toolset_names

        leaf_names = resolve_toolset_names(["role_writer"])
        schemas = registry.get_schemas(toolsets=leaf_names)
        self.assertGreater(len(schemas), 10)


class TestAIAgentMocked(unittest.TestCase):
    """AIAgent 모킹 테스트 (LLM 호출 없이)."""

    @classmethod
    def setUpClass(cls):
        from agent.registry import registry
        if registry.tool_count == 0:
            from agent.tools import discover_tools
            discover_tools()

    def test_agent_creation(self):
        """에이전트 생성."""
        from agent import AIAgent
        agent = AIAgent(
            model="chatmock/gpt-5.3-codex-spark",
            toolsets=["role_writer"],
            system_prompt="테스트 에이전트",
            max_iterations=5,
        )
        self.assertEqual(agent.model, "cliproxy/gpt-5.3-codex-spark")
        self.assertEqual(agent._budget.max_iterations, 5)

    @patch("litellm.completion")
    def test_agent_run_no_tools(self, mock_completion):
        """도구 호출 없이 바로 응답하는 케이스."""
        # Mock: assistant가 도구 없이 텍스트만 반환
        mock_msg = MagicMock()
        mock_msg.content = "안녕하세요! 도움이 필요하시면 말씀해주세요."
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_completion.return_value = mock_response

        from agent import AIAgent
        agent = AIAgent(model="chatmock/test", max_iterations=5)
        result = agent.run("안녕")

        self.assertIn("안녕하세요", result.content)
        self.assertEqual(result.tool_calls_count, 0)
        self.assertEqual(result.iterations_used, 1)

    @patch("litellm.completion")
    def test_agent_run_with_tool_call(self, mock_completion):
        """도구를 호출하고 결과를 사용하는 케이스."""
        from types import SimpleNamespace

        # 1차 호출: 도구 호출
        tool_call = SimpleNamespace(
            id="call_1",
            type="function",
            function=SimpleNamespace(
                name="detect_source_type",
                arguments='{"url": "https://youtube.com/watch?v=test"}',
            ),
        )
        msg1 = SimpleNamespace(content=None, tool_calls=[tool_call])
        resp1 = SimpleNamespace(
            choices=[SimpleNamespace(message=msg1)],
            usage=SimpleNamespace(prompt_tokens=200, completion_tokens=30),
        )

        # 2차 호출: 최종 응답
        msg2 = SimpleNamespace(
            content="이 URL은 YouTube 영상입니다.",
            tool_calls=None,
        )
        resp2 = SimpleNamespace(
            choices=[SimpleNamespace(message=msg2)],
            usage=SimpleNamespace(prompt_tokens=300, completion_tokens=50),
        )

        mock_completion.side_effect = [resp1, resp2]

        from agent import AIAgent
        agent = AIAgent(model="chatmock/test", max_iterations=5)
        result = agent.run("이 URL이 뭔지 확인해줘: https://youtube.com/watch?v=test")

        self.assertIn("YouTube", result.content)
        self.assertEqual(result.tool_calls_count, 1)
        self.assertEqual(result.iterations_used, 2)


class TestRolePrompts(unittest.TestCase):
    """역할별 프롬프트 테스트."""

    def test_all_roles_have_prompts(self):
        from agent.prompts.roles import ROLE_PROMPTS, ROLE_TOOLSETS
        for role in ["supervisor", "writer", "editor", "seo", "publisher"]:
            self.assertIn(role, ROLE_PROMPTS)
            self.assertIn(role, ROLE_TOOLSETS)
            self.assertGreater(len(ROLE_PROMPTS[role]), 100)

    def test_get_role_prompt(self):
        from agent.prompts.roles import get_role_prompt
        prompt = get_role_prompt("writer")
        self.assertIn("Content Writer", prompt)
        self.assertIsNone(get_role_prompt("nonexistent"))


class TestCompressor(unittest.TestCase):
    """컨텍스트 압축 테스트."""

    def test_prune_old_tool_results(self):
        from agent.compressor import _prune_tool_results
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "tool", "content": "x" * 500},
            {"role": "tool", "content": "y" * 500},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "next"},
            {"role": "assistant", "content": "done"},
        ]
        pruned = _prune_tool_results(messages, max_len=200, protect_recent=3)
        # 오래된 tool 결과는 축약
        self.assertLess(len(pruned[1]["content"]), 300)
        # 최근 3개는 보호
        self.assertEqual(pruned[-1]["content"], "done")

    def test_split_head_middle_tail(self):
        from agent.compressor import _split_head_middle_tail
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ] + [
            {"role": "user", "content": f"q{i}"}
            for i in range(2, 20)
        ]
        head, middle, tail = _split_head_middle_tail(messages, tail_count=5)
        self.assertGreater(len(head), 0)
        self.assertGreater(len(middle), 0)
        self.assertEqual(len(tail), 5)


if __name__ == "__main__":
    unittest.main()
