"""
콘텐츠 운영 관제 대시보드 서비스 단위 테스트
"""
import unittest
from services.content_ops_dashboard_service import (
    get_ops_dashboard,
    OpsDashboard,
    _compute_token_cost,
    _compute_avg_latency,
    _compute_failure_rate,
    _compute_quality_score,
    _generate_alerts,
)


class TestContentOpsDashboardService(unittest.TestCase):
    """get_ops_dashboard 함수 단위 테스트"""

    def test_basic_dashboard(self):
        """기본 대시보드 생성"""
        data = {
            "total_cost": 5.50,
            "avg_latency_ms": 3000,
            "total_requests": 100,
            "failed_requests": 3,
            "quality_score": 75.0,
            "active_pipelines": 2,
        }
        result = get_ops_dashboard(data)
        self.assertIsInstance(result, OpsDashboard)
        self.assertAlmostEqual(result.token_cost, 5.50, places=2)
        self.assertEqual(result.avg_latency_ms, 3000)
        self.assertAlmostEqual(result.failure_rate, 0.03, places=2)
        self.assertEqual(result.quality_score, 75.0)
        self.assertEqual(result.active_pipelines, 2)

    def test_empty_data(self):
        """빈 데이터"""
        result = get_ops_dashboard({})
        self.assertEqual(result.token_cost, 0.0)
        self.assertIn("운영 데이터 없음", result.alerts)

    def test_none_data(self):
        """None 데이터"""
        result = get_ops_dashboard(None)
        self.assertIn("운영 데이터 없음", result.alerts)

    def test_token_cost_from_tokens(self):
        """토큰 수 기반 비용 계산"""
        data = {
            "input_tokens": 10000,
            "output_tokens": 5000,
            "input_price_per_1k": 0.01,
            "output_price_per_1k": 0.03,
        }
        cost = _compute_token_cost(data)
        # (10000/1000 * 0.01) + (5000/1000 * 0.03) = 0.1 + 0.15 = 0.25
        self.assertAlmostEqual(cost, 0.25, places=4)

    def test_token_cost_direct(self):
        """직접 비용 우선"""
        data = {"total_cost": 3.14, "input_tokens": 99999}
        cost = _compute_token_cost(data)
        self.assertAlmostEqual(cost, 3.14, places=2)

    def test_avg_latency_from_list(self):
        """지연시간 리스트에서 평균 계산"""
        data = {"latencies_ms": [1000, 2000, 3000, 4000]}
        latency = _compute_avg_latency(data)
        self.assertAlmostEqual(latency, 2500.0, places=1)

    def test_avg_latency_direct(self):
        """직접 지연시간 값"""
        data = {"avg_latency_ms": 4500}
        self.assertEqual(_compute_avg_latency(data), 4500.0)

    def test_avg_latency_empty(self):
        """빈 지연시간 데이터"""
        self.assertEqual(_compute_avg_latency({}), 0.0)

    def test_failure_rate_calculation(self):
        """실패율 계산"""
        data = {"total_requests": 200, "failed_requests": 10}
        rate = _compute_failure_rate(data)
        self.assertAlmostEqual(rate, 0.05, places=4)

    def test_failure_rate_zero_requests(self):
        """요청 0건"""
        data = {"total_requests": 0, "failed_requests": 0}
        self.assertEqual(_compute_failure_rate(data), 0.0)

    def test_failure_rate_clamped(self):
        """실패율 1.0 초과 클램핑"""
        data = {"failure_rate": 1.5}
        self.assertEqual(_compute_failure_rate(data), 1.0)

    def test_quality_score_from_list(self):
        """품질 점수 리스트 평균"""
        data = {"quality_scores": [80, 90, 70]}
        score = _compute_quality_score(data)
        self.assertAlmostEqual(score, 80.0, places=1)

    def test_quality_score_clamped(self):
        """품질 점수 범위 클램핑"""
        self.assertEqual(_compute_quality_score({"quality_score": 150}), 100.0)
        self.assertEqual(_compute_quality_score({"quality_score": -10}), 0.0)

    def test_alerts_failure_critical(self):
        """실패율 위험 알림"""
        alerts = _generate_alerts(0, 0, 0.20, 80, 0)
        self.assertTrue(any("[위험]" in a and "실패율" in a for a in alerts))

    def test_alerts_failure_warning(self):
        """실패율 경고 알림"""
        alerts = _generate_alerts(0, 0, 0.08, 80, 0)
        self.assertTrue(any("[경고]" in a and "실패율" in a for a in alerts))

    def test_alerts_latency_critical(self):
        """지연 위험 알림"""
        alerts = _generate_alerts(0, 20000, 0, 80, 0)
        self.assertTrue(any("[위험]" in a and "응답" in a for a in alerts))

    def test_alerts_cost_warning(self):
        """비용 경고 알림"""
        alerts = _generate_alerts(15.0, 0, 0, 80, 0)
        self.assertTrue(any("[경고]" in a and "비용" in a for a in alerts))

    def test_alerts_quality_warning(self):
        """품질 경고 알림"""
        alerts = _generate_alerts(0, 0, 0, 30, 0)
        self.assertTrue(any("[경고]" in a and "품질" in a for a in alerts))

    def test_alerts_pipeline_warning(self):
        """파이프라인 경고 알림"""
        alerts = _generate_alerts(0, 0, 0, 80, 15)
        self.assertTrue(any("[주의]" in a and "파이프라인" in a for a in alerts))

    def test_no_alerts_healthy(self):
        """정상 지표 — 알림 없음"""
        alerts = _generate_alerts(1.0, 2000, 0.01, 85, 3)
        self.assertEqual(len(alerts), 0)

    def test_full_dashboard_with_alerts(self):
        """알림 포함 전체 대시보드"""
        data = {
            "total_cost": 20.0,
            "avg_latency_ms": 18000,
            "total_requests": 100,
            "failed_requests": 20,
            "quality_score": 30.0,
            "active_pipelines": 12,
        }
        result = get_ops_dashboard(data)
        self.assertTrue(len(result.alerts) >= 3)


if __name__ == '__main__':
    unittest.main()
