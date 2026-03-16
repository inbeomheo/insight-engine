"""Threads MCP 플러그인 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestThreadsRoutes(unittest.TestCase):
    """POST /api/mcp/threads/publish 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_content_returns_400(self, _mock_sb):
        """content 누락 시 400."""
        resp = self.client.post('/api/mcp/threads/publish',
                                json={'title': 'test'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_credentials_returns_400(self, _mock_sb):
        """access_token/user_id 누락 시 400."""
        resp = self.client.post('/api/mcp/threads/publish',
                                json={'content': 'hello', 'access_token': 'tok'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugins.threads.ThreadsPlugin.execute')
    def test_publish_success(self, mock_execute, _mock_sb):
        """발행 성공 시 200."""
        mock_execute.return_value = {
            'success': True,
            'message': 'Threads 포스트 게시 완료 (ID: 123)',
            'url': None,
        }
        resp = self.client.post('/api/mcp/threads/publish',
                                json={
                                    'content': '테스트 게시물',
                                    'access_token': 'fake-token',
                                    'user_id': '12345',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_endpoint(self, _mock_sb):
        """스키마 조회 GET."""
        resp = self.client.get('/api/mcp/threads/schema', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Threads')


if __name__ == '__main__':
    unittest.main()
