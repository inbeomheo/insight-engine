"""Transcript Aggregate + TranscriptSegment + SourceMeta 단위 테스트.

- `TranscriptSegment`: 빈/공백 텍스트 거부, 불변성
- `SourceMeta`: 4단계 폴백별 메타데이터 보관
- `Transcript` (Aggregate Root): 빈 segments 거부, 리스트→tuple 자동 변환,
  파생 속성 (segment_count / total_duration_ms / full_text), text_at 조회 로직
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.contexts.transcript.domain.transcript import (
    SourceMeta,
    Transcript,
    TranscriptSegment,
)
from src.contexts.transcript.domain.value_objects import (
    SourceType,
    TimecodeMs,
    VideoId,
)


VID = VideoId("dQw4w9WgXcQ")
SEG1 = TranscriptSegment(TimecodeMs(0), TimecodeMs(2000), "hello")
SEG2 = TranscriptSegment(TimecodeMs(2000), TimecodeMs(3000), "world")
FIXED_TS = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)
META = SourceMeta(SourceType.YOUTUBE_API, True, 90, "ko", FIXED_TS)


class TestTranscriptSegment:
    def test_valid_segment(self) -> None:
        s = TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "text")
        assert s.text == "text"
        assert s.start_ms.value == 0
        assert s.duration_ms.value == 1000

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="빈 문자열"):
            TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "")

    def test_whitespace_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="빈 문자열"):
            TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "   ")

    def test_newline_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="빈 문자열"):
            TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "\n\t")

    def test_immutable(self) -> None:
        s = TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "text")
        with pytest.raises((AttributeError, Exception)):
            s.text = "modified"  # type: ignore[misc]


class TestSourceMeta:
    def test_youtube_api_meta(self) -> None:
        m = SourceMeta(SourceType.YOUTUBE_API, True, 90, "ko", FIXED_TS)
        assert m.source_type == SourceType.YOUTUBE_API
        assert m.is_auto_generated is True
        assert m.quality_score == 90
        assert m.language == "ko"
        assert m.extracted_at == FIXED_TS

    def test_whisper_meta(self) -> None:
        m = SourceMeta(SourceType.WHISPER, True, 60, "en", FIXED_TS)
        assert m.source_type == SourceType.WHISPER
        assert m.quality_score == 60

    def test_manual_subtitle_meta(self) -> None:
        # 자동 자막이 아닌 수동 자막
        m = SourceMeta(SourceType.WATCH_PAGE, False, 70, "ja", FIXED_TS)
        assert m.is_auto_generated is False


class TestTranscript:
    def test_basic_construction(self) -> None:
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.segment_count == 2
        assert t.video_id == VID
        assert t.source_meta == META

    def test_empty_segments_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            Transcript(VID, (), META)

    def test_total_duration_ms(self) -> None:
        # 마지막 세그먼트의 start + duration = 2000 + 3000 = 5000
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.total_duration_ms == 5000

    def test_total_duration_single_segment(self) -> None:
        t = Transcript(VID, (SEG1,), META)
        assert t.total_duration_ms == 2000

    def test_full_text_joined_with_newline(self) -> None:
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.full_text == "hello\nworld"

    def test_full_text_single(self) -> None:
        t = Transcript(VID, (SEG1,), META)
        assert t.full_text == "hello"

    def test_segment_count(self) -> None:
        assert Transcript(VID, (SEG1,), META).segment_count == 1
        assert Transcript(VID, (SEG1, SEG2), META).segment_count == 2

    def test_text_at_within_first_segment(self) -> None:
        # SEG1: 0 <= t < 2000
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.text_at(0) == "hello"
        assert t.text_at(1500) == "hello"
        assert t.text_at(1999) == "hello"

    def test_text_at_within_second_segment(self) -> None:
        # SEG2: 2000 <= t < 5000
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.text_at(2000) == "world"
        assert t.text_at(3000) == "world"
        assert t.text_at(4999) == "world"

    def test_text_at_after_end_returns_none(self) -> None:
        t = Transcript(VID, (SEG1, SEG2), META)
        assert t.text_at(10000) is None
        assert t.text_at(5000) is None  # exclusive 경계

    def test_text_at_before_first_segment_returns_none(self) -> None:
        # 첫 세그먼트가 1000ms부터 시작하는 경우, 500ms 시점에는 자막 없음
        late_seg = TranscriptSegment(TimecodeMs(1000), TimecodeMs(1000), "late")
        t = Transcript(VID, (late_seg,), META)
        assert t.text_at(500) is None

    def test_list_segments_converted_to_tuple(self) -> None:
        # __post_init__에서 list → tuple 자동 변환 (불변성 보장)
        t = Transcript(VID, [SEG1, SEG2], META)  # type: ignore[arg-type]
        assert isinstance(t.segments, tuple)
        assert t.segments == (SEG1, SEG2)

    def test_tuple_segments_preserved(self) -> None:
        t = Transcript(VID, (SEG1, SEG2), META)
        assert isinstance(t.segments, tuple)

    def test_aggregate_holds_source_meta(self) -> None:
        # SourceMeta가 Aggregate 내부에 잘 보존되는지
        whisper_meta = SourceMeta(SourceType.WHISPER, True, 60, "en", FIXED_TS)
        t = Transcript(VID, (SEG1,), whisper_meta)
        assert t.source_meta.source_type == SourceType.WHISPER
        assert t.source_meta.quality_score == 60
