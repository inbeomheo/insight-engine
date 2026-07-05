"""MCP 서버 상태/도구 라우트 테스트."""
import asyncio
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

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
        # MCP_TOOLS에 5개 도구가 정의되어 있음
        self.assertGreaterEqual(len(data['tools']), 1)
        tool = data['tools'][0]
        self.assertIn('name', tool)
        self.assertIn('inputSchema', tool)

    def test_search_knowledge_uses_shared_rag_context_builder(self):
        """MCP 검색 핸들러가 user_id와 query를 넘겨 RAG 컨텍스트 문자열을 반환."""
        from services.mcp.mcp_server import handle_search_knowledge

        mock_builder = MagicMock()
        mock_builder.build_context.return_value = "관련 문서 컨텍스트"
        fake_rag_module = SimpleNamespace(context_builder=mock_builder)

        with patch.dict(sys.modules, {"services.rag": fake_rag_module}):
            result = asyncio.run(handle_search_knowledge({
                "user_id": "user-1",
                "query": "테스트 검색",
                "top_k": 3,
            }))

        self.assertEqual(result, "관련 문서 컨텍스트")
        self.assertNotIn("검색 실패", result)
        mock_builder.build_context.assert_called_once_with(
            "user-1",
            "테스트 검색",
            top_k=3,
        )


if __name__ == '__main__':
    unittest.main()
