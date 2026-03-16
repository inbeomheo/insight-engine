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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_has_oldest_and_newest_entry(self, _mock_sb):
        """oldest_entry와 newest_entry 필드가 응답에 포함."""
        resp = self.client.get('/api/cache/stats', headers=_HEADERS)
        data = resp.get_json()
        self.assertIn('oldest_entry', data)
        self.assertIn('newest_entry', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_cache_has_null_entries(self, _mock_sb):
        """빈 캐시에서 oldest/newest는 None."""
        resp = self.client.get('/api/cache/stats', headers=_HEADERS)
        data = resp.get_json()
        if data['count'] == 0:
            self.assertIsNone(data['oldest_entry'])
            self.assertIsNone(data['newest_entry'])


if __name__ == '__main__':
    unittest.main()
