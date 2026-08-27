"""에이전트 세션/메모리 사용자 격리 회귀 테스트."""
from __future__ import annotations

import json
import logging

import pytest

from agent.core import AIAgent, AgentLLMError, inherited_agent_context
from agent.memory import AgentMemoryStore, SessionAccessDenied
from agent.tools.agent_control_tools import (
    _handle_memory_read,
    _handle_memory_search,
    _handle_memory_write,
)


@pytest.fixture
def store(tmp_path):
    return AgentMemoryStore(db_path=str(tmp_path / "agent-isolation.db"))


def test_cross_user_session_is_hidden_and_not_replaced(store):
    owner_session = store.create_session(
        model="test/model",
        base_system_prompt="owner prompt",
        user_id="owner-user",
    )

    assert store.get_session(owner_session.session_id, user_id="other-user") is None
    with pytest.raises(SessionAccessDenied) as mismatch:
        AIAgent(
            model="test/model",
            session_id=owner_session.session_id,
            user_id="other-user",
            memory_store_instance=store,
        ).run("타인 세션 메시지")

    with pytest.raises(SessionAccessDenied) as missing:
        AIAgent(
            model="test/model",
            session_id="not-a-real-session",
            user_id="other-user",
            memory_store_instance=store,
        ).run("없는 세션 메시지")

    # 존재 여부를 예외 메시지로 추론할 수 없고 새 세션도 생성되지 않는다.
    assert str(mismatch.value) == str(missing.value)
    assert len(store.list_sessions()) == 1
    assert store.get_messages(owner_session.session_id, user_id="owner-user") == []


def test_cross_user_session_rejection_happens_before_cost_start(store):
    owner_session = store.create_session(
        model="test/model",
        base_system_prompt="owner prompt",
        user_id="owner-user",
    )
    cost_events = []

    with pytest.raises(SessionAccessDenied):
        AIAgent(
            model="test/model",
            session_id=owner_session.session_id,
            user_id="other-user",
            memory_store_instance=store,
            on_cost_start=lambda: cost_events.append("started"),
        ).run("타인 세션 메시지")

    assert cost_events == []


def test_message_store_rejects_cross_user_access(store):
    session = store.create_session(
        model="test/model", base_system_prompt="prompt", user_id="user-a",
    )
    store.add_message(session.session_id, "user", "owner", user_id="user-a")

    with pytest.raises(SessionAccessDenied):
        store.add_message(session.session_id, "user", "intruder", user_id="user-b")
    with pytest.raises(SessionAccessDenied):
        store.get_messages(session.session_id, user_id="user-b")

    messages = store.get_messages(session.session_id, user_id="user-a")
    assert [message["content"] for message in messages] == ["owner"]


def test_memory_tools_force_authenticated_user_namespace(store):
    # 전역 메모리는 관리자 컨텍스트가 없는 사용자 도구에서 보이면 안 된다.
    store.update_memory("global-secret", "shared-sensitive-value", "agent")

    write_a = json.loads(_handle_memory_write(
        {
            "key": "preference",
            "value": "alpha-private-marker",
            "category": "project",
            "user_id": "malicious-override",
        },
        user_id="user-a",
        memory_store=store,
    ))
    _handle_memory_write(
        {"key": "preference", "value": "beta-private-marker", "category": "agent"},
        user_id="user-b",
        memory_store=store,
    )

    assert write_a["category"] == "user"
    assert store.get_memory("preference", "user", user_id="user-a") == "alpha-private-marker"
    assert store.get_memory("preference", "user", user_id="user-b") == "beta-private-marker"

    read_a = json.loads(_handle_memory_read(
        {"key": "preference", "category": "agent"},
        user_id="user-a",
        memory_store=store,
    ))
    read_global = json.loads(_handle_memory_read(
        {"key": "global-secret", "category": "agent"},
        user_id="user-a",
        memory_store=store,
    ))
    search_a = json.loads(_handle_memory_search(
        {"query": "private-marker"},
        user_id="user-a",
        memory_store=store,
    ))

    assert read_a["value"] == "alpha-private-marker"
    assert read_global["found"] is False
    assert [item["value"] for item in search_a["results"]] == ["alpha-private-marker"]


def test_authenticated_session_snapshot_excludes_global_memory(store):
    store.update_memory("global-agent", "agent-sensitive", "agent")
    store.update_memory("global-project", "project-sensitive", "project")
    store.update_memory(
        "tone", "user-visible", "user", user_id="user-a",
    )

    session = store.create_session(
        model="test/model", base_system_prompt="base", user_id="user-a",
    )

    assert "user-visible" in session.system_prompt_snapshot
    assert "agent-sensitive" not in session.system_prompt_snapshot
    assert "project-sensitive" not in session.system_prompt_snapshot


def test_delegated_agent_inherits_user_and_memory_scope(store):
    with inherited_agent_context(
        user_id="parent-user", memory_store_instance=store,
    ):
        child = AIAgent(model="test/model")

    assert child.user_id == "parent-user"
    assert child._memory is store
    assert child._is_admin_context is False


def test_llm_exception_propagates_without_secret_in_result_or_log(store, caplog):
    raw_secret = "sk-super-secret-provider-token"
    agent = AIAgent(
        model="test/model", user_id="user-a", memory_store_instance=store,
    )

    def fail_llm(_messages, _tools):
        raise RuntimeError(f"provider failed Authorization: Bearer {raw_secret}")

    agent._call_llm = fail_llm
    with caplog.at_level(logging.ERROR, logger="agent.core"):
        with pytest.raises(AgentLLMError) as raised:
            agent.run("실패 전파")

    assert str(raised.value) == "AI 모델 호출에 실패했습니다."
    assert raw_secret not in str(raised.value)
    assert raw_secret not in caplog.text
