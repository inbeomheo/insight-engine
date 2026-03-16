"""Substack MCP 플러그인 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestSubstackRoutes(unittest.TestCase):
    """POST /api/mcp/substack/publish 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_fields_returns_400(self, _mock_sb):
        """필수 필드 누락 시 400."""
        resp = self.client.post('/api/mcp/substack/publish',
                                json={'title': 'test'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugins.substack.SubstackPlugin.execute')
    def test_publish_success(self, mock_execute, _mock_sb):
        """발행 성공 시 200."""
        mock_execute.return_value = {
            'success': True,
            'message': 'Substack draft 포스트 생성 완료',
            'url': 'https://test.substack.com/p/123',
        }
        resp = self.client.post('/api/mcp/substack/publish',
                                json={
                                    'title': '테스트 제목',
                                    'content': '테스트 본문',
                                    'subdomain': 'test',
                                    'api_key': 'fake-key',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_endpoint(self, _mock_sb):
        """스키마 조회 GET."""
        resp = self.client.get('/api/mcp/substack/schema', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Substack')
        self.assertIn('schema', data)


if __name__ == '__main__':
    unittest.main()
