"""에이전트 압축·위임 경로의 비용 잠금 경계 회귀 테스트."""
from __future__ import annotations

import json
import logging
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.compressor import _summarize_middle, compress_messages
from agent.core import AIAgent, inherited_agent_context
from agent.delegate import DelegateManager, DelegateResult, DelegateTask
from agent.memory import AgentMemoryStore
from agent.registry import ToolRegistry, registry
from agent.tools.agent_control_tools import _handle_delegate_task
from services.usage.usage_lock import UsageLockUnavailable


@pytest.fixture
def memory_store(tmp_path):
    return AgentMemoryStore(db_path=str(tmp_path / "agent-cost-boundary.db"))


def _completion_response(content: str = "완료"):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content, tool_calls=None),
        )],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
    )


def test_compressor_marks_cost_immediately_before_litellm_call():
    events = []

    def provider(**_kwargs):
        events.append("provider")
        return _completion_response("요약")

    with patch("litellm.completion", side_effect=provider):
        result = _summarize_middle(
            [{"role": "user", "content": "오래된 대화"}],
            on_cost_start=lambda: events.append("cost"),
        )

    assert result == "요약"
    assert events == ["cost", "provider"]


def test_compressor_lock_loss_prevents_provider_and_skips_fallback():
    provider = MagicMock(return_value=_completion_response("호출되면 안 됨"))

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    with patch("litellm.completion", provider), pytest.raises(
        UsageLockUnavailable,
    ):
        _summarize_middle(
            [{"role": "user", "content": "오래된 대화"}],
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_compressor_keeps_generic_provider_failure_fallback(caplog):
    callback = MagicMock()
    raw_secret = "Bearer sk-compressor-secret https://internal.example"

    with caplog.at_level(
        logging.ERROR,
        logger="agent.compressor",
    ), patch(
        "litellm.completion",
        side_effect=RuntimeError(raw_secret),
    ):
        result = _summarize_middle(
            [{"role": "user", "content": "폴백에 남겨야 할 요청"}],
            on_cost_start=callback,
        )

    callback.assert_called_once_with()
    assert "폴백에 남겨야 할 요청" in result
    assert raw_secret not in caplog.text
    assert "RuntimeError" in caplog.text


def test_compressor_does_not_mark_cost_when_pruning_is_sufficient():
    callback = MagicMock()
    messages = [{"role": "system", "content": "짧은 대화"}]

    assert compress_messages(
        messages,
        target_tokens=10_000,
        on_cost_start=callback,
    ) == messages
    callback.assert_not_called()


def test_agent_passes_cost_callback_into_compressor(memory_store):
    callback = MagicMock()
    messages = [{"role": "user", "content": "압축 대상"}]
    agent = AIAgent(
        model="test/model",
        toolsets=[],
        memory_store_instance=memory_store,
        compression_threshold=0,
        on_cost_start=callback,
    )

    with patch(
        "agent.compressor.compress_messages",
        return_value=messages,
    ) as compressor:
        assert agent._maybe_compress(
            messages,
            SimpleNamespace(prompt_tokens=1),
        ) == messages

    assert compressor.call_args.kwargs["on_cost_start"] is callback


def test_agent_run_rethrows_lock_loss_before_provider(memory_store):
    provider = MagicMock(return_value=_completion_response())

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    agent = AIAgent(
        model="test/model",
        toolsets=[],
        memory_store_instance=memory_store,
        on_cost_start=reject_cost,
    )

    with patch("litellm.completion", provider), pytest.raises(
        UsageLockUnavailable,
    ):
        agent.run("호출하지 마")

    provider.assert_not_called()


def test_execute_tool_forwards_parent_cost_callback(memory_store):
    callback = MagicMock()
    agent = AIAgent(
        model="test/model",
        toolsets=[],
        memory_store_instance=memory_store,
        on_cost_start=callback,
    )
    tool_call = SimpleNamespace(
        id="cost-forward",
        function=SimpleNamespace(name="probe", arguments="{}"),
    )

    with patch.object(registry, "dispatch", return_value="{}") as dispatch:
        agent._execute_single_tool(tool_call)

    assert dispatch.call_args.kwargs["on_cost_start"] is callback


def test_delegate_handler_passes_callback_to_manager():
    callback = MagicMock()
    delegated = DelegateResult(
        task="하위 작업",
        content="완료",
        success=True,
        tool_calls_count=0,
        elapsed_seconds=0.1,
    )

    with patch("agent.delegate.DelegateManager") as manager_class:
        manager_class.return_value.delegate.return_value = delegated
        payload = json.loads(_handle_delegate_task(
            {"task": "하위 작업", "toolsets": []},
            parent_model="test/model",
            parent_toolsets=[],
            on_cost_start=callback,
        ))

    assert payload["success"] is True
    assert (
        manager_class.call_args.kwargs["parent_on_cost_start"]
        is callback
    )


def test_delegated_child_checks_parent_callback_before_every_provider_call():
    events = []
    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=[],
        parent_on_cost_start=lambda: events.append("cost"),
    )
    child = manager._create_child_agent(DelegateTask(
        task="외부 호출 두 번",
        toolsets=[],
    ))

    def provider(**_kwargs):
        events.append("provider")
        return _completion_response()

    with patch("litellm.completion", side_effect=provider):
        child._call_llm([], [])
        child._call_llm([], [])

    assert events == ["cost", "provider", "cost", "provider"]


def test_delegated_child_lock_loss_propagates_end_to_end(
    memory_store,
):
    provider = MagicMock(return_value=_completion_response())

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=[],
        parent_on_cost_start=reject_cost,
    )

    with inherited_agent_context(
        user_id="cost-owner",
        memory_store_instance=memory_store,
    ), patch("litellm.completion", provider), pytest.raises(
        UsageLockUnavailable,
    ):
        manager.delegate(DelegateTask(task="호출하지 마", toolsets=[]))

    provider.assert_not_called()
    assert manager._active_children == []


def test_delegate_generic_failure_keeps_safe_result_and_log(caplog):
    raw_secret = "Bearer sk-delegate-secret https://internal.example"
    child = MagicMock()
    child.run.side_effect = RuntimeError(raw_secret)
    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=[],
    )

    with patch.object(
        manager,
        "_create_child_agent",
        return_value=child,
    ), caplog.at_level(logging.ERROR, logger="agent.delegate"):
        result = manager.delegate(DelegateTask(task="일반 실패"))

    assert result.success is False
    assert raw_secret not in (result.error or "")
    assert raw_secret not in caplog.text
    assert "RuntimeError" in caplog.text


def test_registry_rethrows_lock_loss_but_keeps_generic_error_json():
    tool_registry = ToolRegistry()
    tool_registry.register(
        name="lock_loss",
        toolset="test",
        description="잠금 예외",
        parameters={"type": "object", "properties": {}},
        handler=lambda _args, **_kwargs: (_ for _ in ()).throw(
            UsageLockUnavailable("임대 소유권 상실"),
        ),
    )
    tool_registry.register(
        name="generic_failure",
        toolset="test",
        description="일반 예외",
        parameters={"type": "object", "properties": {}},
        handler=lambda _args, **_kwargs: (_ for _ in ()).throw(
            ValueError("일반 실패"),
        ),
    )

    with pytest.raises(UsageLockUnavailable):
        tool_registry.dispatch("lock_loss", {})

    generic_payload = json.loads(tool_registry.dispatch("generic_failure", {}))
    assert generic_payload["code"] == "TOOL_EXECUTION_FAILED"


def _executor_with_futures(*futures):
    executor = MagicMock()
    executor.submit.side_effect = futures
    context = MagicMock()
    context.__enter__.return_value = executor
    context.__exit__.return_value = False
    return context


def test_core_parallel_rethrows_lock_loss_and_cancels_pending(memory_store):
    failed = Future()
    failed.set_exception(UsageLockUnavailable("임대 소유권 상실"))
    pending = Future()
    agent = AIAgent(
        model="test/model",
        toolsets=[],
        memory_store_instance=memory_store,
    )
    tool_calls = [
        SimpleNamespace(id="failed"),
        SimpleNamespace(id="pending"),
    ]

    with patch(
        "agent.core.ThreadPoolExecutor",
        return_value=_executor_with_futures(failed, pending),
    ), patch("agent.core.as_completed", return_value=[failed]), pytest.raises(
        UsageLockUnavailable,
    ):
        agent._process_parallel(tool_calls)

    assert pending.cancelled()


def test_core_parallel_generic_failure_keeps_safe_result_and_log(
    memory_store,
    caplog,
):
    raw_secret = "Bearer sk-parallel-secret https://internal.example"
    failed = Future()
    failed.set_exception(RuntimeError(raw_secret))
    agent = AIAgent(
        model="test/model",
        toolsets=[],
        memory_store_instance=memory_store,
    )
    tool_calls = [SimpleNamespace(id="failed")]

    with patch(
        "agent.core.ThreadPoolExecutor",
        return_value=_executor_with_futures(failed),
    ), patch(
        "agent.core.as_completed",
        return_value=[failed],
    ), caplog.at_level(logging.ERROR, logger="agent.core"):
        results = agent._process_parallel(tool_calls)

    assert raw_secret not in results[0]["content"]
    assert json.loads(results[0]["content"])["code"] == (
        "TOOL_EXECUTION_FAILED"
    )
    assert raw_secret not in caplog.text
    assert "RuntimeError" in caplog.text


def test_delegate_parallel_rethrows_lock_loss_and_cancels_pending():
    failed = Future()
    failed.set_exception(UsageLockUnavailable("임대 소유권 상실"))
    pending = Future()
    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=[],
    )
    tasks = [DelegateTask(task="실패"), DelegateTask(task="대기")]

    with patch(
        "agent.delegate.ThreadPoolExecutor",
        return_value=_executor_with_futures(failed, pending),
    ), patch(
        "agent.delegate.as_completed",
        return_value=[failed],
    ), patch.object(manager, "interrupt_all") as interrupt_all, pytest.raises(
        UsageLockUnavailable,
    ):
        manager.delegate_parallel(tasks)

    assert pending.cancelled()
    interrupt_all.assert_called_once_with()
