"""컨트롤 타워 서비스 테스트."""

import unittest
from services.control_tower_service import (
    PipelineStatus,
    TowerDashboard,
    register_pipeline,
    update_status,
    get_dashboard,
    generate_alerts,
    _reset_store,
)


class TestRegisterPipeline(unittest.TestCase):
    """파이프라인 등록 테스트."""

    def setUp(self):
        _reset_store()

    def test_register_basic(self):
        """기본 파이프라인 등록."""
        ps = register_pipeline("p1", "테스트 파이프라인")
        self.assertEqual(ps.pipeline_id, "p1")
        self.assertEqual(ps.name, "테스트 파이프라인")
        self.assertEqual(ps.status, "idle")
        self.assertEqual(ps.progress_pct, 0.0)
        self.assertTrue(ps.started_at)

    def test_register_multiple(self):
        """여러 파이프라인 등록."""
        ps1 = register_pipeline("p1", "파이프라인1")
        ps2 = register_pipeline("p2", "파이프라인2")
        self.assertEqual(ps1.pipeline_id, "p1")
        self.assertEqual(ps2.pipeline_id, "p2")


class TestUpdateStatus(unittest.TestCase):
    """상태 업데이트 테스트."""

    def setUp(self):
        _reset_store()

    def test_update_basic(self):
        """기본 상태 업데이트."""
        register_pipeline("p1", "테스트")
        ps = update_status("p1", "running", 50.0)
        self.assertEqual(ps.status, "running")
        self.assertEqual(ps.progress_pct, 50.0)

    def test_update_with_error_count(self):
        """에러 카운트 업데이트."""
        register_pipeline("p1", "테스트")
        ps = update_status("p1", "running", 30.0, error_count=2)
        self.assertEqual(ps.error_count, 2)

    def test_update_unregistered(self):
        """미등록 파이프라인 → KeyError."""
        with self.assertRaises(KeyError):
            update_status("nonexistent", "running", 0.0)

    def test_update_completed(self):
        """완료 상태로 업데이트."""
        register_pipeline("p1", "테스트")
        ps = update_status("p1", "completed", 100.0)
        self.assertEqual(ps.status, "completed")
        self.assertEqual(ps.progress_pct, 100.0)


class TestGetDashboard(unittest.TestCase):
    """대시보드 테스트."""

    def test_dashboard_empty(self):
        """빈 상태 목록."""
        dash = get_dashboard([])
        self.assertEqual(dash.total_pipelines, 0)
        self.assertEqual(dash.active, 0)
        self.assertEqual(dash.avg_progress, 0.0)

    def test_dashboard_counts(self):
        """상태별 카운트."""
        statuses = [
            PipelineStatus("p1", "A", "running", 50.0),
            PipelineStatus("p2", "B", "completed", 100.0),
            PipelineStatus("p3", "C", "failed", 30.0),
            PipelineStatus("p4", "D", "running", 70.0),
        ]
        dash = get_dashboard(statuses)
        self.assertEqual(dash.total_pipelines, 4)
        self.assertEqual(dash.active, 2)
        self.assertEqual(dash.completed, 1)
        self.assertEqual(dash.failed, 1)

    def test_dashboard_avg_progress(self):
        """평균 진행률."""
        statuses = [
            PipelineStatus("p1", "A", "running", 40.0),
            PipelineStatus("p2", "B", "running", 60.0),
        ]
        dash = get_dashboard(statuses)
        self.assertEqual(dash.avg_progress, 50.0)

    def test_dashboard_includes_alerts(self):
        """대시보드에 알림 포함."""
        statuses = [
            PipelineStatus("p1", "A", "failed", 0.0, error_count=5),
        ]
        dash = get_dashboard(statuses)
        self.assertTrue(len(dash.alerts) > 0)


class TestGenerateAlerts(unittest.TestCase):
    """알림 생성 테스트."""

    def test_alerts_empty(self):
        """빈 상태 → 알림 없음."""
        alerts = generate_alerts([])
        self.assertEqual(alerts, [])

    def test_alert_high_failure_rate(self):
        """실패율 30% 초과 경고."""
        statuses = [
            PipelineStatus("p1", "A", "failed", 0.0),
            PipelineStatus("p2", "B", "failed", 0.0),
            PipelineStatus("p3", "C", "completed", 100.0),
        ]
        alerts = generate_alerts(statuses)
        fail_alerts = [a for a in alerts if "실패율" in a]
        self.assertTrue(len(fail_alerts) > 0)

    def test_alert_stalled_pipeline(self):
        """진행 정체 경고 (running + 0%)."""
        statuses = [
            PipelineStatus("p1", "정체됨", "running", 0.0),
        ]
        alerts = generate_alerts(statuses)
        stall_alerts = [a for a in alerts if "정체" in a]
        self.assertTrue(len(stall_alerts) > 0)

    def test_alert_high_error_count(self):
        """에러 3회 이상 경고."""
        statuses = [
            PipelineStatus("p1", "에러다발", "running", 50.0, error_count=5),
        ]
        alerts = generate_alerts(statuses)
        error_alerts = [a for a in alerts if "에러 다발" in a]
        self.assertTrue(len(error_alerts) > 0)

    def test_no_alerts_normal(self):
        """정상 상태 → 알림 없음."""
        statuses = [
            PipelineStatus("p1", "A", "running", 50.0, error_count=0),
            PipelineStatus("p2", "B", "completed", 100.0, error_count=0),
        ]
        alerts = generate_alerts(statuses)
        self.assertEqual(alerts, [])

    def test_alert_multiple_issues(self):
        """복합 이상 징후."""
        statuses = [
            PipelineStatus("p1", "A", "failed", 0.0, error_count=5),
            PipelineStatus("p2", "B", "failed", 0.0, error_count=3),
            PipelineStatus("p3", "정체됨", "running", 0.0),
        ]
        alerts = generate_alerts(statuses)
        # 실패율 + 에러 다발 + 정체 → 다수 알림
        self.assertTrue(len(alerts) >= 3)


if __name__ == "__main__":
    unittest.main()
