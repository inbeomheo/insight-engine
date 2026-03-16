"""R62: /api/schedule GET 응답에 next_run_at 필드 포함 테스트"""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestScheduleNextRunAt(unittest.TestCase):
    """/api/schedule GET 응답의 next_run_at 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_next_run_at_with_pending_posts(self, mock_svc, _):
        """pending 상태 예약이 있을 때 next_run_at 반환"""
        mock_svc.list_by_user.return_value = [
            {'title': 'A', 'status': 'pending', 'scheduled_at': '2026-03-20T10:00:00+00:00'},
            {'title': 'B', 'status': 'pending', 'scheduled_at': '2026-03-18T10:00:00+00:00'},
            {'title': 'C', 'status': 'published', 'scheduled_at': '2026-03-15T10:00:00+00:00'},
        ]

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('next_run_at', data)
        # 가장 빠른 pending: B
        self.assertEqual(data['next_run_at'], '2026-03-18T10:00:00+00:00')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_next_run_at_none_when_no_pending(self, mock_svc, _):
        """pending 예약이 없을 때 next_run_at이 None"""
        mock_svc.list_by_user.return_value = [
            {'title': 'C', 'status': 'published', 'scheduled_at': '2026-03-15T10:00:00+00:00'},
        ]

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        data = resp.get_json()
        self.assertIsNone(data['next_run_at'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_next_run_at_none_when_empty(self, mock_svc, _):
        """예약 목록이 비어있을 때 next_run_at이 None"""
        mock_svc.list_by_user.return_value = []

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        data = resp.get_json()
        self.assertIn('next_run_at', data)
        self.assertIsNone(data['next_run_at'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_schedules_still_returned(self, mock_svc, _):
        """next_run_at 추가 후에도 schedules 필드 정상 반환"""
        mock_svc.list_by_user.return_value = [
            {'title': 'A', 'status': 'pending', 'scheduled_at': '2026-03-20T10:00:00+00:00'},
        ]

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        data = resp.get_json()
        self.assertIn('schedules', data)
        self.assertEqual(len(data['schedules']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_total_count_and_pending_count(self, mock_svc, _):
        """total_count와 pending_count 필드 반환"""
        mock_svc.list_by_user.return_value = [
            {'title': 'A', 'status': 'pending', 'scheduled_at': '2026-03-20T10:00:00+00:00'},
            {'title': 'B', 'status': 'pending', 'scheduled_at': '2026-03-18T10:00:00+00:00'},
            {'title': 'C', 'status': 'published', 'scheduled_at': '2026-03-15T10:00:00+00:00'},
        ]

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['total_count'], 3)
        self.assertEqual(data['pending_count'], 2)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.schedule_service.schedule_service')
    def test_counts_zero_when_empty(self, mock_svc, _):
        """빈 목록일 때 카운트 0"""
        mock_svc.list_by_user.return_value = []

        resp = self.client.get('/api/schedule', headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['total_count'], 0)
        self.assertEqual(data['pending_count'], 0)


if __name__ == '__main__':
    unittest.main()
