"""R69: /api/health/detailed 응답에 scheduled_jobs 필드 포함 검증."""
from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestHealthScheduledJobs(unittest.TestCase):
    """상세 헬스체크의 scheduled_jobs 필드 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_scheduled_jobs_field_present(self, _mock_sb):
        """scheduled_jobs 필드가 checks에 포함되어야 함."""
        resp = self.client.get('/api/health/detailed')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('scheduled_jobs', data['checks'])
        self.assertIsInstance(data['checks']['scheduled_jobs'], int)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.scheduler_worker.scheduler')
    def test_running_scheduler_reports_job_count(self, mock_scheduler, _mock_sb):
        """스케줄러 실행 중이면 등록된 잡 수를 반환."""
        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock(), MagicMock()]
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        self.assertEqual(data['checks']['scheduled_jobs'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.scheduler_worker.scheduler')
    def test_stopped_scheduler_reports_zero(self, mock_scheduler, _mock_sb):
        """스케줄러 미실행 시 0 반환."""
        mock_scheduler.running = False
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        self.assertEqual(data['checks']['scheduled_jobs'], 0)


if __name__ == '__main__':
    unittest.main()
