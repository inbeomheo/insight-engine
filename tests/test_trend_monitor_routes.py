"""트렌드 키워드 모니터 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestTrendMonitorRoutes(unittest.TestCase):
    """트렌드 키워드 추가/삭제/조회 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # 싱글톤 리셋
        import routes.analytics_routes as ar
        ar._trend_monitor = None

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_keywords_empty(self, _mock_sb):
        """초기 키워드 목록은 빈 배열."""
        resp = self.client.get('/api/admin/trends/keywords', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['keywords'], [])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_add_keyword(self, _mock_sb):
        """키워드 추가."""
        resp = self.client.post(
            '/api/admin/trends/keywords',
            json={'keyword': 'AI'},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('AI', resp.get_json()['keywords'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_add_keyword_empty(self, _mock_sb):
        """빈 키워드 추가 시 400."""
        resp = self.client.post(
            '/api/admin/trends/keywords',
            json={'keyword': ''},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_cached_returns_data(self, _mock_sb):
        """캐시 조회."""
        resp = self.client.get('/api/admin/trends/cached', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data', resp.get_json())


if __name__ == '__main__':
    unittest.main()
