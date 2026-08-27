"""integration_routes.py 라우트 커버리지 테스트.

MCP Apps, RAG 엔드포인트 커버.
"""
import io
import unittest
from unittest.mock import patch

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── MCP Apps ──────────────────────────────────────


class TestMCPApps(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.mcp_apps.app_registry.list_apps')
    def test_mcp_apps_list(self, mock_list, _):
        mock_list.return_value = []
        resp = self.client.get('/api/mcp-apps')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.mcp_apps.app_registry.get', return_value=None)
    def test_mcp_app_render_not_found(self, mock_get, _):
        resp = self.client.post('/api/mcp-apps/nonexistent/render',
                                json={'data': 'test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_mcp_app_render_no_data(self, _):
        resp = self.client.post('/api/mcp-apps/test/render',
                                data='not json',
                                content_type='text/plain',
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_mcp_app_action_missing_action(self, _):
        resp = self.client.post('/api/mcp-apps/test/action',
                                json={'some': 'data'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.mcp_apps.app_registry.get', return_value=None)
    def test_mcp_app_action_not_found(self, mock_get, _):
        resp = self.client.post('/api/mcp-apps/nonexistent/action',
                                json={'action': 'click'},
                                headers=_H)
        self.assertEqual(resp.status_code, 404)


# ── RAG 지식 베이스 ──────────────────────────────────────


class TestKnowledgeRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.RAG_ENABLED', False)
    def test_knowledge_upload_rag_disabled(self, _):
        data = {'file': (io.BytesIO(b'test'), 'doc.txt')}
        resp = self.client.post('/api/knowledge/upload',
                                data=data,
                                content_type='multipart/form-data',
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('RAG', resp.get_json()['error'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_knowledge_upload_no_file(self, _):
        resp = self.client.post('/api/knowledge/upload',
                                json={},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.RAG_ENABLED', True)
    def test_knowledge_upload_wrong_ext(self, _):
        data = {'file': (io.BytesIO(b'data'), 'doc.exe')}
        resp = self.client.post('/api/knowledge/upload',
                                data=data,
                                content_type='multipart/form-data',
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.rag.vector_store.VectorStore.add_document')
    @patch(
        'services.rag.chunker.extract_text_from_file',
        side_effect=ValueError('PDF 처리 시간이 허용 한도를 초과합니다.'),
    )
    @patch('config.RAG_ENABLED', True)
    def test_knowledge_upload_parser_limit_never_writes_vector_store(
        self, _extract, add_document, _supabase,
    ):
        data = {'file': (io.BytesIO(b'%PDF-malformed'), 'doc.pdf')}
        resp = self.client.post(
            '/api/knowledge/upload',
            data=data,
            content_type='multipart/form-data',
            headers=_H,
        )

        self.assertGreaterEqual(resp.status_code, 400)
        add_document.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.RAG_ENABLED', False)
    def test_knowledge_list_rag_disabled(self, _):
        resp = self.client.get('/api/knowledge/list')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['documents'], [])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('config.RAG_ENABLED', False)
    def test_knowledge_delete_rag_disabled(self, _):
        resp = self.client.delete('/api/knowledge/doc1', headers=_H)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
