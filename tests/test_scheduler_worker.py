"""scheduler_worker 단위 테스트 — check_and_publish, start/stop_scheduler"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


ROOT = Path(__file__).resolve().parents[1]


class TestCheckAndPublish(unittest.TestCase):
    """check_and_publish: 예약 포스트 발행 로직"""

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    @patch('services.mcp.plugin_registry')
    def test_no_due_posts(self, mock_registry, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = []
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_registry.execute.assert_not_called()

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    @patch('services.mcp.plugin_registry')
    def test_successful_publish(self, mock_registry, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = [
            {'id': 'p1', 'target_plugin': 'naver', 'content': 'body', 'title': 'title'}
        ]
        mock_registry.execute.return_value = {'success': True, 'url': 'https://blog.naver.com/1'}
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_schedule.update_status.assert_called_once_with(
            'p1', 'published', published_url='https://blog.naver.com/1'
        )

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    @patch('services.mcp.plugin_registry')
    def test_failed_publish(self, mock_registry, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = [
            {'id': 'p2', 'target_plugin': 'wp', 'content': 'c', 'title': 't'}
        ]
        mock_registry.execute.return_value = {'success': False, 'message': 'auth error'}
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_schedule.update_status.assert_called_once_with(
            'p2', 'failed', error_message='auth error'
        )

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    @patch('services.mcp.plugin_registry')
    def test_exception_during_publish(self, mock_registry, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = [
            {'id': 'p3', 'target_plugin': 'x', 'content': 'c', 'title': 't'}
        ]
        mock_registry.execute.side_effect = RuntimeError("network")
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_schedule.update_status.assert_called_once_with('p3', 'failed', error_message='network')


class TestStartSchedulerLeaderLock(unittest.TestCase):
    """start_scheduler: gunicorn worker별 중복 스케줄러 방지"""

    @patch.dict('os.environ', {'SCHEDULER_ENABLED': 'true'}, clear=False)
    def test_start_scheduler_skips_when_another_worker_holds_leader_lock(self):
        from services.data import scheduler_worker

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_app = MagicMock()

        with patch.object(scheduler_worker, '_get_scheduler', return_value=mock_scheduler), \
             patch.object(scheduler_worker, '_acquire_scheduler_leader_lock', return_value=False), \
             patch.object(scheduler_worker.logger, 'info') as mock_info:
            scheduler_worker.start_scheduler(mock_app)

        mock_scheduler.add_job.assert_not_called()
        mock_scheduler.start.assert_not_called()
        mock_info.assert_any_call('다른 worker가 스케줄러 리더락을 보유 중 — 스케줄러 기동 생략')

    @patch.dict('os.environ', {'SCHEDULER_ENABLED': 'true', 'AUTO_BACKUP_INTERVAL_HOURS': '6'}, clear=False)
    def test_start_scheduler_registers_app_data_backup_when_configured(self):
        from services.data import scheduler_worker

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None

        with patch.object(scheduler_worker, '_get_scheduler', return_value=mock_scheduler), \
             patch.object(scheduler_worker, '_acquire_scheduler_leader_lock', return_value=True), \
             patch.object(scheduler_worker, '_scheduler', None):
            scheduler_worker.start_scheduler(mock_app)
            scheduler_worker.stop_scheduler()

        job_ids = [call.kwargs.get('id') for call in mock_scheduler.add_job.call_args_list]
        self.assertIn('app_data_backup', job_ids)

    def test_start_scheduler_writes_and_registers_heartbeat_when_configured(self):
        from services.data import scheduler_worker

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None

        with tempfile.TemporaryDirectory() as tempdir:
            heartbeat = Path(tempdir) / 'scheduler.heartbeat'
            env = {
                'SCHEDULER_ENABLED': 'true',
                'SCHEDULER_HEARTBEAT_FILE': str(heartbeat),
                'SCHEDULER_HEARTBEAT_INTERVAL_SECONDS': '7',
            }
            with patch.dict('os.environ', env, clear=False), \
                 patch.object(scheduler_worker, '_get_scheduler', return_value=mock_scheduler), \
                 patch.object(scheduler_worker, '_acquire_scheduler_leader_lock', return_value=True), \
                 patch.object(scheduler_worker, '_scheduler', None):
                scheduler_worker.start_scheduler(mock_app)
                scheduler_worker.stop_scheduler()

            self.assertTrue(heartbeat.exists())

        heartbeat_jobs = [
            call for call in mock_scheduler.add_job.call_args_list
            if call.kwargs.get('id') == 'scheduler_heartbeat'
        ]
        self.assertEqual(len(heartbeat_jobs), 1)
        self.assertEqual(heartbeat_jobs[0].args[1], 'interval')
        self.assertEqual(heartbeat_jobs[0].kwargs['seconds'], 7)


class TestBackupConfiguration(unittest.TestCase):
    """app_data 백업 스케줄러 설정 파싱"""

    @patch.dict('os.environ', {'MAX_BACKUPS': '14'}, clear=False)
    def test_max_backups_returns_configured_integer(self):
        from services.data.scheduler_worker import _max_backups

        self.assertEqual(_max_backups(), 14)

    @patch.dict('os.environ', {'MAX_BACKUPS': 'invalid'}, clear=False)
    def test_max_backups_ignores_invalid_values(self):
        from services.data.scheduler_worker import _max_backups

        self.assertIsNone(_max_backups())

    @patch.dict('os.environ', {'MAX_BACKUPS': '14', 'APP_DATA_BACKUP_REPLICA_MAX_BACKUPS': ''}, clear=False)
    def test_max_replica_backups_defaults_to_max_backups(self):
        from services.data.scheduler_worker import _max_replica_backups

        self.assertEqual(_max_replica_backups(), 14)

    @patch.dict('os.environ', {'MAX_BACKUPS': '14', 'APP_DATA_BACKUP_REPLICA_MAX_BACKUPS': '21'}, clear=False)
    def test_max_replica_backups_uses_replica_override(self):
        from services.data.scheduler_worker import _max_replica_backups

        self.assertEqual(_max_replica_backups(), 21)


class TestSchedulerWorkerEntrypoint(unittest.TestCase):
    """scripts/run_scheduler_worker.py: K8s worker no-op 방지"""

    def test_scheduler_worker_entrypoint_refuses_disabled_scheduler(self):
        env = os.environ.copy()
        env['SCHEDULER_ENABLED'] = 'false'

        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'run_scheduler_worker.py')],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn('SCHEDULER_ENABLED must be true', result.stderr)


class TestStopScheduler(unittest.TestCase):
    """stop_scheduler: 스케줄러 종료"""

    @patch('services.data.scheduler_worker.scheduler')
    def test_stop_running_scheduler(self, mock_scheduler):
        mock_scheduler.running = True
        from services.data.scheduler_worker import stop_scheduler
        stop_scheduler()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    @patch('services.data.scheduler_worker.scheduler')
    def test_stop_not_running(self, mock_scheduler):
        mock_scheduler.running = False
        from services.data.scheduler_worker import stop_scheduler
        stop_scheduler()
        mock_scheduler.shutdown.assert_not_called()


if __name__ == '__main__':
    unittest.main()
