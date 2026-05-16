"""agent/delegate — 서브에이전트 위임 매니저 단위 테스트

자식 에이전트(AIAgent)는 모의로 처리. 핵심 로직:
- 깊이 제한 (MAX_DEPTH)
- 병렬 처리 제한 (MAX_CONCURRENT_CHILDREN)
- 인터럽트 전파
- 차단 도구 frozenset
- 결과 순서 보장
"""
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

from agent.delegate import (
    DelegateManager,
    DelegateTask,
    DelegateResult,
    DELEGATE_BLOCKED_TOOLS,
    MAX_CONCURRENT_CHILDREN,
    MAX_DEPTH,
)


class TestDelegateBlockedTools(unittest.TestCase):

    def test_blocked_tools_immutable(self):
        self.assertIsInstance(DELEGATE_BLOCKED_TOOLS, frozenset)

    def test_essential_blocks(self):
        """안전 핵심: 재귀 위임/사용자 상호작용/발행 차단"""
        for tool in ('delegate_task', 'clarify', 'mcp_publish_naver', 'mcp_publish_wordpress'):
            self.assertIn(tool, DELEGATE_BLOCKED_TOOLS)


class TestDelegateTaskDataclass(unittest.TestCase):

    def test_default_values(self):
        t = DelegateTask(task='분석해줘')
        self.assertEqual(t.task, '분석해줘')
        self.assertIsNone(t.toolsets)
        self.assertEqual(t.max_iterations, 20)
        self.assertIsNone(t.context)
        self.assertIsNone(t.model)


class _FakeChild:
    """AIAgent 모의 — interrupt 가능, run 결과 제어"""

    def __init__(self, content='결과', tool_calls_count=2, elapsed=0.5,
                 raise_exc=None, sleep_seconds=0):
        self._content = content
        self._tool_calls_count = tool_calls_count
        self._elapsed = elapsed
        self._raise_exc = raise_exc
        self._sleep = sleep_seconds
        self.interrupted = False

    def run(self, user_message, context=None):
        if self._sleep:
            time.sleep(self._sleep)
        if self._raise_exc:
            raise self._raise_exc
        resp = MagicMock()
        resp.content = self._content
        resp.tool_calls_count = self._tool_calls_count
        resp.elapsed_seconds = self._elapsed
        return resp

    def interrupt(self):
        self.interrupted = True


class TestDelegateDepthLimit(unittest.TestCase):

    def test_depth_at_max_returns_error(self):
        manager = DelegateManager(
            parent_model='m', parent_toolsets=['x'], depth=MAX_DEPTH,
        )
        result = manager.delegate(DelegateTask(task='작업'))
        self.assertFalse(result.success)
        self.assertIn('깊이 초과', result.error)
        self.assertEqual(result.content, '')

    def test_depth_zero_creates_child(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        fake_child = _FakeChild(content='자식 결과')
        with patch.object(manager, '_create_child_agent', return_value=fake_child):
            result = manager.delegate(DelegateTask(task='작업'))
        self.assertTrue(result.success)
        self.assertEqual(result.content, '자식 결과')


class TestDelegateChildExceptionHandling(unittest.TestCase):

    def test_child_raise_returns_failure(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        bad_child = _FakeChild(raise_exc=RuntimeError('자식 폭발'))
        with patch.object(manager, '_create_child_agent', return_value=bad_child):
            result = manager.delegate(DelegateTask(task='작업'))
        self.assertFalse(result.success)
        self.assertIn('자식 폭발', result.error)


class TestDelegateActiveChildrenTracking(unittest.TestCase):

    def test_child_removed_after_completion(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        with patch.object(manager, '_create_child_agent', return_value=_FakeChild()):
            manager.delegate(DelegateTask(task='작업'))
        # 완료 후 활성 자식 리스트 비어있음
        self.assertEqual(len(manager._active_children), 0)

    def test_child_removed_after_exception(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        bad = _FakeChild(raise_exc=RuntimeError('fail'))
        with patch.object(manager, '_create_child_agent', return_value=bad):
            manager.delegate(DelegateTask(task='작업'))
        self.assertEqual(len(manager._active_children), 0)


class TestDelegateParallel(unittest.TestCase):

    def test_parallel_returns_results_in_input_order(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        tasks = [
            DelegateTask(task=f'작업 {i}', context={'i': i})
            for i in range(3)
        ]

        # 각 자식이 자기 task를 인식해서 반환
        def create_child(t):
            return _FakeChild(content=f'결과: {t.task}')

        with patch.object(manager, '_create_child_agent', side_effect=create_child):
            results = manager.delegate_parallel(tasks)

        self.assertEqual(len(results), 3)
        for i, r in enumerate(results):
            self.assertEqual(r.task, f'작업 {i}')
            self.assertTrue(r.success)

    def test_parallel_truncates_over_limit(self):
        """MAX_CONCURRENT_CHILDREN 초과 시 truncate"""
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        tasks = [DelegateTask(task=f't{i}') for i in range(MAX_CONCURRENT_CHILDREN + 2)]
        with patch.object(manager, '_create_child_agent', return_value=_FakeChild()):
            results = manager.delegate_parallel(tasks)
        # 초과분은 잘려나감
        self.assertEqual(len(results), MAX_CONCURRENT_CHILDREN)

    def test_parallel_mixed_success_failure(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        children_iter = iter([
            _FakeChild(content='ok1'),
            _FakeChild(raise_exc=RuntimeError('boom')),
            _FakeChild(content='ok3'),
        ])

        def next_child(*args, **kw):
            return next(children_iter)

        with patch.object(manager, '_create_child_agent', side_effect=next_child):
            results = manager.delegate_parallel([
                DelegateTask(task='t1'),
                DelegateTask(task='t2'),
                DelegateTask(task='t3'),
            ])
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)
        self.assertTrue(results[2].success)


class TestInterruptAll(unittest.TestCase):

    def test_interrupt_sets_parent_event(self):
        parent_event = threading.Event()
        manager = DelegateManager(
            parent_model='m', parent_toolsets=['x'], depth=0,
            parent_interrupt=parent_event,
        )
        manager.interrupt_all()
        self.assertTrue(parent_event.is_set())

    def test_interrupt_propagates_to_active_children(self):
        manager = DelegateManager(parent_model='m', parent_toolsets=['x'], depth=0)
        child1 = _FakeChild()
        child2 = _FakeChild()
        manager._active_children = [child1, child2]
        manager.interrupt_all()
        self.assertTrue(child1.interrupted)
        self.assertTrue(child2.interrupted)


if __name__ == '__main__':
    unittest.main()
