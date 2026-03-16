"""스케줄러 상태 조회 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestSchedulerRoutes(unittest.TestCase):
    """GET /api/scheduler/status 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.scheduler_worker.scheduler')
    def test_status_returns_jobs(self, mock_scheduler, _mock_sb):
        """스케줄러 잡 목록 반환."""
        mock_job = MagicMock()
        mock_job.id = 'publish_checker'
        mock_job.name = 'check_and_publish'
        mock_job.next_run_time = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
        mock_job.trigger = MagicMock(__str__=lambda s: 'interval[0:01:00]')

        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [mock_job]

        resp = self.client.get('/api/scheduler/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['running'])
        self.assertEqual(data['total_jobs'], 1)
        self.assertEqual(data['jobs'][0]['id'], 'publish_checker')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.scheduler_worker.scheduler')
    def test_status_not_running(self, mock_scheduler, _mock_sb):
        """스케줄러 미실행 상태."""
        mock_scheduler.running = False
        mock_scheduler.get_jobs.return_value = []

        resp = self.client.get('/api/scheduler/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['running'])
        self.assertEqual(data['total_jobs'], 0)


if __name__ == '__main__':
    unittest.main()
