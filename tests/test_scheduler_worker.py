"""scheduler_worker 단위 테스트 — check_and_publish, start/stop_scheduler"""
import unittest
from unittest.mock import patch, MagicMock


class TestCheckAndPublish(unittest.TestCase):
    """check_and_publish: 예약 포스트 확인 — 발행 플러그인 제거(Dep-5) 후 실패 처리"""

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    def test_no_due_posts(self, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = []
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_schedule.update_status.assert_not_called()

    @patch('services.data.scheduler_worker.logger')
    @patch('services.data.schedule_service.schedule_service')
    def test_due_posts_marked_failed(self, mock_schedule, mock_logger):
        mock_schedule.get_due_posts.return_value = [
            {'id': 'p1', 'target_plugin': 'naver', 'content': 'body', 'title': 'title'}
        ]
        from services.data.scheduler_worker import check_and_publish
        check_and_publish()
        mock_schedule.update_status.assert_called_once_with(
            'p1', 'failed', error_message='발행 기능이 종료되었습니다.'
        )


class TestStartSchedulerLeaderLock(unittest.TestCase):
    """start_scheduler: gunicorn worker별 중복 스케줄러 방지"""

    @patch.dict('os.environ', {'SCHEDULER_ENABLED': 'true'}, clear=False)
    def test_start_scheduler_skips_when_another_worker_holds_leader_lock(self):
        from services.data import scheduler_worker

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_app = MagicMock()

        with patch.object(scheduler_worker, '_get_scheduler', return_value=mock_scheduler), \
             patch.object(scheduler_worker, '_acquire_scheduler_leader_lock', return_value=False, create=True), \
             patch.object(scheduler_worker.logger, 'info') as mock_info:
            scheduler_worker.start_scheduler(mock_app)

        mock_scheduler.add_job.assert_not_called()
        mock_scheduler.start.assert_not_called()
        mock_info.assert_any_call('다른 worker가 스케줄러 리더락을 보유 중 — 스케줄러 기동 생략')


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
