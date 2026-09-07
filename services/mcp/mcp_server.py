"""
MCP 서버 (외부 노출) (F10-09)
Model Context Protocol 서버로 외부 AI 에이전트에게 Insight Engine 기능 제공
"""
import json
import logging
import os
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

logger = logging.getLogger(__name__)

# MCP SDK 선택적 import
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    import mcp.types as mcp_types
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    logger.info("MCP SDK 미설치 — pip install mcp")


# ── MCP 도구 정의 ─────────────────────────────────────────────────────────────

_ANALYZE_COMPLEXITY_TOOL = {
    "name": "analyze_complexity",
    "description": "콘텐츠 복잡도 및 가독성 분석",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "분석할 콘텐츠",
                "maxLength": 100000,
            }
        },
        "required": ["content"],
        "additionalProperties": False,
    },
}

_GENERATE_CONTENT_TOOL = {
    "name": "generate_content",
    "description": "YouTube URL에서 AI 콘텐츠 생성 (블로그, 요약, 튜토리얼 등)",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "YouTube URL",
                "maxLength": 2048,
            },
            "style_id": {
                "type": "string",
                "description": "콘텐츠 스타일",
                "enum": ["blog_seo", "summary", "tutorial", "qna", "sns_post"],
            },
            "language": {
                "type": "string",
                "description": "출력 언어",
                "enum": ["ko", "en", "ja"],
                "default": "ko",
            },
            "length": {
                "type": "string",
                "enum": ["short", "medium", "long"],
                "default": "medium",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
}

# Backwards-compatible constant containing only tools that are always safe.
# Config-dependent tools are returned by get_mcp_tools_schema().
MCP_TOOLS = [_ANALYZE_COMPLEXITY_TOOL]


class MCPToolUnavailable(RuntimeError):
    """Raised when an MCP tool is not safely configured on the server."""


def _get_api_token() -> str:
    token = os.getenv("INSIGHT_ENGINE_API_TOKEN", "").strip()
    if "\r" in token or "\n" in token:
        return ""
    return token


def _get_generate_endpoint() -> str:
    """Return a validated server-controlled /generate endpoint."""
    raw_base = os.getenv("INSIGHT_ENGINE_URL", "http://localhost:5001").strip()
    parsed = urlsplit(raw_base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MCPToolUnavailable("MCP 콘텐츠 생성 서버 설정이 올바르지 않습니다.")

    base_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, f"{base_path}/generate", "", ""))


# ── 도구 실행 핸들러 ──────────────────────────────────────────────────────────

async def handle_generate_content(args: Dict[str, Any]) -> str:
    """generate_content 도구 핸들러"""
    import httpx

    api_token = _get_api_token()
    if not api_token:
        raise MCPToolUnavailable("MCP 콘텐츠 생성이 구성되지 않았습니다.")

    url = args.get("url")
    if not isinstance(url, str) or not url.strip() or len(url) > 2048:
        return "콘텐츠 생성 요청이 올바르지 않습니다."

    style_id = args.get("style_id", "blog_seo")
    language = args.get("language", "ko")
    length = args.get("length", "medium")
    if style_id not in {"blog_seo", "summary", "tutorial", "qna", "sns_post"}:
        return "콘텐츠 생성 요청이 올바르지 않습니다."
    if language not in {"ko", "en", "ja"} or length not in {"short", "medium", "long"}:
        return "콘텐츠 생성 요청이 올바르지 않습니다."

    try:
        endpoint = _get_generate_endpoint()
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Idempotency-Key": f"mcp-{uuid4().hex}",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                endpoint,
                headers=headers,
                json={
                    "url": url.strip(),
                    "style": style_id,
                    "modifiers": {
                        "language": language,
                        "length": length,
                    },
                },
            )
        if not 200 <= resp.status_code < 300:
            logger.warning("MCP content generation failed (status=%s)", resp.status_code)
            return "콘텐츠 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
        data = resp.json()
        content = data.get("content") if isinstance(data, dict) else None
        if not isinstance(content, str) or not content:
            return "콘텐츠 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
        return content
    except MCPToolUnavailable:
        raise
    except Exception as exc:
        logger.warning(
            "MCP content generation failed (%s)",
            type(exc).__name__,
        )
        return "콘텐츠 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."


async def handle_analyze_complexity(args: Dict[str, Any]) -> str:
    """analyze_complexity 도구 핸들러"""
    from services.analysis.complexity_service import ComplexityService

    content = args.get("content")
    if not isinstance(content, str) or not content or len(content) > 100000:
        return "복잡도 분석 요청이 올바르지 않습니다."
    svc = ComplexityService()
    report = svc.analyze(content)
    result = report.to_dict()
    return json.dumps(result, ensure_ascii=False, indent=2)


TOOL_HANDLERS = {
    'generate_content': handle_generate_content,
    'analyze_complexity': handle_analyze_complexity,
}


# ── MCP 서버 실행 ─────────────────────────────────────────────────────────────

def create_mcp_server():
    """MCP 서버 인스턴스 생성"""
    if not _MCP_AVAILABLE:
        raise RuntimeError("MCP SDK 미설치: pip install mcp")

    server = Server("insight-engine")

    @server.list_tools()
    async def list_tools():
        return [
            mcp_types.Tool(
                name=tool['name'],
                description=tool['description'],
                inputSchema=tool['inputSchema'],
            )
            for tool in get_mcp_tools_schema()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        enabled_names = {tool["name"] for tool in get_mcp_tools_schema()}
        if name not in enabled_names:
            raise MCPToolUnavailable("요청한 MCP 도구를 사용할 수 없습니다.")
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise MCPToolUnavailable("요청한 MCP 도구를 사용할 수 없습니다.")

        result = await handler(arguments)
        return [mcp_types.TextContent(type="text", text=str(result))]

    return server


async def run_mcp_server():
    """MCP 서버 실행 (stdio 전송)"""
    if not _MCP_AVAILABLE:
        logger.error("MCP SDK 미설치")
        return

    from mcp.server.stdio import stdio_server

    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="insight-engine",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


def get_mcp_tools_schema() -> List[Dict]:
    """도구 스키마 반환 (REST API용)"""
    tools = list(MCP_TOOLS)
    if _get_api_token():
        try:
            _get_generate_endpoint()
        except MCPToolUnavailable:
            logger.warning("MCP content generation is disabled by invalid server URL")
        else:
            tools.append(_GENERATE_CONTENT_TOOL)
    return tools


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())
