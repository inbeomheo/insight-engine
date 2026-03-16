"""Ghost CMS 발행 플러그인 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestGhostRoutes(unittest.TestCase):
    """POST /api/mcp/plugins/ghost/publish, GET /schema 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_returns_ghost_config(self, _mock_sb):
        """Ghost 스키마 엔드포인트가 설정 스키마를 반환."""
        resp = self.client.get('/api/mcp/plugins/ghost/schema',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Ghost CMS')
        self.assertIn('schema', data)
        self.assertIn('api_url', data['schema']['properties'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_missing_fields_returns_400(self, _mock_sb):
        """title/content 없이 발행 시 400."""
        resp = self.client.post('/api/mcp/plugins/ghost/publish',
                                json={'title': '', 'content': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugins.ghost.GhostPlugin.execute')
    def test_publish_success(self, mock_execute, _mock_sb):
        """정상 발행 시 성공 응답."""
        mock_execute.return_value = {
            'success': True,
            'message': 'Ghost CMS draft 포스트 생성 완료',
            'url': 'https://blog.example.com/test-post',
        }
        resp = self.client.post('/api/mcp/plugins/ghost/publish',
                                json={
                                    'title': '테스트',
                                    'content': '본문',
                                    'api_url': 'https://blog.example.com',
                                    'admin_api_key': 'abc:def',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])


if __name__ == '__main__':
    unittest.main()
