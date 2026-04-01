"""
Claude Code SDK 기반 에이전트

기존 196개 Tool Registry를 MCP 서버로 변환하여
Claude Code SDK의 query()로 에이전트를 실행합니다.

Claude Code 구독으로 동작 — 별도 API 키 불필요.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from claude_code_sdk import (
    ClaudeCodeOptions,
    create_sdk_mcp_server,
    query,
    tool as sdk_tool,
    SdkMcpTool,
)
from claude_code_sdk.types import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    UserMessage,
)

from agent.registry import registry

logger = logging.getLogger(__name__)


def _build_mcp_tools_from_registry(
    toolsets: Optional[List[str]] = None,
) -> List[SdkMcpTool]:
    """Registry의 도구들을 Claude Code SDK MCP 도구로 변환합니다."""
    entries = registry.list_tools(
        toolsets=toolsets,
        available_only=True,
    )

    mcp_tools = []
    for entry in entries:
        # 클로저로 핸들러 캡처
        def make_handler(handler_fn: Callable, tool_name: str):
            async def handler(args: dict) -> dict:
                try:
                    result = handler_fn(args)
                    if isinstance(result, str):
                        return {"content": [{"type": "text", "text": result}]}
                    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]}
                except Exception as e:
                    return {"content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}]}
            return handler

        # @tool 데코레이터로 MCP 도구 생성
        decorated = sdk_tool(
            entry.name,
            entry.description,
            entry.parameters,
        )(make_handler(entry.handler, entry.name))

        mcp_tools.append(decorated)

    return mcp_tools


def create_insight_mcp_server(
    toolsets: Optional[List[str]] = None,
) -> dict:
    """Insight Engine의 도구를 MCP 서버로 패키징합니다.

    Returns:
        McpSdkServerConfig (dict) — ClaudeCodeOptions.mcp_servers에 전달
    """
    tools = _build_mcp_tools_from_registry(toolsets)
    server = create_sdk_mcp_server(
        name="insight-engine",
        version="1.0.0",
        tools=tools,
    )
    logger.info("MCP 서버 생성: %d개 도구", len(tools))
    return server


async def run_sdk_agent(
    message: str,
    system_prompt: Optional[str] = None,
    toolsets: Optional[List[str]] = None,
    model: Optional[str] = None,
    max_turns: int = 30,
    on_text: Optional[Callable[[str], None]] = None,
    on_tool: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Claude Code SDK로 에이전트를 실행합니다.

    Args:
        message: 사용자 메시지
        system_prompt: 시스템 프롬프트 (None이면 기본값)
        toolsets: 사용할 Toolset 목록 (None이면 전체)
        model: Claude 모델 (None이면 기본값)
        max_turns: 최대 턴 수
        on_text: 텍스트 스트리밍 콜백
        on_tool: 도구 호출 알림 콜백

    Returns:
        {"content": str, "tool_calls": int, "elapsed": float}
    """
    # 도구 디스커버리 (최초 1회)
    if registry.tool_count == 0:
        from agent.tools import discover_tools
        discover_tools()

    # Toolset 해석
    if toolsets:
        from agent.toolsets import resolve_toolset_names
        leaf_names = resolve_toolset_names(toolsets)
    else:
        leaf_names = None

    # MCP 서버 생성
    mcp_server = create_insight_mcp_server(toolsets=leaf_names)

    # 시스템 프롬프트
    if not system_prompt:
        system_prompt = (
            "당신은 Insight Engine의 AI 에이전트입니다.\n"
            "사용자의 콘텐츠 생성 요청을 처리합니다.\n"
            "mcp__insight-engine__ 접두사가 붙은 도구를 활용하여 "
            "URL에서 콘텐츠를 수집하고, 분석하고, 고품질 콘텐츠를 작성합니다.\n"
            "항상 한국어로 응답합니다."
        )

    # allowed_tools: MCP 도구만 허용
    entries = registry.list_tools(toolsets=leaf_names, available_only=True)
    allowed = [f"mcp__insight-engine__{e.name}" for e in entries]

    start = time.time()
    content_parts = []
    tool_calls = 0

    options = ClaudeCodeOptions(
        system_prompt=system_prompt,
        mcp_servers={"insight-engine": mcp_server},
        allowed_tools=allowed,
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        model=model,
    )

    async for msg in query(prompt=message, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    content_parts.append(block.text)
                    if on_text:
                        on_text(block.text)
                elif hasattr(block, "name"):
                    tool_calls += 1
                    if on_tool:
                        on_tool(block.name)

        elif isinstance(msg, ResultMessage):
            # 최종 결과
            pass

    elapsed = time.time() - start
    final_content = "\n".join(content_parts)

    logger.info(
        "SDK 에이전트 완료: %d도구, %.1f초, %d자",
        tool_calls, elapsed, len(final_content),
    )

    return {
        "content": final_content,
        "tool_calls": tool_calls,
        "elapsed": round(elapsed, 2),
    }


def run_sdk_agent_sync(
    message: str,
    **kwargs,
) -> Dict[str, Any]:
    """동기 래퍼 — Flask에서 호출용."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, run_sdk_agent(message, **kwargs))
            return future.result(timeout=300)
    else:
        return asyncio.run(run_sdk_agent(message, **kwargs))
