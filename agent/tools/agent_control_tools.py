"""
에이전트 제어 도구 — delegate, memory, clarify

agent_control toolset에 속하는 도구들.
AIAgent가 자기 자신을 제어하는 메타 도구.
"""
from __future__ import annotations

import json
import logging

from agent.registry import TOOL_BLOCKED_MESSAGE, registry

logger = logging.getLogger(__name__)


def _memory_context(kwargs: dict):
    """코어가 전달한 저장소와 인증 범위를 보존한다."""
    from agent.memory import memory_store

    return (
        kwargs.get("memory_store") or memory_store,
        kwargs.get("user_id"),
        bool(kwargs.get("is_admin_context", False)),
    )


# ── delegate_task ──

def _handle_delegate_task(args: dict, **kwargs) -> str:
    """서브에이전트에 작업을 위임합니다."""
    from agent.delegate import DelegateManager, DelegateTask

    task_text = args.get("task", "")
    toolsets = args.get("toolsets")
    max_iterations = args.get("max_iterations", 20)
    context = args.get("context")

    if not task_text:
        return json.dumps({"error": "task 파라미터가 필요합니다."})

    current_depth = max(
        0,
        int(kwargs.get("delegation_depth", kwargs.get("depth", 0))),
    )
    # 현재 제품 정책은 위임받은 모든 자식의 재위임을 금지한다. 스키마 필터나
    # registry dispatch를 우회해 핸들러가 직접 호출돼도 여기서 다시 거부한다.
    if current_depth > 0:
        return json.dumps({
            "error": TOOL_BLOCKED_MESSAGE,
            "code": "TOOL_BLOCKED",
        }, ensure_ascii=False)

    # 부모 에이전트 정보 (kwargs에서 전달)
    parent_model = kwargs.get("parent_model", "gemini/gemini-3-flash-preview")
    parent_toolsets = kwargs.get("parent_toolsets", ["full"])

    manager = DelegateManager(
        parent_model=parent_model,
        parent_toolsets=parent_toolsets,
        depth=current_depth,
        parent_blocked_tools=kwargs.get("blocked_tools"),
        parent_on_cost_start=kwargs.get("on_cost_start"),
    )

    task = DelegateTask(
        task=task_text,
        toolsets=toolsets,
        max_iterations=max_iterations,
        context=context,
    )

    user_id = kwargs.get("user_id")
    if user_id is not None:
        # DelegateManager는 기존 API상 user_id를 받지 않는다. 컨텍스트 변수를
        # 통해 자식 AIAgent 생성 시 동일 인증/저장소 범위를 상속시킨다.
        from agent.core import inherited_agent_context
        from agent.memory import memory_store

        with inherited_agent_context(
            user_id=user_id,
            memory_store_instance=kwargs.get("memory_store") or memory_store,
            is_admin_context=bool(kwargs.get("is_admin_context", False)),
            delegation_depth=current_depth,
            blocked_tools=kwargs.get("blocked_tools"),
        ):
            result = manager.delegate(task)
    else:
        result = manager.delegate(task)

    return json.dumps({
        "success": result.success,
        "content": result.content,
        "tool_calls_count": result.tool_calls_count,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "error": result.error,
    }, ensure_ascii=False)


registry.register(
    name="delegate_task",
    toolset="agent_control",
    description=(
        "서브에이전트에 작업을 위임합니다. 복잡한 작업을 분할하거나 "
        "전문 도구셋이 필요한 하위 작업에 사용하세요. "
        "서브에이전트는 독립적으로 실행되며 결과만 반환합니다."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "서브에이전트에 위임할 작업 설명",
            },
            "toolsets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "서브에이전트가 사용할 toolset 목록 (예: ['seo', 'analysis']). null이면 부모와 동일.",
            },
            "max_iterations": {
                "type": "integer",
                "description": "서브에이전트 최대 반복 횟수 (기본: 20)",
                "default": 20,
            },
            "context": {
                "type": "object",
                "description": "서브에이전트에 전달할 추가 컨텍스트",
            },
        },
        "required": ["task"],
    },
    handler=_handle_delegate_task,
)


# ── memory_read ──

def _handle_memory_read(args: dict, **kwargs) -> str:
    """메모리에서 값을 읽습니다."""
    key = args.get("key", "")
    category = args.get("category", "agent")
    store, user_id, is_admin = _memory_context(kwargs)

    if not key:
        # 키 없으면 해당 카테고리 전체 목록 반환
        entries = store.list_memory(
            category=category if category != "all" else None,
            user_id=user_id,
            is_admin=is_admin,
        )
        return json.dumps({
            "entries": [
                {"key": e.key, "value": e.value, "category": e.category}
                for e in entries[:30]
            ],
            "total": len(entries),
        }, ensure_ascii=False)

    value = store.get_memory(
        key, category, user_id=user_id, is_admin=is_admin,
    )
    if value is None:
        return json.dumps({"key": key, "found": False})
    return json.dumps({"key": key, "value": value, "found": True}, ensure_ascii=False)


registry.register(
    name="memory_read",
    toolset="agent_control",
    description="에이전트 메모리에서 값을 읽습니다. 키를 생략하면 목록을 반환합니다.",
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "메모리 키 (생략하면 전체 목록)",
            },
            "category": {
                "type": "string",
                "enum": ["agent", "user", "project", "all"],
                "description": "메모리 카테고리 (기본: agent)",
                "default": "agent",
            },
        },
    },
    handler=_handle_memory_read,
)


# ── memory_write ──

def _handle_memory_write(args: dict, **kwargs) -> str:
    """메모리에 값을 저장합니다."""
    key = args.get("key", "")
    value = args.get("value", "")
    category = args.get("category", "agent")
    store, user_id, is_admin = _memory_context(kwargs)

    if not key or not value:
        return json.dumps({"error": "key와 value가 필요합니다."})

    store.update_memory(
        key, value, category, user_id=user_id, is_admin=is_admin,
    )
    effective_category = "user" if user_id is not None and not is_admin else category
    return json.dumps({
        "success": True, "key": key, "category": effective_category,
    }, ensure_ascii=False)


registry.register(
    name="memory_write",
    toolset="agent_control",
    description=(
        "에이전트 메모리에 값을 저장합니다. "
        "환경 사실, 사용자 선호도, 프로젝트 규칙 등을 기억합니다. "
        "주의: 현재 세션의 시스템 프롬프트에는 반영되지 않습니다 (다음 세션부터 적용)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "메모리 키 (예: 'preferred_style', 'user_name')",
            },
            "value": {
                "type": "string",
                "description": "저장할 값",
            },
            "category": {
                "type": "string",
                "enum": ["agent", "user", "project"],
                "description": "카테고리 (기본: agent)",
                "default": "agent",
            },
        },
        "required": ["key", "value"],
    },
    handler=_handle_memory_write,
)


# ── memory_search ──

def _handle_memory_search(args: dict, **kwargs) -> str:
    """메모리를 풀텍스트 검색합니다."""
    query = args.get("query", "")
    store, user_id, is_admin = _memory_context(kwargs)
    if not query:
        return json.dumps({"error": "query가 필요합니다."})

    entries = store.search_memory(
        query,
        limit=args.get("limit", 10),
        user_id=user_id,
        is_admin=is_admin,
    )
    return json.dumps({
        "results": [
            {"key": e.key, "value": e.value, "category": e.category}
            for e in entries
        ],
        "count": len(entries),
    }, ensure_ascii=False)


registry.register(
    name="memory_search",
    toolset="agent_control",
    description="에이전트 메모리를 검색합니다 (풀텍스트 FTS5).",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "검색 쿼리",
            },
            "limit": {
                "type": "integer",
                "description": "최대 결과 수 (기본: 10)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
    handler=_handle_memory_search,
)


# ── clarify ──

def _handle_clarify(args: dict, **kwargs) -> str:
    """사용자에게 질문합니다 (대화형 모드에서만 동작)."""
    question = args.get("question", "")
    options = args.get("options", [])

    # 실제 구현은 프론트엔드와 연동 필요
    # 현재는 질문을 반환하고 다음 사용자 입력을 기다림
    return json.dumps({
        "type": "clarification_needed",
        "question": question,
        "options": options,
        "note": "사용자의 다음 메시지가 답변입니다.",
    }, ensure_ascii=False)


registry.register(
    name="clarify",
    toolset="agent_control",
    description=(
        "사용자에게 확인이나 추가 정보를 요청합니다. "
        "불확실한 사항이 있을 때 사용하세요. "
        "서브에이전트에서는 사용할 수 없습니다."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "사용자에게 할 질문",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "선택지 목록 (선택적)",
            },
        },
        "required": ["question"],
    },
    handler=_handle_clarify,
)
