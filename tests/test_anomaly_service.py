"""
AnomalyService 단위 테스트 (F6-16)
"""
import unittest
from services.analytics.anomaly_service import AnomalyService


class TestAnomalyService(unittest.TestCase):

    def setUp(self):
        self.svc = AnomalyService(z_threshold=2.0)

    def test_no_anomaly_before_baseline(self):
        """기준선 수립 전(10개 미만)에는 이상 탐지 없음"""
        for i in range(9):
            result = self.svc.record_metric('error_rate', float(i))
            self.assertIsNone(result)

    def test_anomaly_detected(self):
        """이상값 주입 후 탐지"""
        baseline = [1.0, 1.1, 0.9, 1.0, 1.0, 1.1, 0.95, 1.0, 1.05, 1.0]
        for v in baseline:
            self.svc.record_metric('latency_ms', v)
        # 극단값 주입
        result = self.svc.record_metric('latency_ms', 100.0)
        self.assertIsNotNone(result)
        self.assertEqual(result['metric'], 'latency_ms')
        self.assertGreater(result['z_score'], 2.0)

    def test_normal_value_not_anomaly(self):
        """정상 범위 값은 이상 아님"""
        for v in [1.0] * 10:
            self.svc.record_metric('score', v)
        result = self.svc.record_metric('score', 1.0)
        self.assertIsNone(result)

    def test_handler_called_on_anomaly(self):
        called = []
        self.svc.add_handler(lambda a: called.append(a))
        for _ in range(10):
            self.svc.record_metric('m', 0.0)
        self.svc.record_metric('m', 100.0)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]['metric'], 'm')

    def test_get_anomalies(self):
        for _ in range(10):
            self.svc.record_metric('x', 0.0)
        self.svc.record_metric('x', 999.0)
        anomalies = self.svc.get_anomalies()
        self.assertEqual(len(anomalies), 1)

    def test_get_baseline(self):
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            self.svc.record_metric('b', v)
        baseline = self.svc.get_baseline('b')
        self.assertEqual(baseline['count'], 5)
        self.assertAlmostEqual(baseline['mean'], 3.0)

    def test_clear_anomalies(self):
        for _ in range(10):
            self.svc.record_metric('c', 0.0)
        self.svc.record_metric('c', 999.0)
        self.svc.clear_anomalies()
        self.assertEqual(len(self.svc.get_anomalies()), 0)


if __name__ == '__main__':
    unittest.main()
