"""코호트 분석 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestCohortRoutes(unittest.TestCase):
    """코호트 이벤트 기록 / 잔존율 / LTV API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_record_event_success(self, _mock_sb):
        """이벤트 기록 성공."""
        resp = self.client.post(
            '/api/admin/cohort/event',
            json={'user_id': 'u1', 'event': 'signup', 'revenue': 10.0},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_record_event_missing_fields(self, _mock_sb):
        """필수 필드 누락 시 400."""
        resp = self.client.post(
            '/api/admin/cohort/event',
            json={'user_id': '', 'event': ''},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_retention(self, _mock_sb):
        """잔존율 조회 성공."""
        resp = self.client.get('/api/admin/cohort/retention?period=month', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_ltv(self, _mock_sb):
        """LTV 집계 조회."""
        resp = self.client.get('/api/admin/cohort/ltv', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('average_ltv', data)


if __name__ == '__main__':
    unittest.main()
