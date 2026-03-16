"""캐시 통계 API 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestCacheStats(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_returns_stats(self, _mock_sb):
        """캐시 통계가 구조화된 JSON 반환."""
        resp = self.client.get('/api/cache/stats', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('count', data)
        self.assertIn('total_mb', data)
        self.assertIn('max_mb', data)
        self.assertIn('ttl_days', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_count_is_non_negative(self, _mock_sb):
        """캐시 항목 수는 0 이상."""
        resp = self.client.get('/api/cache/stats', headers=_HEADERS)
        data = resp.get_json()
        self.assertGreaterEqual(data['count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_total_mb_is_numeric(self, _mock_sb):
        """total_mb가 숫자."""
        resp = self.client.get('/api/cache/stats', headers=_HEADERS)
        data = resp.get_json()
        self.assertIsInstance(data['total_mb'], (int, float))


if __name__ == '__main__':
    unittest.main()
