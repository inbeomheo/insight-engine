"""사용자 세그먼트 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestSegmentRoutes(unittest.TestCase):
    """세그먼트 업데이트 / 분류 / 집계 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_update_stats(self, _mock_sb):
        """사용자 통계 업데이트."""
        resp = self.client.post(
            '/api/admin/segments/update',
            json={'user_id': 'u1', 'stats': {'monthly_uses': 55}},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_update_stats_missing_user_id(self, _mock_sb):
        """user_id 누락 시 400."""
        resp = self.client.post(
            '/api/admin/segments/update',
            json={'stats': {}},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_classify_unknown_user(self, _mock_sb):
        """미등록 사용자 분류 → unknown."""
        resp = self.client.get('/api/admin/segments/classify/unknown_user', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('unknown', data['segments'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_segment_counts(self, _mock_sb):
        """세그먼트별 카운트 조회."""
        resp = self.client.get('/api/admin/segments/counts', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
