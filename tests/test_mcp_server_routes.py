"""MCP 서버 상태/도구 라우트 테스트."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestMCPServerRoutes(unittest.TestCase):
    """GET /api/mcp/status, /api/mcp/tools 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_status_returns_mcp_info(self, _mock_sb):
        """MCP 상태 엔드포인트가 서버 정보를 반환."""
        resp = self.client.get('/api/mcp/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('mcp_available', data)
        self.assertEqual(data['server_name'], 'insight-engine')
        self.assertEqual(data['server_version'], '1.0.0')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_tools_returns_list(self, _mock_sb):
        """MCP 도구 목록 엔드포인트가 도구 스키마를 반환."""
        resp = self.client.get('/api/mcp/tools', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('tools', data)
        self.assertIsInstance(data['tools'], list)
        self.assertGreaterEqual(len(data['tools']), 1)
        tool = data['tools'][0]
        self.assertIn('name', tool)
        self.assertIn('inputSchema', tool)

    def test_default_schema_excludes_unmetered_or_user_scoped_tools(self):
        """인증·사용량 컨텍스트 없는 stdio에서는 안전한 로컬 분석만 노출."""
        from services.mcp.mcp_server import get_mcp_tools_schema

        with patch.dict(os.environ, {"INSIGHT_ENGINE_API_TOKEN": ""}):
            names = {tool["name"] for tool in get_mcp_tools_schema()}

        self.assertEqual(names, {"analyze_complexity"})
        self.assertTrue(names.isdisjoint({
            "search_knowledge",
            "repurpose_content",
            "translate_content",
            "generate_content",
        }))

    def test_configured_schema_adds_authenticated_generate_only(self):
        from services.mcp.mcp_server import get_mcp_tools_schema

        with patch.dict(os.environ, {"INSIGHT_ENGINE_API_TOKEN": "server-token"}):
            tools = get_mcp_tools_schema()

        names = {tool["name"] for tool in tools}
        self.assertEqual(names, {"analyze_complexity", "generate_content"})
        serialized = str(tools)
        self.assertNotIn("user_id", serialized)

    def test_invalid_server_url_keeps_generate_tool_disabled(self):
        from services.mcp.mcp_server import get_mcp_tools_schema

        with patch.dict(os.environ, {
            "INSIGHT_ENGINE_API_TOKEN": "server-token",
            "INSIGHT_ENGINE_URL": "file:///etc/passwd",
        }):
            names = {tool["name"] for tool in get_mcp_tools_schema()}

        self.assertEqual(names, {"analyze_complexity"})

    def test_generate_without_server_token_fails_before_network(self):
        from services.mcp.mcp_server import (
            MCPToolUnavailable,
            handle_generate_content,
        )

        with (
            patch.dict(os.environ, {"INSIGHT_ENGINE_API_TOKEN": ""}),
            patch("httpx.AsyncClient") as mock_client,
            self.assertRaises(MCPToolUnavailable),
        ):
            asyncio.run(handle_generate_content({"url": "https://youtu.be/abc"}))
        mock_client.assert_not_called()

    def test_generate_sends_server_auth_and_idempotency_headers(self):
        from services.mcp.mcp_server import handle_generate_content

        response = MagicMock(status_code=200)
        response.json.return_value = {"content": "완성된 콘텐츠"}
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.post = AsyncMock(return_value=response)

        with (
            patch.dict(os.environ, {
                "INSIGHT_ENGINE_API_TOKEN": "server-token",
                "INSIGHT_ENGINE_URL": "https://engine.example/base/",
            }),
            patch("httpx.AsyncClient", return_value=client),
        ):
            result = asyncio.run(handle_generate_content({
                "url": "https://youtu.be/abc",
                "style_id": "summary",
            }))

        self.assertEqual(result, "완성된 콘텐츠")
        call = client.post.await_args
        self.assertEqual(call.args[0], "https://engine.example/base/generate")
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer server-token")
        self.assertRegex(call.kwargs["headers"]["Idempotency-Key"], r"^mcp-[a-f0-9]{32}$")
        self.assertEqual(call.kwargs["json"], {
            "url": "https://youtu.be/abc",
            "style": "summary",
            "modifiers": {"language": "ko", "length": "medium"},
        })

    def test_generate_does_not_expose_provider_exception(self):
        from services.mcp.mcp_server import handle_generate_content

        raw_secret = "Authorization: Bearer top-secret"
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.post = AsyncMock(side_effect=RuntimeError(raw_secret))

        with (
            patch.dict(os.environ, {"INSIGHT_ENGINE_API_TOKEN": "server-token"}),
            patch("httpx.AsyncClient", return_value=client),
        ):
            result = asyncio.run(handle_generate_content({
                "url": "https://youtu.be/abc",
            }))

        self.assertNotIn(raw_secret, result)
        self.assertEqual(result, "콘텐츠 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.")


if __name__ == '__main__':
    unittest.main()
