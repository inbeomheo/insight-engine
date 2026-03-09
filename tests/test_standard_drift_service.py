"""
표준 드리프트 감지 서비스 테스트

detect_drift() 함수의 드리프트 계산, 경고 수준,
방향 판별, 엣지 케이스를 검증합니다.
"""
import pytest

from services.standard_drift_service import (
    DriftReport,
    DriftedMetric,
    detect_drift,
)


class TestDetectDrift:
    """detect_drift 핵심 기능 테스트"""

    def test_empty_inputs_returns_normal(self):
        """빈 입력 → normal 상태"""
        result = detect_drift({}, {})
        assert isinstance(result, DriftReport)
        assert result.drifted_metrics == []
        assert result.overall_drift_score == 0.0
        assert result.alert_level == "normal"

    def test_none_inputs(self):
        """None 입력 → normal 상태"""
        result = detect_drift(None, {})
        assert result.alert_level == "normal"
        result2 = detect_drift({}, None)
        assert result2.alert_level == "normal"

    def test_identical_metrics_no_drift(self):
        """동일 메트릭 → 드리프트 없음"""
        metrics = {"views": 100, "clicks": 50, "conversions": 10}
        result = detect_drift(metrics, metrics)
        assert len(result.drifted_metrics) == 0
        assert result.overall_drift_score == 0.0
        assert result.alert_level == "normal"

    def test_small_change_stable(self):
        """작은 변화(1% 미만) → 드리프트 미보고"""
        baseline = {"views": 1000}
        current = {"views": 1005}  # 0.5% 변화
        result = detect_drift(current, baseline)
        assert len(result.drifted_metrics) == 0

    def test_significant_increase_detected(self):
        """유의미한 증가 → 드리프트 감지"""
        baseline = {"views": 100}
        current = {"views": 150}  # 50% 증가
        result = detect_drift(current, baseline)
        assert len(result.drifted_metrics) == 1
        assert result.drifted_metrics[0].metric_name == "views"
        assert result.drifted_metrics[0].direction == "up"
        assert result.drifted_metrics[0].drift_pct == 50.0

    def test_significant_decrease_detected(self):
        """유의미한 감소 → 드리프트 감지"""
        baseline = {"clicks": 200}
        current = {"clicks": 100}  # -50% 감소
        result = detect_drift(current, baseline)
        assert len(result.drifted_metrics) == 1
        assert result.drifted_metrics[0].direction == "down"
        assert result.drifted_metrics[0].drift_pct == -50.0

    def test_multiple_metrics_drift(self):
        """여러 메트릭 동시 드리프트"""
        baseline = {"views": 100, "clicks": 100, "revenue": 100}
        current = {"views": 200, "clicks": 50, "revenue": 100}
        result = detect_drift(current, baseline)
        drifted_names = {m.metric_name for m in result.drifted_metrics}
        assert "views" in drifted_names
        assert "clicks" in drifted_names
        assert "revenue" not in drifted_names  # 변화 없음

    def test_alert_level_warning(self):
        """중간 드리프트 → warning 경고"""
        baseline = {"a": 100, "b": 100}
        current = {"a": 120, "b": 80}  # 20% 변화
        result = detect_drift(current, baseline)
        assert result.alert_level in ("warning", "critical")

    def test_alert_level_critical(self):
        """큰 드리프트 → critical 경고"""
        baseline = {"views": 100, "clicks": 100}
        current = {"views": 200, "clicks": 20}  # 100%, -80%
        result = detect_drift(current, baseline)
        assert result.alert_level == "critical"

    def test_baseline_zero_value(self):
        """기준값 0 → 100% 드리프트 처리"""
        baseline = {"views": 0}
        current = {"views": 50}
        result = detect_drift(current, baseline)
        assert len(result.drifted_metrics) == 1
        assert result.drifted_metrics[0].drift_pct == 100.0

    def test_both_zero_no_drift(self):
        """기준/현재 모두 0 → 드리프트 없음"""
        baseline = {"views": 0}
        current = {"views": 0}
        result = detect_drift(current, baseline)
        assert len(result.drifted_metrics) == 0

    def test_non_overlapping_keys_ignored(self):
        """공통 키만 비교, 나머지 무시"""
        baseline = {"views": 100, "old_metric": 50}
        current = {"views": 120, "new_metric": 30}
        result = detect_drift(current, baseline)
        drifted_names = {m.metric_name for m in result.drifted_metrics}
        assert "old_metric" not in drifted_names
        assert "new_metric" not in drifted_names

    def test_sorted_by_drift_magnitude(self):
        """드리프트 크기 내림차순 정렬"""
        baseline = {"a": 100, "b": 100, "c": 100}
        current = {"a": 110, "b": 150, "c": 200}
        result = detect_drift(current, baseline)
        if len(result.drifted_metrics) >= 2:
            magnitudes = [abs(m.drift_pct) for m in result.drifted_metrics]
            assert magnitudes == sorted(magnitudes, reverse=True)

    def test_invalid_value_skipped(self):
        """숫자로 변환 불가한 값 → 건너뛰기"""
        baseline = {"views": 100, "bad": "not_a_number"}
        current = {"views": 150, "bad": "still_not"}
        result = detect_drift(current, baseline)
        drifted_names = {m.metric_name for m in result.drifted_metrics}
        assert "bad" not in drifted_names

    def test_overall_drift_score_positive(self):
        """전체 드리프트 점수가 0 이상"""
        baseline = {"views": 100}
        current = {"views": 130}
        result = detect_drift(current, baseline)
        assert result.overall_drift_score >= 0

    def test_drifted_metric_dataclass_fields(self):
        """DriftedMetric 필드 타입 검증"""
        baseline = {"views": 100}
        current = {"views": 150}
        result = detect_drift(current, baseline)
        for m in result.drifted_metrics:
            assert isinstance(m.metric_name, str)
            assert isinstance(m.baseline_value, float)
            assert isinstance(m.current_value, float)
            assert isinstance(m.drift_pct, float)
            assert m.direction in ("up", "down", "stable")
