"""integration_routes.py 라우트 커버리지 테스트.

Notion, RSS, 북마크, MCP Apps, RAG 엔드포인트 커버.
"""
import io
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── Notion ──────────────────────────────────────


class TestNotionRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_notion_status(self, _):
        resp = self.client.get('/api/notion/status')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('configured', resp.get_json())

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_notion_import_missing_data(self, _):
        resp = self.client.post('/api/notion/import',
                                json={},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_notion_import_missing_url(self, _):
        resp = self.client.post('/api/notion/import',
                                json={'url': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_notion_import_missing_api_key(self, _):
        resp = self.client.post('/api/notion/import',
                                json={'url': 'https://notion.so/page-123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('API 키', resp.get_json()['error'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.export.notion_service.extract_notion_page')
    def test_notion_import_success(self, mock_extract, _):
        mock_extract.return_value = {'title': '노션 페이지', 'content': '내용'}
        resp = self.client.post('/api/notion/import',
                                json={'url': 'https://notion.so/page-123',
                                      'api_key': 'ntn_test_key'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['title'], '노션 페이지')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.export.notion_service.extract_notion_page',
           side_effect=Exception('API error'))
    def test_notion_import_exception(self, mock_extract, _):
        resp = self.client.post('/api/notion/import',
                                json={'url': 'https://notion.so/page-123',
                                      'api_key': 'ntn_test_key'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)


# ── RSS ──────────────────────────────────────


class TestRSSRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_rss_subscribe_missing_data(self, _):
        resp = self.client.post('/api/rss/subscribe', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_rss_subscribe_missing_feed_url(self, _):
        resp = self.client.post('/api/rss/subscribe',
                                json={'title': '블로그'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.rss_subscription_service.subscribe')
    def test_rss_subscribe_success(self, mock_sub, _):
        mock_sub.return_value = {'id': 'f1', 'feed_url': 'https://blog.com/rss'}
        resp = self.client.post('/api/rss/subscribe',
                                json={'feed_url': 'https://blog.com/rss'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.rss_subscription_service.list_subscriptions')
    def test_rss_list(self, mock_list, _):
        mock_list.return_value = [{'id': 'f1'}]
        resp = self.client.get('/api/rss/list')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['subscriptions']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.rss_subscription_service.unsubscribe', return_value=True)
    def test_rss_unsubscribe_success(self, mock_unsub, _):
        resp = self.client.delete('/api/rss/unsubscribe/f1', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.rss_subscription_service.unsubscribe', return_value=False)
    def test_rss_unsubscribe_not_found(self, mock_unsub, _):
        resp = self.client.delete('/api/rss/unsubscribe/nonexistent', headers=_H)
        self.assertEqual(resp.status_code, 404)


# ── 북마크 ──────────────────────────────────────


class TestBookmarkRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_bookmarks_parse_no_file(self, _):
        resp = self.client.post('/api/bookmarks/parse', headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_bookmarks_parse_wrong_ext(self, _):
        data = {'file': (io.BytesIO(b'data'), 'bookmarks.json')}
        resp = self.client.post('/api/bookmarks/parse',
                                data=data,
                                content_type='multipart/form-data',
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.bookmark_import_service.parse_bookmarks')
    def test_bookmarks_parse_success(self, mock_parse, _):
        mock_parse.return_value = [{'title': 'Site', 'url': 'https://example.com'}]
        html_content = b'<html><body><a href="https://example.com">Site</a></body></html>'
        data = {'file': (io.BytesIO(html_content), 'bookmarks.html')}
        resp = self.client.post('/api/bookmarks/parse',
                                data=data,
                                content_type='multipart/form-data',
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['count'], 1)


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
