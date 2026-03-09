"""오토스케일러 서비스 테스트."""

import unittest
from datetime import datetime, timezone, timedelta
from services.autoscaler_service import (
    ResourceMetrics,
    ScaleDecision,
    evaluate_load,
    decide_scaling,
    calculate_cooldown,
    predict_load,
)


class TestEvaluateLoad(unittest.TestCase):
    """부하 수준 판단 테스트."""

    def test_critical_cpu(self):
        """CPU 90% 이상 → critical."""
        metrics = ResourceMetrics(95.0, 50.0, 10.0, 200.0)
        self.assertEqual(evaluate_load(metrics), "critical")

    def test_critical_memory(self):
        """메모리 95% 이상 → critical."""
        metrics = ResourceMetrics(50.0, 96.0, 10.0, 200.0)
        self.assertEqual(evaluate_load(metrics), "critical")

    def test_high_cpu(self):
        """CPU 80% 이상 → high."""
        metrics = ResourceMetrics(85.0, 50.0, 10.0, 200.0)
        self.assertEqual(evaluate_load(metrics), "high")

    def test_high_memory(self):
        """메모리 85% 이상 → high."""
        metrics = ResourceMetrics(50.0, 88.0, 10.0, 200.0)
        self.assertEqual(evaluate_load(metrics), "high")

    def test_high_latency(self):
        """지연 1000ms 이상 → high."""
        metrics = ResourceMetrics(50.0, 50.0, 10.0, 1500.0)
        self.assertEqual(evaluate_load(metrics), "high")

    def test_low_load(self):
        """CPU + 메모리 모두 낮음 → low."""
        metrics = ResourceMetrics(10.0, 15.0, 5.0, 100.0)
        self.assertEqual(evaluate_load(metrics), "low")

    def test_normal_load(self):
        """보통 수준 → normal."""
        metrics = ResourceMetrics(50.0, 50.0, 30.0, 300.0)
        self.assertEqual(evaluate_load(metrics), "normal")

    def test_boundary_low(self):
        """경계값 (CPU=20, 메모리=25) → low."""
        metrics = ResourceMetrics(20.0, 25.0, 5.0, 100.0)
        self.assertEqual(evaluate_load(metrics), "low")


class TestDecideScaling(unittest.TestCase):
    """스케일링 결정 테스트."""

    def test_scale_up_critical(self):
        """critical → scale_up (2배)."""
        metrics = ResourceMetrics(95.0, 50.0, 100.0, 500.0)
        decision = decide_scaling(metrics, 2, 1, 10)
        self.assertEqual(decision.action, "scale_up")
        self.assertEqual(decision.target_instances, 4)

    def test_scale_up_high(self):
        """high → scale_up (+1)."""
        metrics = ResourceMetrics(85.0, 50.0, 50.0, 300.0)
        decision = decide_scaling(metrics, 3, 1, 10)
        self.assertEqual(decision.action, "scale_up")
        self.assertEqual(decision.target_instances, 4)

    def test_scale_down_low(self):
        """low → scale_down (-1)."""
        metrics = ResourceMetrics(10.0, 15.0, 5.0, 50.0)
        decision = decide_scaling(metrics, 3, 1, 10)
        self.assertEqual(decision.action, "scale_down")
        self.assertEqual(decision.target_instances, 2)

    def test_maintain_normal(self):
        """normal → maintain."""
        metrics = ResourceMetrics(50.0, 50.0, 30.0, 300.0)
        decision = decide_scaling(metrics, 3, 1, 10)
        self.assertEqual(decision.action, "maintain")
        self.assertEqual(decision.target_instances, 3)

    def test_scale_up_capped_at_max(self):
        """max 제한 초과 불가."""
        metrics = ResourceMetrics(95.0, 50.0, 100.0, 500.0)
        decision = decide_scaling(metrics, 8, 1, 10)
        self.assertLessEqual(decision.target_instances, 10)

    def test_scale_down_capped_at_min(self):
        """min 미만으로 감소 불가."""
        metrics = ResourceMetrics(10.0, 15.0, 5.0, 50.0)
        decision = decide_scaling(metrics, 1, 1, 10)
        self.assertEqual(decision.action, "maintain")
        self.assertEqual(decision.target_instances, 1)

    def test_decision_has_reason(self):
        """결정에 사유 포함."""
        metrics = ResourceMetrics(85.0, 50.0, 50.0, 300.0)
        decision = decide_scaling(metrics, 2, 1, 10)
        self.assertTrue(len(decision.reason) > 0)

    def test_critical_at_max_maintain(self):
        """critical이지만 이미 max → maintain."""
        metrics = ResourceMetrics(95.0, 96.0, 200.0, 2000.0)
        decision = decide_scaling(metrics, 10, 1, 10)
        self.assertEqual(decision.action, "maintain")


class TestCalculateCooldown(unittest.TestCase):
    """쿨다운 체크 테스트."""

    def test_cooldown_active(self):
        """최근 스케일링 → 쿨다운 중."""
        now = datetime.now(timezone.utc)
        last_time = (now - timedelta(seconds=30)).isoformat()
        result = calculate_cooldown(last_time, 60)
        self.assertTrue(result)

    def test_cooldown_expired(self):
        """오래된 스케일링 → 쿨다운 해제."""
        now = datetime.now(timezone.utc)
        last_time = (now - timedelta(seconds=120)).isoformat()
        result = calculate_cooldown(last_time, 60)
        self.assertFalse(result)

    def test_cooldown_empty_time(self):
        """이력 없음 → 쿨다운 아님."""
        result = calculate_cooldown("", 60)
        self.assertFalse(result)

    def test_cooldown_invalid_time(self):
        """잘못된 시간 → 쿨다운 아님."""
        result = calculate_cooldown("not-a-date", 60)
        self.assertFalse(result)


class TestPredictLoad(unittest.TestCase):
    """부하 추세 예측 테스트."""

    def test_predict_increasing(self):
        """CPU 증가 추세."""
        history = [
            ResourceMetrics(20.0, 50.0, 10.0, 100.0),
            ResourceMetrics(25.0, 50.0, 10.0, 100.0),
            ResourceMetrics(50.0, 50.0, 10.0, 100.0),
            ResourceMetrics(70.0, 50.0, 10.0, 100.0),
        ]
        self.assertEqual(predict_load(history), "increasing")

    def test_predict_decreasing(self):
        """CPU 감소 추세."""
        history = [
            ResourceMetrics(80.0, 50.0, 10.0, 100.0),
            ResourceMetrics(75.0, 50.0, 10.0, 100.0),
            ResourceMetrics(40.0, 50.0, 10.0, 100.0),
            ResourceMetrics(20.0, 50.0, 10.0, 100.0),
        ]
        self.assertEqual(predict_load(history), "decreasing")

    def test_predict_stable(self):
        """CPU 안정적."""
        history = [
            ResourceMetrics(50.0, 50.0, 10.0, 100.0),
            ResourceMetrics(52.0, 50.0, 10.0, 100.0),
            ResourceMetrics(48.0, 50.0, 10.0, 100.0),
            ResourceMetrics(51.0, 50.0, 10.0, 100.0),
        ]
        self.assertEqual(predict_load(history), "stable")

    def test_predict_too_few_points(self):
        """데이터 부족 → stable."""
        history = [ResourceMetrics(50.0, 50.0, 10.0, 100.0)]
        self.assertEqual(predict_load(history), "stable")

    def test_predict_empty(self):
        """빈 이력 → stable."""
        self.assertEqual(predict_load([]), "stable")


if __name__ == "__main__":
    unittest.main()
