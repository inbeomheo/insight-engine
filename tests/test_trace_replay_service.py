"""
트레이스 리플레이 서비스 테스트
"""

import unittest
import time

from services.trace_replay_service import (
    TraceReplayService,
    TraceRecord,
    TraceStep,
    TraceSummary,
)


class TestRecordTrace(unittest.TestCase):
    """record_trace 테스트"""

    def setUp(self):
        self.svc = TraceReplayService()
        self.sample_steps = [
            {
                "step_name": "extract",
                "start_time": 1000.0,
                "end_time": 1002.0,
                "tokens_used": 500,
                "cost": 0.01,
                "model": "gemini-flash",
                "status": "success",
            },
            {
                "step_name": "generate",
                "start_time": 1002.0,
                "end_time": 1005.0,
                "tokens_used": 1500,
                "cost": 0.03,
                "model": "gemini-flash",
                "status": "success",
            },
        ]

    def test_기본_트레이스_기록(self):
        """트레이스가 올바르게 기록되어야 한다"""
        record = self.svc.record_trace("run_1", self.sample_steps)
        self.assertIsInstance(record, TraceRecord)
        self.assertTrue(record.trace_id.startswith("trace_"))
        self.assertEqual(record.pipeline_run_id, "run_1")
        self.assertEqual(len(record.steps), 2)

    def test_합계_계산(self):
        """total_cost, total_tokens, total_latency_ms 자동 계산"""
        record = self.svc.record_trace("run_1", self.sample_steps)
        self.assertAlmostEqual(record.total_cost, 0.04)
        self.assertEqual(record.total_tokens, 2000)
        # (2000ms + 3000ms) = 5000ms
        self.assertAlmostEqual(record.total_latency_ms, 5000.0)

    def test_빈_pipeline_run_id_거부(self):
        """빈 pipeline_run_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.record_trace("", self.sample_steps)

    def test_공백_pipeline_run_id_거부(self):
        """공백만 있는 pipeline_run_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.record_trace("   ", self.sample_steps)

    def test_빈_steps_거부(self):
        """빈 steps 리스트는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.record_trace("run_1", [])

    def test_에러_단계_포함(self):
        """error 상태 단계도 기록 가능"""
        steps = [
            {
                "step_name": "failing_step",
                "start_time": 1000.0,
                "end_time": 1001.0,
                "tokens_used": 100,
                "cost": 0.005,
                "model": "gemini-flash",
                "status": "error",
                "error_message": "API timeout",
            }
        ]
        record = self.svc.record_trace("run_err", steps)
        self.assertEqual(record.steps[0].status, "error")
        self.assertEqual(record.steps[0].error_message, "API timeout")

    def test_기본값_적용(self):
        """dict에 누락된 필드는 기본값 적용"""
        steps = [{"step_name": "minimal"}]
        record = self.svc.record_trace("run_min", steps)
        step = record.steps[0]
        self.assertEqual(step.tokens_used, 0)
        self.assertEqual(step.cost, 0.0)
        self.assertEqual(step.model, "unknown")
        self.assertEqual(step.status, "success")
        self.assertIsNone(step.error_message)

    def test_고유_trace_id(self):
        """각 트레이스는 고유 ID"""
        r1 = self.svc.record_trace("run_1", self.sample_steps)
        r2 = self.svc.record_trace("run_2", self.sample_steps)
        self.assertNotEqual(r1.trace_id, r2.trace_id)


class TestReplayTrace(unittest.TestCase):
    """replay_trace 테스트"""

    def setUp(self):
        self.svc = TraceReplayService()

    def test_시간순_재생(self):
        """start_time 기준으로 정렬된 단계 반환"""
        steps = [
            {
                "step_name": "second",
                "start_time": 2000.0,
                "end_time": 2001.0,
                "tokens_used": 100,
                "cost": 0.01,
                "model": "m",
            },
            {
                "step_name": "first",
                "start_time": 1000.0,
                "end_time": 1001.0,
                "tokens_used": 100,
                "cost": 0.01,
                "model": "m",
            },
        ]
        record = self.svc.record_trace("run_1", steps)
        replayed = self.svc.replay_trace(record.trace_id)
        self.assertEqual(len(replayed), 2)
        self.assertEqual(replayed[0].step_name, "first")
        self.assertEqual(replayed[1].step_name, "second")

    def test_존재하지_않는_트레이스(self):
        """없는 trace_id는 KeyError"""
        with self.assertRaises(KeyError):
            self.svc.replay_trace("nonexistent")

    def test_TraceStep_반환(self):
        """반환값이 TraceStep 리스트"""
        steps = [
            {
                "step_name": "only",
                "start_time": 100.0,
                "end_time": 101.0,
                "tokens_used": 50,
                "cost": 0.001,
                "model": "m",
            }
        ]
        record = self.svc.record_trace("run_1", steps)
        replayed = self.svc.replay_trace(record.trace_id)
        self.assertIsInstance(replayed[0], TraceStep)


class TestGetTraceSummary(unittest.TestCase):
    """get_trace_summary 테스트"""

    def setUp(self):
        self.svc = TraceReplayService()

    def test_요약_통계(self):
        """step_count, total_cost, total_tokens, avg_latency_ms, success_rate"""
        steps = [
            {
                "step_name": "a",
                "start_time": 1000.0,
                "end_time": 1002.0,
                "tokens_used": 500,
                "cost": 0.01,
                "model": "m",
                "status": "success",
            },
            {
                "step_name": "b",
                "start_time": 1002.0,
                "end_time": 1005.0,
                "tokens_used": 1500,
                "cost": 0.03,
                "model": "m",
                "status": "success",
            },
        ]
        record = self.svc.record_trace("run_1", steps)
        summary = self.svc.get_trace_summary(record.trace_id)
        self.assertIsInstance(summary, TraceSummary)
        self.assertEqual(summary.trace_id, record.trace_id)
        self.assertEqual(summary.step_count, 2)
        self.assertAlmostEqual(summary.total_cost, 0.04)
        self.assertEqual(summary.total_tokens, 2000)
        # avg: 5000ms / 2 = 2500ms
        self.assertAlmostEqual(summary.avg_latency_ms, 2500.0)
        self.assertAlmostEqual(summary.success_rate, 1.0)

    def test_부분_실패_성공률(self):
        """에러가 있으면 성공률 < 1.0"""
        steps = [
            {
                "step_name": "ok",
                "start_time": 0,
                "end_time": 1,
                "tokens_used": 100,
                "cost": 0.01,
                "model": "m",
                "status": "success",
            },
            {
                "step_name": "fail",
                "start_time": 1,
                "end_time": 2,
                "tokens_used": 50,
                "cost": 0.005,
                "model": "m",
                "status": "error",
                "error_message": "timeout",
            },
        ]
        record = self.svc.record_trace("run_fail", steps)
        summary = self.svc.get_trace_summary(record.trace_id)
        self.assertAlmostEqual(summary.success_rate, 0.5)

    def test_존재하지_않는_트레이스(self):
        """없는 trace_id는 KeyError"""
        with self.assertRaises(KeyError):
            self.svc.get_trace_summary("nonexistent")

    def test_전체_실패(self):
        """모든 단계 에러 시 success_rate=0.0"""
        steps = [
            {
                "step_name": "fail1",
                "start_time": 0,
                "end_time": 1,
                "tokens_used": 0,
                "cost": 0.0,
                "model": "m",
                "status": "error",
            },
            {
                "step_name": "fail2",
                "start_time": 1,
                "end_time": 2,
                "tokens_used": 0,
                "cost": 0.0,
                "model": "m",
                "status": "error",
            },
        ]
        record = self.svc.record_trace("run_all_fail", steps)
        summary = self.svc.get_trace_summary(record.trace_id)
        self.assertAlmostEqual(summary.success_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
