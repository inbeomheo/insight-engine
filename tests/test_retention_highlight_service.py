"""
유지율 기반 하이라이트 서비스 테스트
"""
import pytest
from services.retention_highlight_service import (
    highlight_by_retention,
    RetentionHighlight,
    TYPE_PEAK,
    TYPE_RECOVERY,
    TYPE_STEADY,
    _normalize_rate,
    _format_timestamp,
    _parse_timestamp,
)


class TestNormalizeRate:
    """유지율 정규화 테스트."""

    def test_percentage_to_ratio(self):
        assert _normalize_rate(85.0) == 0.85

    def test_already_ratio(self):
        assert _normalize_rate(0.85) == 0.85

    def test_clamp_high(self):
        assert _normalize_rate(1.0) == 1.0

    def test_clamp_low(self):
        assert _normalize_rate(-0.5) == 0.0


class TestTimestampHelpers:
    """타임스탬프 유틸리티 테스트."""

    def test_format(self):
        assert _format_timestamp(90) == "01:30"

    def test_parse_mm_ss(self):
        assert _parse_timestamp("02:30") == 150

    def test_parse_hh_mm_ss(self):
        assert _parse_timestamp("01:00:00") == 3600


class TestHighlightByRetention:
    """highlight_by_retention 통합 테스트."""

    def test_empty_raises(self):
        """빈 데이터는 ValueError."""
        with pytest.raises(ValueError, match="비어있습니다"):
            highlight_by_retention([])

    def test_peak_detection(self):
        """유지율 최고점 감지."""
        data = [
            {"retention_rate": 0.50},
            {"retention_rate": 0.55},
            {"retention_rate": 0.95},  # 피크
            {"retention_rate": 0.93},  # 피크
            {"retention_rate": 0.50},
            {"retention_rate": 0.45},
            {"retention_rate": 0.40},
            {"retention_rate": 0.35},
        ]
        result = highlight_by_retention(data)

        peaks = [h for h in result if h.highlight_type == TYPE_PEAK]
        assert len(peaks) >= 1
        assert peaks[0].retention_rate >= 0.9

    def test_recovery_detection(self):
        """이탈 후 회복 구간 감지."""
        data = [
            {"retention_rate": 0.80, "timestamp": "00:00"},
            {"retention_rate": 0.65, "timestamp": "00:10"},  # 15% 하락
            {"retention_rate": 0.60, "timestamp": "00:20"},
            {"retention_rate": 0.75, "timestamp": "00:30"},  # 회복
            {"retention_rate": 0.80, "timestamp": "00:40"},
        ]
        result = highlight_by_retention(data)

        recoveries = [h for h in result if h.highlight_type == TYPE_RECOVERY]
        assert len(recoveries) >= 1

    def test_steady_detection(self):
        """안정적 유지 구간 감지."""
        data = [
            {"retention_rate": 0.70, "timestamp": "00:00"},
            {"retention_rate": 0.71, "timestamp": "00:10"},
            {"retention_rate": 0.70, "timestamp": "00:20"},
            {"retention_rate": 0.72, "timestamp": "00:30"},
            {"retention_rate": 0.71, "timestamp": "00:40"},
        ]
        result = highlight_by_retention(data)

        steadies = [h for h in result if h.highlight_type == TYPE_STEADY]
        assert len(steadies) >= 1

    def test_percentage_input(self):
        """0~100 범위 입력도 정상 처리."""
        data = [
            {"retention_rate": 90},
            {"retention_rate": 92},
            {"retention_rate": 88},
            {"retention_rate": 91},
        ]
        result = highlight_by_retention(data)
        # 에러 없이 처리됨
        assert isinstance(result, list)

    def test_sorted_by_timestamp(self):
        """결과가 시간순 정렬."""
        data = [
            {"retention_rate": 0.95, "timestamp": "02:00"},
            {"retention_rate": 0.50, "timestamp": "00:00"},
            {"retention_rate": 0.55, "timestamp": "00:10"},
            {"retention_rate": 0.50, "timestamp": "00:20"},
            {"retention_rate": 0.50, "timestamp": "00:30"},
            {"retention_rate": 0.50, "timestamp": "00:40"},
            {"retention_rate": 0.50, "timestamp": "01:00"},
            {"retention_rate": 0.50, "timestamp": "01:30"},
        ]
        result = highlight_by_retention(data)

        if len(result) >= 2:
            timestamps_sec = [_parse_timestamp(h.timestamp) for h in result]
            assert timestamps_sec == sorted(timestamps_sec)

    def test_highlight_has_description(self):
        """모든 하이라이트에 설명이 포함됨."""
        data = [
            {"retention_rate": 0.90},
            {"retention_rate": 0.92},
            {"retention_rate": 0.30},
            {"retention_rate": 0.80},
        ]
        result = highlight_by_retention(data)

        for h in result:
            assert h.description
            assert len(h.description) > 0

    def test_rate_field_alias(self):
        """'rate' 필드명도 지원."""
        data = [
            {"rate": 0.90},
            {"rate": 0.92},
            {"rate": 0.50},
            {"rate": 0.45},
        ]
        result = highlight_by_retention(data)
        assert isinstance(result, list)

    def test_duration_positive(self):
        """하이라이트 구간 길이가 양수."""
        data = [
            {"retention_rate": 0.95, "timestamp": "00:00"},
            {"retention_rate": 0.93, "timestamp": "00:10"},
            {"retention_rate": 0.40, "timestamp": "00:20"},
            {"retention_rate": 0.30, "timestamp": "00:30"},
        ]
        result = highlight_by_retention(data)

        for h in result:
            assert h.duration_seconds > 0
