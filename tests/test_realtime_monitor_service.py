"""
RealtimeMonitorService 단위 테스트 (F6-15)
"""
import unittest
from services.analytics.realtime_monitor_service import RealtimeMonitorService


class TestRealtimeMonitorService(unittest.TestCase):

    def setUp(self):
        self.svc = RealtimeMonitorService()

    def test_initial_state(self):
        status = self.svc.get_status()
        self.assertEqual(status['active_generations'], 0)
        self.assertEqual(status['queue_depth'], 0)
        self.assertEqual(status['total_requests'], 0)
        self.assertEqual(status['error_rate_pct'], 0.0)

    def test_generation_lifecycle(self):
        self.svc.on_generation_start()
        self.svc.on_generation_start()
        status = self.svc.get_status()
        self.assertEqual(status['active_generations'], 2)
        self.assertEqual(status['total_requests'], 2)

        self.svc.on_generation_end(success=True)
        status = self.svc.get_status()
        self.assertEqual(status['active_generations'], 1)

    def test_error_tracking(self):
        self.svc.on_generation_start()
        self.svc.on_generation_end(success=False, error_msg='API timeout')
        status = self.svc.get_status()
        self.assertEqual(status['total_errors'], 1)
        self.assertEqual(status['error_rate_pct'], 100.0)

    def test_mixed_error_rate(self):
        for _ in range(8):
            self.svc.on_generation_start()
            self.svc.on_generation_end(success=True)
        for _ in range(2):
            self.svc.on_generation_start()
            self.svc.on_generation_end(success=False)
        status = self.svc.get_status()
        self.assertAlmostEqual(status['error_rate_pct'], 20.0, places=1)

    def test_queue_depth(self):
        self.svc.set_queue_depth(5)
        status = self.svc.get_status()
        self.assertEqual(status['queue_depth'], 5)

    def test_queue_depth_non_negative(self):
        self.svc.set_queue_depth(-1)
        status = self.svc.get_status()
        self.assertEqual(status['queue_depth'], 0)

    def test_recent_errors(self):
        self.svc.on_generation_start()
        self.svc.on_generation_end(success=False, error_msg='에러 1')
        errors = self.svc.get_recent_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], '에러 1')

    def test_reset_counters(self):
        self.svc.on_generation_start()
        self.svc.on_generation_end(success=True)
        self.svc.reset_counters()
        status = self.svc.get_status()
        self.assertEqual(status['total_requests'], 0)
        self.assertEqual(status['total_errors'], 0)

    def test_active_count_floor_zero(self):
        self.svc.on_generation_end(success=True)  # 시작 없이 종료
        status = self.svc.get_status()
        self.assertEqual(status['active_generations'], 0)


if __name__ == '__main__':
    unittest.main()
