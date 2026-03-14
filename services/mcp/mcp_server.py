"""
MCP 서버 (외부 노출) (F10-09)
Model Context Protocol 서버로 외부 AI 에이전트에게 Insight Engine 기능 제공
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

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

MCP_TOOLS = [
    {
        "name": "generate_content",
        "description": "YouTube URL에서 AI 콘텐츠 생성 (블로그, 요약, 튜토리얼 등)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube URL"},
                "style_id": {
                    "type": "string",
                    "description": "콘텐츠 스타일",
                    "enum": ["blog_seo", "summary", "tutorial", "qna", "sns_post"]
                },
                "language": {
                    "type": "string",
                    "description": "출력 언어",
                    "enum": ["ko", "en", "ja"],
                    "default": "ko"
                },
                "length": {
                    "type": "string",
                    "enum": ["short", "medium", "long"],
                    "default": "medium"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "search_knowledge",
        "description": "RAG 지식베이스에서 관련 정보 검색",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색 쿼리"},
                "top_k": {"type": "integer", "description": "결과 수", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_complexity",
        "description": "콘텐츠 복잡도 및 가독성 분석",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "분석할 콘텐츠"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "repurpose_content",
        "description": "콘텐츠를 다양한 포맷으로 재활용 변환",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "target_format": {
                    "type": "string",
                    "enum": ["twitter_thread", "linkedin_post", "youtube_shorts_script",
                             "email_newsletter", "infographic_points"]
                }
            },
            "required": ["content", "target_format"]
        }
    },
    {
        "name": "translate_content",
        "description": "콘텐츠 번역 (ko/en/ja)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "target_lang": {"type": "string", "enum": ["ko", "en", "ja"]}
            },
            "required": ["text", "target_lang"]
        }
    }
]


# ── 도구 실행 핸들러 ──────────────────────────────────────────────────────────

async def handle_generate_content(args: Dict[str, Any]) -> str:
    """generate_content 도구 핸들러"""
    import httpx

    base_url = os.getenv('INSIGHT_ENGINE_URL', 'http://localhost:5001')
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{base_url}/generate", json={
            'url': args['url'],
            'style_id': args.get('style_id', 'blog_seo'),
            'language': args.get('language', 'ko'),
            'length': args.get('length', 'medium'),
        })
    resp.raise_for_status()
    data = resp.json()
    return data.get('content', data.get('error', '생성 실패'))


async def handle_search_knowledge(args: Dict[str, Any]) -> str:
    """search_knowledge 도구 핸들러"""
    try:
        from services.rag.context_builder import ContextBuilder
        builder = ContextBuilder()
        results = builder.build_context(args['query'], top_k=args.get('top_k', 5))
        return results.get('context', '검색 결과 없음')
    except Exception as e:
        return f"검색 실패: {e}"


async def handle_analyze_complexity(args: Dict[str, Any]) -> str:
    """analyze_complexity 도구 핸들러"""
    from services.analysis.complexity_service import ComplexityService
    svc = ComplexityService()
    report = svc.analyze(args['content'])
    result = report.to_dict()
    return json.dumps(result, ensure_ascii=False, indent=2)


async def handle_repurpose_content(args: Dict[str, Any]) -> str:
    """repurpose_content 도구 핸들러"""
    from services.export.repurpose_service import RepurposeService
    svc = RepurposeService()
    result = svc.repurpose(args['content'], args['target_format'])
    return result.get('content', '변환 실패')


async def handle_translate_content(args: Dict[str, Any]) -> str:
    """translate_content 도구 핸들러"""
    from services.transcript.realtime_translate_service import RealtimeTranslateService
    svc = RealtimeTranslateService()
    result = svc.translate(args['text'], args['target_lang'])
    return result.get('translated', '번역 실패')


TOOL_HANDLERS = {
    'generate_content': handle_generate_content,
    'search_knowledge': handle_search_knowledge,
    'analyze_complexity': handle_analyze_complexity,
    'repurpose_content': handle_repurpose_content,
    'translate_content': handle_translate_content,
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
            for tool in MCP_TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValueError(f"알 수 없는 도구: {name}")

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
    return MCP_TOOLS


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())
