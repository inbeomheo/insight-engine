"""
이탈 구간 리컷 시뮬레이션 서비스 테스트
"""
import pytest
from services.dropout_recut_service import (
    simulate_recut,
    RecutPlan,
    RemovedSegment,
    _parse_timestamp,
    _format_timestamp,
    _normalize_rate,
    _classify_reason,
)


class TestHelpers:
    """헬퍼 함수 테스트."""

    def test_parse_mm_ss(self):
        assert _parse_timestamp("02:30") == 150

    def test_parse_hh_mm_ss(self):
        assert _parse_timestamp("01:00:00") == 3600

    def test_format_timestamp(self):
        assert _format_timestamp(150) == "02:30"

    def test_normalize_percentage(self):
        assert _normalize_rate(25.0) == 0.25

    def test_normalize_ratio(self):
        assert _normalize_rate(0.25) == 0.25

    def test_classify_severe(self):
        reason = _classify_reason(0.30)
        assert "심각한" in reason

    def test_classify_high(self):
        reason = _classify_reason(0.18)
        assert "높은" in reason


class TestSimulateRecut:
    """simulate_recut 통합 테스트."""

    def test_empty_raises(self):
        """빈 데이터는 ValueError."""
        with pytest.raises(ValueError, match="비어있습니다"):
            simulate_recut([])

    def test_basic_removal(self):
        """이탈률 높은 구간이 제거됨."""
        data = [
            {"timestamp": "00:00", "end": "00:30", "dropout_rate": 0.05},
            {"timestamp": "00:30", "end": "01:00", "dropout_rate": 0.25},  # 제거 대상
            {"timestamp": "01:00", "end": "01:30", "dropout_rate": 0.03},
            {"timestamp": "01:30", "end": "02:00", "dropout_rate": 0.20},  # 제거 대상
        ]
        result = simulate_recut(data)

        assert isinstance(result, RecutPlan)
        assert len(result.removed_segments) >= 1
        assert result.recut_length < result.original_length

    def test_no_removal_low_dropout(self):
        """이탈률이 전부 낮으면 제거 구간 없음."""
        data = [
            {"timestamp": "00:00", "end": "00:30", "dropout_rate": 0.05},
            {"timestamp": "00:30", "end": "01:00", "dropout_rate": 0.08},
            {"timestamp": "01:00", "end": "01:30", "dropout_rate": 0.03},
        ]
        result = simulate_recut(data)

        assert len(result.removed_segments) == 0
        assert result.recut_length == result.original_length

    def test_max_removal_ratio(self):
        """전체 40% 이상 제거 제한."""
        # 모든 구간이 높은 이탈률 — 40%만 제거되어야 함
        data = [
            {"timestamp": "00:00", "end": "00:30", "dropout_rate": 0.30},
            {"timestamp": "00:30", "end": "01:00", "dropout_rate": 0.30},
            {"timestamp": "01:00", "end": "01:30", "dropout_rate": 0.30},
            {"timestamp": "01:30", "end": "02:00", "dropout_rate": 0.30},
        ]
        result = simulate_recut(data)

        total_removed = sum(s.duration_seconds for s in result.removed_segments)
        assert total_removed <= result.original_length * 0.40

    def test_recut_length_calculation(self):
        """리컷 길이 = 원본 - 제거."""
        data = [
            {"timestamp": "00:00", "end": "01:00", "dropout_rate": 0.05},
            {"timestamp": "01:00", "end": "02:00", "dropout_rate": 0.25},
        ]
        result = simulate_recut(data)

        total_removed = sum(s.duration_seconds for s in result.removed_segments)
        assert result.recut_length == result.original_length - total_removed

    def test_estimated_improvement_range(self):
        """유지율 개선 예측값이 0~0.30 범위."""
        data = [
            {"timestamp": "00:00", "end": "01:00", "dropout_rate": 0.30},
            {"timestamp": "01:00", "end": "02:00", "dropout_rate": 0.30},
        ]
        result = simulate_recut(data)

        assert 0.0 <= result.estimated_improvement <= 0.30

    def test_rate_field_alias(self):
        """'rate' 필드명도 지원."""
        data = [
            {"timestamp": "00:00", "end": "00:30", "rate": 0.25},
            {"timestamp": "00:30", "end": "01:00", "rate": 0.05},
        ]
        result = simulate_recut(data)
        assert isinstance(result, RecutPlan)

    def test_min_segment_duration(self):
        """5초 미만 구간은 제거 대상에서 제외."""
        data = [
            {"timestamp": "00:00", "end": "00:03", "dropout_rate": 0.30},  # 3초 → 제외
            {"timestamp": "00:03", "end": "00:30", "dropout_rate": 0.05},
        ]
        result = simulate_recut(data)
        assert len(result.removed_segments) == 0

    def test_duration_seconds_field(self):
        """duration_seconds 필드로 구간 끝 결정."""
        data = [
            {"timestamp": "00:00", "duration_seconds": 10, "dropout_rate": 0.25},
            {"timestamp": "00:10", "duration_seconds": 50, "dropout_rate": 0.05},
            {"timestamp": "01:00", "duration_seconds": 60, "dropout_rate": 0.02},
        ]
        result = simulate_recut(data)

        # 첫 구간(10초, 이탈률 25%)이 제거 대상, 전체 120초의 40% = 48초 한도 내
        assert len(result.removed_segments) >= 1
        assert result.removed_segments[0].duration_seconds == 10

    def test_removed_segment_has_reason(self):
        """제거 구간에 사유가 포함됨."""
        data = [
            {"timestamp": "00:00", "end": "00:30", "dropout_rate": 0.30},
        ]
        result = simulate_recut(data)

        for seg in result.removed_segments:
            assert seg.reason
            assert len(seg.reason) > 0
