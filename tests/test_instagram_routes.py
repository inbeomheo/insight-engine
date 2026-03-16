"""Instagram 발행 플러그인 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestInstagramRoutes(unittest.TestCase):
    """POST /api/mcp/plugins/instagram/publish, GET /schema 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_returns_instagram_config(self, _mock_sb):
        """Instagram 스키마 엔드포인트가 설정 스키마를 반환."""
        resp = self.client.get('/api/mcp/plugins/instagram/schema',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Instagram')
        self.assertIn('image_url', data['schema']['properties'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_missing_content_returns_400(self, _mock_sb):
        """title/content 없이 발행 시 400."""
        resp = self.client.post('/api/mcp/plugins/instagram/publish',
                                json={'title': '제목'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugins.instagram.InstagramPlugin.execute')
    def test_publish_success(self, mock_execute, _mock_sb):
        """정상 발행 시 성공 응답."""
        mock_execute.return_value = {
            'success': True,
            'message': 'Instagram 포스트 게시 완료',
            'url': 'https://www.instagram.com/p/123/',
        }
        resp = self.client.post('/api/mcp/plugins/instagram/publish',
                                json={
                                    'title': '테스트',
                                    'content': '본문',
                                    'access_token': 'token123',
                                    'instagram_account_id': 'acct1',
                                    'image_url': 'https://example.com/img.jpg',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])


if __name__ == '__main__':
    unittest.main()
