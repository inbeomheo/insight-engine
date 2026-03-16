"""R49: /api/health/detailed에 active_requests 필드 테스트"""
import unittest
from unittest.mock import patch

from app import create_app
from routes.utility_routes import (
    increment_active_requests,
    decrement_active_requests,
    get_active_requests,
    _active_requests_lock,
)


class TestActiveRequests(unittest.TestCase):
    """active_requests 카운터 + 헬스체크 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # 카운터 초기화
        import routes.utility_routes as mod
        with _active_requests_lock:
            mod._active_requests_counter = 0

    def test_increment_and_get(self):
        """increment 후 get이 증가된 값을 반환."""
        self.assertEqual(get_active_requests(), 0)
        increment_active_requests()
        self.assertEqual(get_active_requests(), 1)
        increment_active_requests()
        self.assertEqual(get_active_requests(), 2)

    def test_decrement_does_not_go_negative(self):
        """decrement가 0 이하로 내려가지 않아야 한다."""
        decrement_active_requests()
        self.assertEqual(get_active_requests(), 0)

    def test_increment_then_decrement(self):
        """증가 후 감소하면 원래 값으로 돌아간다."""
        increment_active_requests()
        increment_active_requests()
        decrement_active_requests()
        self.assertEqual(get_active_requests(), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_health_detailed_includes_active_requests(self, _mock_sb):
        """상세 헬스체크 응답에 active_requests 필드가 포함되어야 한다."""
        resp = self.client.get('/api/health/detailed')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('active_requests', data['checks'])
        self.assertIsInstance(data['checks']['active_requests'], int)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_active_requests_is_zero_by_default(self, _mock_sb):
        """기본 상태에서 active_requests는 0."""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        self.assertEqual(data['checks']['active_requests'], 0)


if __name__ == '__main__':
    unittest.main()
