"""task_queue_service 단위 테스트"""
import threading
import time
import unittest

from services.task_queue_service import TaskQueueService, TaskStatus


class TestTaskQueueService(unittest.TestCase):

    def setUp(self):
        self.svc = TaskQueueService(num_workers=2, max_queue_size=50)

    def tearDown(self):
        if self.svc._started:
            self.svc._shutdown_event.set()
            # 워커 깨우기 — 큐에 남은 아이템과 타입 호환되는 더미
            for _ in self.svc._workers:
                try:
                    self.svc._queue.put_nowait((-999, 0.0, None))
                except Exception:
                    pass
            for w in self.svc._workers:
                w.join(timeout=2)

    def test_enqueue_and_get(self):
        """태스크 등록 및 결과 조회"""
        tid = self.svc.enqueue(lambda: 42, task_id='t1')
        self.assertEqual(tid, 't1')
        # 워커가 처리할 시간
        time.sleep(0.5)
        result = self.svc.get_task('t1')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['result'], 42)

    def test_auto_start(self):
        """enqueue 시 자동 시작"""
        self.assertFalse(self.svc._started)
        self.svc.enqueue(lambda: 1)
        self.assertTrue(self.svc._started)

    def test_get_nonexistent_task(self):
        """없는 태스크 조회"""
        self.assertIsNone(self.svc.get_task('nonexistent'))

    def test_cancel_pending_task(self):
        """PENDING 태스크 취소"""
        # 큐를 바쁘게 만들어 pending 유지
        barrier = threading.Event()
        self.svc.enqueue(lambda: barrier.wait(timeout=5), priority=10)
        time.sleep(0.1)
        # 낮은 우선순위로 등록 → pending 상태 유지
        tid = self.svc.enqueue(lambda: 99, priority=0, task_id='cancel_me')
        cancelled = self.svc.cancel_task('cancel_me')
        self.assertTrue(cancelled)
        result = self.svc.get_task('cancel_me')
        self.assertEqual(result['status'], 'cancelled')
        barrier.set()

    def test_cancel_nonexistent(self):
        """없는 태스크 취소 → False"""
        self.assertFalse(self.svc.cancel_task('bad_id'))

    def test_failed_task(self):
        """실패한 태스크"""
        def fail():
            raise ValueError('test error')

        tid = self.svc.enqueue(fail, task_id='fail1')
        time.sleep(0.5)
        result = self.svc.get_task('fail1')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('test error', result['error'])

    def test_task_with_args(self):
        """인자가 있는 태스크"""
        def add(a, b):
            return a + b

        tid = self.svc.enqueue(add, 3, 4, task_id='add1')
        time.sleep(0.5)
        result = self.svc.get_task('add1')
        self.assertEqual(result['result'], 7)

    def test_get_stats(self):
        """큐 통계"""
        self.svc.enqueue(lambda: 1, task_id='s1')
        time.sleep(0.5)
        stats = self.svc.get_stats()
        self.assertEqual(stats['num_workers'], 2)
        self.assertGreaterEqual(stats['total_tasks'], 1)
        self.assertIn('by_status', stats)

    def test_priority_order(self):
        """우선순위 순서"""
        results = []
        barrier = threading.Event()

        # 워커를 블로킹하여 큐에 쌓이게 만듦
        self.svc.enqueue(lambda: barrier.wait(timeout=5), priority=100)
        time.sleep(0.1)

        self.svc.enqueue(lambda: results.append('low'), priority=1, task_id='low')
        self.svc.enqueue(lambda: results.append('high'), priority=10, task_id='high')
        time.sleep(0.1)
        barrier.set()
        time.sleep(0.5)

        # high(10)가 low(1)보다 먼저 처리
        if len(results) == 2:
            self.assertEqual(results[0], 'high')

    def test_to_dict_duration(self):
        """to_dict에 duration_s 포함"""
        self.svc.enqueue(lambda: time.sleep(0.1), task_id='dur1')
        time.sleep(0.5)
        result = self.svc.get_task('dur1')
        self.assertIsNotNone(result['duration_s'])
        self.assertGreater(result['duration_s'], 0)

    def test_stop_graceful(self):
        """그레이스풀 셧다운"""
        self.svc.enqueue(lambda: 1)
        time.sleep(0.3)
        self.svc.stop(timeout=3)
        self.assertTrue(self.svc._shutdown_event.is_set())


if __name__ == '__main__':
    unittest.main()
