"""
base_framework (FrameworkBaseAgent + AgentEvent) 단위 테스트
"""
import unittest
from unittest.mock import MagicMock
from typing import Any, Dict

from services.agents.base_framework import (
    BaseAgent, AgentEvent,
    EVENT_PLAN, EVENT_EXECUTE, EVENT_REFLECT, EVENT_DONE, EVENT_ERROR,
    MAX_ITERATIONS,
)


class ConcreteAgent(BaseAgent):
    """테스트용 구체 에이전트"""

    def __init__(self, plan_fn=None, execute_fn=None, reflect_fn=None, **kwargs):
        super().__init__(**kwargs)
        self._plan_fn = plan_fn or (lambda t, c: {"summary": "plan"})
        self._execute_fn = execute_fn or (lambda p: {"output": "result"})
        self._reflect_fn = reflect_fn or (lambda r: {"done": True, "feedback": ""})

    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._plan_fn(task, context)

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute_fn(plan)

    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return self._reflect_fn(result)


class TestAgentEvent(unittest.TestCase):
    """AgentEvent 테스트"""

    def test_to_dict(self):
        evt = AgentEvent(phase="plan", message="테스트", data={"k": "v"}, iteration=1, progress=0.5)
        d = evt.to_dict()
        self.assertEqual(d["phase"], "plan")
        self.assertEqual(d["message"], "테스트")
        self.assertEqual(d["data"]["k"], "v")
        self.assertEqual(d["iteration"], 1)
        self.assertAlmostEqual(d["progress"], 0.5)
        self.assertIn("timestamp", d)

    def test_defaults(self):
        evt = AgentEvent(phase="execute", message="msg")
        self.assertEqual(evt.data, {})
        self.assertEqual(evt.iteration, 0)
        self.assertAlmostEqual(evt.progress, 0.0)


class TestBaseAgent(unittest.TestCase):
    """base_framework.BaseAgent 테스트"""

    def test_init(self):
        agent = ConcreteAgent(name="test", model="gemini/test", max_iterations=3)
        self.assertEqual(agent.name, "test")
        self.assertEqual(agent.model, "gemini/test")
        self.assertEqual(agent.max_iterations, 3)

    def test_run_single_iteration_done(self):
        """reflect에서 done=True → 1회 반복 후 종료"""
        agent = ConcreteAgent(name="a", model="m")
        result = agent.run("task")
        self.assertEqual(result["output"], "result")

    def test_run_emits_events(self):
        """run() 실행 시 plan/execute/reflect/done 이벤트 발생"""
        events = []
        agent = ConcreteAgent(name="a", model="m")
        agent.on_event(lambda e: events.append(e.phase))
        agent.run("task")

        self.assertIn(EVENT_PLAN, events)
        self.assertIn(EVENT_EXECUTE, events)
        self.assertIn(EVENT_REFLECT, events)
        self.assertIn(EVENT_DONE, events)

    def test_run_max_iterations(self):
        """reflect에서 done=False → max_iterations까지 반복"""
        call_count = {"plan": 0}

        def plan_fn(t, c):
            call_count["plan"] += 1
            return {"summary": "plan"}

        agent = ConcreteAgent(
            name="a", model="m", max_iterations=3,
            plan_fn=plan_fn,
            reflect_fn=lambda r: {"done": False, "feedback": "더 해"},
        )
        result = agent.run("task")
        self.assertEqual(call_count["plan"], 3)

    def test_run_error_raises_if_no_result(self):
        """execute 오류 + 이전 결과 없음 → 예외 raise"""
        agent = ConcreteAgent(
            name="a", model="m",
            execute_fn=lambda p: (_ for _ in ()).throw(ValueError("fail")),
        )
        with self.assertRaises(ValueError):
            agent.run("task")

    def test_run_error_returns_previous_result(self):
        """두 번째 반복에서 오류 시 첫 번째 결과 반환"""
        call_count = {"n": 0}

        def execute_fn(p):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("boom")
            return {"output": "first"}

        agent = ConcreteAgent(
            name="a", model="m", max_iterations=3,
            execute_fn=execute_fn,
            reflect_fn=lambda r: {"done": False, "feedback": "more"},
        )
        result = agent.run("task")
        self.assertEqual(result["output"], "first")

    def test_event_listener_error_ignored(self):
        """이벤트 리스너 예외가 루프를 중단시키지 않음"""
        agent = ConcreteAgent(name="a", model="m")
        agent.on_event(lambda e: (_ for _ in ()).throw(RuntimeError("listener fail")))
        # 리스너 오류에도 정상 실행
        result = agent.run("task")
        self.assertEqual(result["output"], "result")


class TestConstants(unittest.TestCase):
    def test_max_iterations_default(self):
        self.assertEqual(MAX_ITERATIONS, 5)

    def test_event_constants(self):
        self.assertEqual(EVENT_PLAN, "plan")
        self.assertEqual(EVENT_EXECUTE, "execute")
        self.assertEqual(EVENT_REFLECT, "reflect")
        self.assertEqual(EVENT_DONE, "done")
        self.assertEqual(EVENT_ERROR, "error")


if __name__ == '__main__':
    unittest.main()
