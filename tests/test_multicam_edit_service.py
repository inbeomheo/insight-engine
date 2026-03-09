"""
멀티캠 자동 편집 서비스 테스트
"""
import pytest
from services.multicam_edit_service import (
    auto_multicam,
    MulticamEdit,
    StreamInfo,
    CutDecision,
    REASON_SPEAKER_CHANGE,
    REASON_SCENE_CHANGE,
    REASON_PERIODIC,
    _parse_timestamp,
    _format_timestamp,
    _next_stream,
)


class TestParseTimestamp:
    """타임스탬프 파싱 테스트."""

    def test_mm_ss_format(self):
        assert _parse_timestamp("01:30") == 90

    def test_hh_mm_ss_format(self):
        assert _parse_timestamp("01:02:30") == 3750

    def test_zero(self):
        assert _parse_timestamp("00:00") == 0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_timestamp("invalid")


class TestFormatTimestamp:
    """타임스탬프 포맷 테스트."""

    def test_basic(self):
        assert _format_timestamp(90) == "01:30"

    def test_zero(self):
        assert _format_timestamp(0) == "00:00"

    def test_large(self):
        assert _format_timestamp(600) == "10:00"


class TestNextStream:
    """다음 스트림 선택 테스트."""

    def test_round_robin(self):
        streams = [
            StreamInfo("a", "카메라A", 1),
            StreamInfo("b", "카메라B", 2),
            StreamInfo("c", "카메라C", 3),
        ]
        # a → b
        result = _next_stream("a", streams)
        assert result.stream_id == "b"

    def test_wrap_around(self):
        streams = [
            StreamInfo("a", "카메라A", 1),
            StreamInfo("b", "카메라B", 2),
        ]
        # b → a (마지막 → 처음으로 순환)
        result = _next_stream("b", streams)
        assert result.stream_id == "a"

    def test_unknown_id_returns_first(self):
        streams = [
            StreamInfo("a", "카메라A", 1),
            StreamInfo("b", "카메라B", 2),
        ]
        result = _next_stream("unknown", streams)
        assert result.stream_id == "a"


class TestAutoMulticam:
    """auto_multicam 통합 테스트."""

    def test_minimum_two_streams_required(self):
        """2개 미만 스트림은 ValueError."""
        with pytest.raises(ValueError, match="최소 2개"):
            auto_multicam([{"stream_id": "a", "label": "캠1", "priority": 1}])

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            auto_multicam([])

    def test_basic_speaker_change(self):
        """화자 변경 이벤트로 컷 생성."""
        streams = [
            {
                "stream_id": "cam1",
                "label": "메인 카메라",
                "priority": 1,
                "events": [
                    {"type": "speaker_change", "timestamp": "00:30", "speaker": "A"},
                    {"type": "speaker_change", "timestamp": "01:00", "speaker": "B"},
                ],
            },
            {
                "stream_id": "cam2",
                "label": "보조 카메라",
                "priority": 2,
                "events": [],
            },
        ]
        result = auto_multicam(streams)

        assert isinstance(result, MulticamEdit)
        assert len(result.streams) == 2
        assert result.total_cuts == len(result.cuts)
        assert result.total_cuts >= 2
        # 첫 번째 컷은 화자 변경
        assert result.cuts[0].reason == REASON_SPEAKER_CHANGE

    def test_scene_change_cuts(self):
        """장면 전환 이벤트로 컷 생성."""
        streams = [
            {
                "stream_id": "a",
                "label": "A",
                "priority": 1,
                "events": [
                    {"type": "scene_change", "timestamp": "00:20"},
                ],
            },
            {
                "stream_id": "b",
                "label": "B",
                "priority": 2,
                "events": [],
            },
        ]
        result = auto_multicam(streams)

        assert result.total_cuts >= 1
        assert any(c.reason == REASON_SCENE_CHANGE for c in result.cuts)

    def test_no_events_periodic_cuts(self):
        """이벤트 없으면 주기적 전환."""
        streams = [
            {"stream_id": "a", "label": "A", "priority": 1, "duration_seconds": 120},
            {"stream_id": "b", "label": "B", "priority": 2, "duration_seconds": 120},
        ]
        result = auto_multicam(streams)

        assert result.total_cuts > 0
        assert all(c.reason == REASON_PERIODIC for c in result.cuts)

    def test_min_cut_gap_respected(self):
        """연속 컷 최소 간격 준수."""
        streams = [
            {
                "stream_id": "a",
                "label": "A",
                "priority": 1,
                "events": [
                    {"type": "speaker_change", "timestamp": "00:10", "speaker": "X"},
                    {"type": "speaker_change", "timestamp": "00:12", "speaker": "Y"},  # 2초 차이 → 무시
                    {"type": "speaker_change", "timestamp": "00:30", "speaker": "Z"},
                ],
            },
            {"stream_id": "b", "label": "B", "priority": 2},
        ]
        result = auto_multicam(streams)

        # 00:12는 최소 간격(5초) 미만이므로 스킵
        timestamps = [c.timestamp for c in result.cuts]
        assert "00:12" not in timestamps

    def test_edit_id_generated(self):
        """edit_id가 생성됨."""
        streams = [
            {"stream_id": "a", "label": "A", "priority": 1},
            {"stream_id": "b", "label": "B", "priority": 2},
        ]
        result = auto_multicam(streams)
        assert result.edit_id
        assert len(result.edit_id) > 0

    def test_streams_sorted_by_priority(self):
        """스트림이 우선순위 순으로 정렬됨."""
        streams = [
            {"stream_id": "low", "label": "낮은", "priority": 10},
            {"stream_id": "high", "label": "높은", "priority": 1},
            {"stream_id": "mid", "label": "중간", "priority": 5},
        ]
        result = auto_multicam(streams)

        assert result.streams[0].stream_id == "high"
        assert result.streams[1].stream_id == "mid"
        assert result.streams[2].stream_id == "low"

    def test_three_streams_rotation(self):
        """3개 스트림 라운드로빈 전환."""
        streams = [
            {
                "stream_id": "a", "label": "A", "priority": 1,
                "events": [
                    {"type": "speaker_change", "timestamp": "00:10", "speaker": "1"},
                    {"type": "speaker_change", "timestamp": "00:20", "speaker": "2"},
                    {"type": "speaker_change", "timestamp": "00:30", "speaker": "3"},
                ],
            },
            {"stream_id": "b", "label": "B", "priority": 2},
            {"stream_id": "c", "label": "C", "priority": 3},
        ]
        result = auto_multicam(streams)

        # 최소 3개 컷 생성
        assert result.total_cuts >= 3
        # 컷의 to_stream이 순환
        assert result.cuts[0].to_stream == "b"
        assert result.cuts[1].to_stream == "c"
        assert result.cuts[2].to_stream == "a"
