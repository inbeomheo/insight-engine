"""상세 헬스체크 API 테스트."""
import unittest
from unittest.mock import patch

from app import create_app


class TestHealthDetailed(unittest.TestCase):
    """GET /api/health/detailed 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_returns_structured_response(self, _mock_sb):
        """상세 헬스체크가 구조화된 JSON 반환."""
        resp = self.client.get('/api/health/detailed')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('configured_providers', data)
        self.assertIn('providers', data['checks'])
        self.assertIn('supabase', data['checks'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
    def test_supabase_enabled(self, _mock_sb):
        """Supabase 활성화 상태 반영."""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        self.assertTrue(data['checks']['supabase']['connected'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_no_providers_shows_degraded(self, _mock_sb):
        """API 키 없으면 degraded 상태."""
        with patch.dict('os.environ', {}, clear=True):
            resp = self.client.get('/api/health/detailed')
            data = resp.get_json()
            self.assertEqual(data['status'], 'degraded')
            self.assertEqual(data['configured_providers'], 0)

    def test_basic_health_still_works(self):
        """기존 /health 엔드포인트는 변함없음."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'healthy')


if __name__ == '__main__':
    unittest.main()
