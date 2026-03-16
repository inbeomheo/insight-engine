"""R94: /api/health/detailed에 cache_hit_rate 필드 노출 테스트."""
import unittest
from unittest.mock import patch

from app import create_app


class TestCacheHitRateHealth(unittest.TestCase):
    """health/detailed 응답의 checks에 cache_hit_rate가 포함되는지 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_cache_hit_rate_in_health(self, _):
        """checks.cache_hit_rate 필드가 존재한다."""
        resp = self.client.get(
            '/api/health/detailed',
            headers={'Origin': 'http://localhost:3000'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('checks', data)
        self.assertIn('cache_hit_rate', data['checks'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_cache_hit_rate_type(self, _):
        """cache_hit_rate는 float 타입이다."""
        resp = self.client.get(
            '/api/health/detailed',
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertIsInstance(data['checks']['cache_hit_rate'], float)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_cache_hit_rate_range(self, _):
        """cache_hit_rate는 0.0~1.0 범위다."""
        resp = self.client.get(
            '/api/health/detailed',
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        rate = data['checks']['cache_hit_rate']
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_cache_hit_rate_initial_zero(self, _):
        """초기 상태에서 cache_hit_rate = 0.0."""
        resp = self.client.get(
            '/api/health/detailed',
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertEqual(data['checks']['cache_hit_rate'], 0.0)


if __name__ == '__main__':
    unittest.main()
