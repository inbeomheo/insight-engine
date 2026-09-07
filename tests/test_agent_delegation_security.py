"""에이전트 위임 깊이·도구 정책·예외 노출 회귀 테스트."""
from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.core import AIAgent, inherited_agent_context
from agent.delegate import (
    DELEGATE_BLOCKED_TOOLS,
    MAX_DELEGATION_DEPTH,
    DelegateManager,
    DelegateTask,
)
from agent.memory import AgentMemoryStore
from agent.registry import registry
from agent.tools.agent_control_tools import _handle_delegate_task
from agent.toolsets import resolve_toolset_names


@pytest.fixture
def store(tmp_path):
    return AgentMemoryStore(db_path=str(tmp_path / "agent-security.db"))


@pytest.mark.parametrize("composite_toolset", ["full", "role_writer"])
def test_delegated_child_cannot_recover_delegate_via_composite_toolset(
    composite_toolset,
    store,
):
    """합성 toolset의 간접 agent_control 포함도 스키마/실행에서 막는다."""
    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=[composite_toolset],
        depth=0,
    )
    with inherited_agent_context(
        user_id="parent-user",
        memory_store_instance=store,
    ):
        child = manager._create_child_agent(DelegateTask(
            task="재귀 위임을 시도해",
            toolsets=[composite_toolset],
        ))

    assert child._delegation_depth == 1
    assert DELEGATE_BLOCKED_TOOLS <= child._blocked_tools
    assert "agent_control" not in resolve_toolset_names(child._toolset_names)

    schema_names = {
        schema["function"]["name"] for schema in child._get_tool_schemas()
    }
    assert "delegate_task" not in schema_names
    assert "delegate_task" not in child._get_allowed_tool_names()

    # 모델이 숨겨진 도구 이름을 직접 만들어도 dispatch 경계에서 차단된다.
    tool_call = SimpleNamespace(
        id="recursive-call",
        function=SimpleNamespace(
            name="delegate_task",
            arguments=json.dumps({
                "task": "한 단계 더 위임",
                "toolsets": ["full"],
            }),
        ),
    )
    result = json.loads(child._execute_single_tool(tool_call)["content"])
    assert result["code"] == "TOOL_BLOCKED"


def test_delegation_depth_is_passed_to_child_and_max_depth_is_enforced(store):
    manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=["content"],
        depth=MAX_DELEGATION_DEPTH - 1,
    )
    with inherited_agent_context(
        user_id="parent-user",
        memory_store_instance=store,
    ):
        child = manager._create_child_agent(DelegateTask(task="깊이 확인"))

    assert child._delegation_depth == MAX_DELEGATION_DEPTH
    assert "delegate_task" in child._blocked_tools

    maxed_manager = DelegateManager(
        parent_model="test/model",
        parent_toolsets=["full"],
        depth=MAX_DELEGATION_DEPTH,
    )
    with patch.object(maxed_manager, "_create_child_agent") as create_child:
        result = maxed_manager.delegate(DelegateTask(task="초과 위임"))

    assert result.success is False
    assert "최대 위임 깊이 초과" in (result.error or "")
    create_child.assert_not_called()


def test_delegate_handler_rejects_direct_call_from_delegated_child():
    result = json.loads(_handle_delegate_task(
        {"task": "registry를 우회한 재위임", "toolsets": ["full"]},
        delegation_depth=1,
        parent_model="test/model",
        parent_toolsets=["full"],
    ))

    assert result["code"] == "TOOL_BLOCKED"


def test_tool_exception_detail_stays_in_internal_log_not_result_or_callback(
    store,
    caplog,
):
    raw_secret = "Bearer sk-secret-tool-exception-token"
    tool_name = "security_exception_probe"
    previews = []

    def explode(_args, **_kwargs):
        raise RuntimeError(
            f"upstream failed Authorization: {raw_secret} "
            "postgresql://admin:password@internal/db"
        )

    registry.register(
        name=tool_name,
        toolset="content",
        description="보안 예외 테스트",
        parameters={"type": "object", "properties": {}},
        handler=explode,
    )
    try:
        agent = AIAgent(
            model="test/model",
            toolsets=["content"],
            memory_store_instance=store,
            on_tool_end=lambda _name, preview, _elapsed: previews.append(preview),
        )
        tool_call = SimpleNamespace(
            id="exception-call",
            function=SimpleNamespace(name=tool_name, arguments="{}"),
        )

        with caplog.at_level(logging.ERROR, logger="agent.registry"):
            tool_result = agent._execute_single_tool(tool_call)["content"]
    finally:
        registry.unregister(tool_name)

    # 운영 로그와 LLM 도구 결과, SSE 콜백 모두에
    # 공급자 예외 원문을 싣지 않는다.
    assert raw_secret not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "도구 실행 실패" in caplog.text
    assert raw_secret not in tool_result
    assert raw_secret not in previews[0]
    assert json.loads(tool_result)["code"] == "TOOL_EXECUTION_FAILED"


@pytest.mark.parametrize("as_json_string", [False, True])
def test_tool_returned_error_payload_cannot_bypass_redaction(
    store,
    as_json_string,
):
    """예외를 잡아 정상 반환한 자동 래퍼도 비밀 문자열을 노출하지 않는다."""
    raw_secret = "Bearer sk-secret-returned-error postgresql://admin:pw@internal/db"
    tool_name = f"security_returned_error_{int(as_json_string)}"
    payload = {"error": raw_secret}

    registry.register(
        name=tool_name,
        toolset="content",
        description="오류 payload 우회 테스트",
        parameters={"type": "object", "properties": {}},
        handler=lambda _args, **_kwargs: (
            json.dumps(payload) if as_json_string else payload
        ),
    )
    try:
        agent = AIAgent(
            model="test/model",
            toolsets=["content"],
            memory_store_instance=store,
        )
        tool_call = SimpleNamespace(
            id="returned-error-call",
            function=SimpleNamespace(name=tool_name, arguments="{}"),
        )
        tool_result = agent._execute_single_tool(tool_call)["content"]
    finally:
        registry.unregister(tool_name)

    assert raw_secret not in tool_result
    assert json.loads(tool_result) == {
        "error": "도구 실행 중 문제가 발생했습니다.",
        "code": "TOOL_EXECUTION_FAILED",
    }
