"""상세 헬스체크 disk_usage 필드 테스트 (R38)."""
import unittest
from unittest.mock import patch

from app import create_app


class TestHealthDiskUsage(unittest.TestCase):
    """GET /api/health/detailed에 disk_usage 포함 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_disk_usage_in_response(self, _mock_sb):
        """disk_usage 필드가 응답에 존재."""
        resp = self.client.get('/api/health/detailed')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('disk_usage', data['checks'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_disk_usage_has_required_fields(self, _mock_sb):
        """disk_usage에 cache_dir, size_bytes, size_mb 포함."""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        du = data['checks']['disk_usage']
        self.assertIn('cache_dir', du)
        self.assertIn('size_bytes', du)
        self.assertIn('size_mb', du)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_disk_usage_size_non_negative(self, _mock_sb):
        """size_bytes는 0 이상."""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        du = data['checks']['disk_usage']
        self.assertGreaterEqual(du['size_bytes'], 0)
        self.assertGreaterEqual(du['size_mb'], 0.0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_disk_usage_size_mb_is_float(self, _mock_sb):
        """size_mb는 float 타입."""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        du = data['checks']['disk_usage']
        self.assertIsInstance(du['size_mb'], float)


if __name__ == '__main__':
    unittest.main()
