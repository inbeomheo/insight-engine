"""agent/core — 데이터 클래스 + 상수 단위 테스트

650줄 AIAgent 코어 중 LLM 호출 없이 테스트 가능한 부분:
- IterationBudget: 스레드 세이프 예산 관리
- AgentResponse 데이터 클래스
- PARALLEL_SAFE_TOOLS / NEVER_PARALLEL 상수 invariant
- MAX_PARALLEL_WORKERS 합리적 값
"""
import threading
import time
import unittest

from agent.core import (
    IterationBudget,
    AgentResponse,
    PARALLEL_SAFE_TOOLS,
    NEVER_PARALLEL,
    MAX_PARALLEL_WORKERS,
)


class TestIterationBudget(unittest.TestCase):

    def test_initial_state(self):
        b = IterationBudget(max_iterations=10)
        self.assertEqual(b.remaining, 10)

    def test_consume_reduces_remaining(self):
        b = IterationBudget(max_iterations=10)
        self.assertTrue(b.consume(3))
        self.assertEqual(b.remaining, 7)

    def test_consume_over_budget_fails(self):
        b = IterationBudget(max_iterations=10)
        self.assertTrue(b.consume(8))
        self.assertFalse(b.consume(5))  # 8+5 > 10
        # 실패 시 _used는 변경 안 됨
        self.assertEqual(b.remaining, 2)

    def test_consume_exact_remaining(self):
        b = IterationBudget(max_iterations=10)
        b.consume(7)
        self.assertTrue(b.consume(3))  # exactly fills
        self.assertEqual(b.remaining, 0)

    def test_refund(self):
        b = IterationBudget(max_iterations=10)
        b.consume(5)
        b.refund(2)
        self.assertEqual(b.remaining, 7)

    def test_refund_below_zero_clamps(self):
        """refund > _used 면 0으로 클램프"""
        b = IterationBudget(max_iterations=10)
        b.consume(2)
        b.refund(5)
        self.assertEqual(b.remaining, 10)

    def test_thread_safety(self):
        """100개 스레드가 동시에 consume → 정확한 합계"""
        b = IterationBudget(max_iterations=100)

        def consume_one():
            b.consume(1)

        threads = [threading.Thread(target=consume_one) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(b.remaining, 0)

    def test_consume_zero(self):
        b = IterationBudget(max_iterations=10)
        self.assertTrue(b.consume(0))
        self.assertEqual(b.remaining, 10)


class TestAgentResponse(unittest.TestCase):

    def test_required_fields(self):
        resp = AgentResponse(
            content='응답',
            messages=[{'role': 'user', 'content': 'q'}],
            tool_calls_count=2,
            iterations_used=3,
            elapsed_seconds=1.5,
        )
        self.assertEqual(resp.content, '응답')
        self.assertEqual(resp.tool_calls_count, 2)
        self.assertEqual(resp.iterations_used, 3)
        self.assertEqual(resp.elapsed_seconds, 1.5)

    def test_default_metadata(self):
        resp = AgentResponse(
            content='', messages=[], tool_calls_count=0,
            iterations_used=0, elapsed_seconds=0,
        )
        self.assertEqual(resp.metadata, {})
        self.assertIsNone(resp.session_id)

    def test_custom_metadata(self):
        resp = AgentResponse(
            content='', messages=[], tool_calls_count=0,
            iterations_used=0, elapsed_seconds=0,
            session_id='s-123',
            metadata={'cost': 0.05, 'tokens': 1000},
        )
        self.assertEqual(resp.session_id, 's-123')
        self.assertEqual(resp.metadata['cost'], 0.05)


class TestParallelToolConstants(unittest.TestCase):

    def test_parallel_safe_is_frozenset(self):
        self.assertIsInstance(PARALLEL_SAFE_TOOLS, frozenset)

    def test_never_parallel_is_frozenset(self):
        self.assertIsInstance(NEVER_PARALLEL, frozenset)

    def test_safe_and_never_disjoint(self):
        """병렬 안전과 절대 금지는 교집합 없어야 함"""
        self.assertEqual(PARALLEL_SAFE_TOOLS & NEVER_PARALLEL, frozenset())

    def test_never_parallel_includes_state_changes(self):
        """상태 변경 도구는 NEVER_PARALLEL에 포함"""
        for tool in ('memory_write', 'create_schedule', 'mcp_publish_naver'):
            with self.subTest(tool=tool):
                self.assertIn(tool, NEVER_PARALLEL)

    def test_never_parallel_includes_user_interaction(self):
        """사용자 상호작용은 NEVER_PARALLEL"""
        self.assertIn('clarify', NEVER_PARALLEL)

    def test_never_parallel_includes_delegate(self):
        """위임은 NEVER_PARALLEL"""
        self.assertIn('delegate_task', NEVER_PARALLEL)

    def test_parallel_safe_includes_read_only(self):
        """읽기 전용 도구는 PARALLEL_SAFE"""
        for tool in ('analyze_readability', 'web_search', 'rag_query'):
            with self.subTest(tool=tool):
                self.assertIn(tool, PARALLEL_SAFE_TOOLS)


class TestMaxParallelWorkers(unittest.TestCase):

    def test_reasonable_value(self):
        """MAX_PARALLEL_WORKERS는 1~16 범위 (실용적 ThreadPoolExecutor 한계)"""
        self.assertGreaterEqual(MAX_PARALLEL_WORKERS, 1)
        self.assertLessEqual(MAX_PARALLEL_WORKERS, 16)


if __name__ == '__main__':
    unittest.main()
