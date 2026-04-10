"""integration_routes.py 라우트 커버리지 테스트.

Notion, Google Docs, RSS, 북마크, MCP, 발행 큐, 예약, RAG, 이메일,
버전, 검색, 폴더 엔드포인트 커버.
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


# ── Google Docs ──────────────────────────────────────


class TestGDocsRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_gdocs_import_missing_data(self, _):
        resp = self.client.post('/api/gdocs/import', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_gdocs_import_missing_url(self, _):
        resp = self.client.post('/api/gdocs/import',
                                json={'url': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.export.gdocs_service.extract_google_doc')
    def test_gdocs_import_success(self, mock_extract, _):
        mock_extract.return_value = {'title': 'Docs 제목', 'content': '내용'}
        resp = self.client.post('/api/gdocs/import',
                                json={'url': 'https://docs.google.com/document/d/abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)


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


# ── MCP 플러그인 ──────────────────────────────────────


class TestMCPRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugin_registry.list_plugins')
    def test_mcp_list_plugins(self, mock_list, _):
        mock_list.return_value = [{'id': 'naver', 'name': 'Naver Blog'}]
        resp = self.client.get('/api/mcp/plugins')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('plugins', resp.get_json())

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_mcp_publish_missing_data(self, _):
        resp = self.client.post('/api/mcp/publish', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_mcp_publish_missing_fields(self, _):
        resp = self.client.post('/api/mcp/publish',
                                json={'plugin_id': 'naver'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugin_registry.execute')
    def test_mcp_publish_success(self, mock_exec, _):
        mock_exec.return_value = {'success': True, 'url': 'https://blog.naver.com/123'}
        resp = self.client.post('/api/mcp/publish',
                                json={'plugin_id': 'naver',
                                      'title': '테스트',
                                      'content': '콘텐츠'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugin_registry.execute',
           side_effect=Exception('plugin error'))
    def test_mcp_publish_exception(self, mock_exec, _):
        resp = self.client.post('/api/mcp/publish',
                                json={'plugin_id': 'naver',
                                      'title': '테스트',
                                      'content': '콘텐츠'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)


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


# ── 발행 큐 ──────────────────────────────────────


class TestPublishQueue(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.publish_queue_service.publish_queue_service')
    def test_publish_queue_list(self, mock_pq, _):
        mock_pq.get_queue_status.return_value = []
        mock_pq.get_status_summary.return_value = {'pending': 0}
        resp = self.client.get('/api/publish-queue')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('items', resp.get_json())

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_queue_enqueue_missing_data(self, _):
        resp = self.client.post('/api/publish-queue', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_queue_enqueue_missing_fields(self, _):
        resp = self.client.post('/api/publish-queue',
                                json={'content_id': 'c1'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.publish_queue_service.publish_queue_service')
    def test_publish_queue_enqueue_success(self, mock_pq, _):
        mock_pq.enqueue.return_value = {'id': 'item1', 'status': 'pending'}
        resp = self.client.post('/api/publish-queue',
                                json={'content_id': 'c1', 'title': '제목',
                                      'content': '내용', 'plugin_id': 'naver'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.publish_queue_service.publish_queue_service')
    def test_publish_queue_cancel(self, mock_pq, _):
        mock_pq.cancel_item.return_value = {'success': True}
        resp = self.client.post('/api/publish-queue/item1/cancel', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.publish_queue_service.publish_queue_service')
    def test_publish_queue_retry(self, mock_pq, _):
        mock_pq.retry_item.return_value = {'success': True}
        resp = self.client.post('/api/publish-queue/item1/retry', headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 예약 발행 ──────────────────────────────────────


class TestScheduleRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schedule_create_missing_data(self, _):
        resp = self.client.post('/api/schedule', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schedule_create_missing_fields(self, _):
        resp = self.client.post('/api/schedule',
                                json={'title': '제목'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedule_create_success(self, mock_sched, _):
        mock_sched.create.return_value = {'id': 's1', 'status': 'pending'}
        resp = self.client.post('/api/schedule',
                                json={'title': '제목', 'content': '내용',
                                      'target_plugin': 'naver',
                                      'scheduled_at': '2026-04-15T10:00:00Z'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedule_create_returns_none(self, mock_sched, _):
        mock_sched.create.return_value = None
        resp = self.client.post('/api/schedule',
                                json={'title': '제목', 'content': '내용',
                                      'target_plugin': 'naver',
                                      'scheduled_at': '2026-04-15T10:00:00Z'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedule_list(self, mock_sched, _):
        mock_sched.list_by_user.return_value = [
            {'id': 's1', 'status': 'pending', 'scheduled_at': '2026-04-15T10:00:00Z'}
        ]
        resp = self.client.get('/api/schedule')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('schedules', data)
        self.assertEqual(data['pending_count'], 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedule_delete_success(self, mock_sched, _):
        mock_sched.delete.return_value = True
        resp = self.client.delete('/api/schedule/s1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedule_delete_not_found(self, mock_sched, _):
        mock_sched.delete.return_value = False
        resp = self.client.delete('/api/schedule/s999', headers=_H)
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


# ── 이메일 인제스트 ──────────────────────────────────────


class TestEmailIngest(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_email_ingest_no_file_no_json(self, _):
        resp = self.client.post('/api/email/ingest', headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_email_ingest_wrong_ext(self, _):
        data = {'file': (io.BytesIO(b'data'), 'email.txt')}
        resp = self.client.post('/api/email/ingest',
                                data=data,
                                content_type='multipart/form-data',
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_email_ingest_empty_raw_text(self, _):
        resp = self.client.post('/api/email/ingest',
                                json={'raw_text': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.email_ingest_service.parse_forwarded_email')
    def test_email_ingest_text_mode(self, mock_parse, _):
        mock_parse.return_value = {'subject': '뉴스레터', 'body': '내용'}
        resp = self.client.post('/api/email/ingest',
                                json={'raw_text': 'Subject: 테스트\n\n내용'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 버전 히스토리 ──────────────────────────────────────


class TestVersionRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.list_versions')
    def test_list_versions(self, mock_list, _):
        mock_list.return_value = [{'id': 'v1', 'created_at': '2026-01-01'}]
        resp = self.client.get('/api/content/c1/versions')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['versions']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_save_version_empty_content(self, _):
        resp = self.client.post('/api/content/c1/versions',
                                json={'content': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.save_version')
    def test_save_version_success(self, mock_save, _):
        mock_save.return_value = {'id': 'v2', 'content_id': 'c1'}
        resp = self.client.post('/api/content/c1/versions',
                                json={'content': '새 버전 내용', 'title': '제목'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.get_version', return_value=None)
    def test_get_version_not_found(self, mock_get, _):
        resp = self.client.get('/api/content/c1/versions/v999')
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.get_version')
    def test_get_version_success(self, mock_get, _):
        mock_get.return_value = {'id': 'v1', 'content': '내용'}
        resp = self.client.get('/api/content/c1/versions/v1')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_diff_versions_missing_params(self, _):
        resp = self.client.get('/api/content/c1/versions/diff')
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.diff_versions')
    def test_diff_versions_success(self, mock_diff, _):
        mock_diff.return_value = {'added': 5, 'removed': 2}
        resp = self.client.get('/api/content/c1/versions/diff?a=v1&b=v2')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.version_service.restore_version', return_value=None)
    def test_restore_version_not_found(self, mock_restore, _):
        resp = self.client.post('/api/content/c1/versions/v999/restore',
                                headers=_H)
        self.assertEqual(resp.status_code, 404)


# ── 검색 ──────────────────────────────────────


class TestSearchRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.seo.search_service.search')
    def test_search_content(self, mock_search, _):
        mock_search.return_value = {'results': [], 'total': 0}
        resp = self.client.get('/api/search?q=test')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.get_json())


# ── 폴더 ──────────────────────────────────────


class TestFolderRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.folder_service.list_folders')
    def test_list_folders(self, mock_list, _):
        mock_list.return_value = [{'id': 'f1', 'name': '폴더1'}]
        resp = self.client.get('/api/folders')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['folders']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_folder_missing_name(self, _):
        resp = self.client.post('/api/folders', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.folder_service.create_folder')
    def test_create_folder_success(self, mock_create, _):
        mock_create.return_value = {'id': 'f2', 'name': '새 폴더'}
        resp = self.client.post('/api/folders',
                                json={'name': '새 폴더'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.folder_service.update_folder', return_value=None)
    def test_update_folder_not_found(self, mock_update, _):
        resp = self.client.put('/api/folders/f999',
                               json={'name': '변경'},
                               headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.folder_service.delete_folder', return_value=False)
    def test_delete_folder_not_found(self, mock_delete, _):
        resp = self.client.delete('/api/folders/f999', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.folder_service.delete_folder', return_value=True)
    def test_delete_folder_success(self, mock_delete, _):
        resp = self.client.delete('/api/folders/f1', headers=_H)
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
