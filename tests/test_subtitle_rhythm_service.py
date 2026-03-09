"""
자막 리듬 최적화 서비스 테스트 (T4.3)
SRT 파싱/직렬화, 리듬 최적화, 텍스트→컷 포인트 변환 검증.
"""
import pytest

from services.subtitle_rhythm_service import (
    CutPoint,
    OptimizedSrt,
    SrtEntry,
    _duration_sec,
    _ms_to_time,
    _time_to_ms,
    entries_to_srt,
    optimize_rhythm,
    parse_srt,
    text_to_cuts,
)

# ── 테스트 픽스처 ──

SIMPLE_SRT = """\
1
00:00:01,000 --> 00:00:04,000
안녕하세요, 첫 번째 자막입니다.

2
00:00:04,500 --> 00:00:08,000
두 번째 자막입니다.

3
00:00:08,500 --> 00:00:12,000
세 번째 자막입니다.
"""

# 짧은 자막 (0.5초) — 병합 대상
SHORT_SUBTITLE_SRT = """\
1
00:00:01,000 --> 00:00:01,400
짧은

2
00:00:01,500 --> 00:00:05,000
두 번째 자막입니다.
"""

# 긴 자막 (10초) — 분할 대상
LONG_SUBTITLE_SRT = """\
1
00:00:00,000 --> 00:00:10,000
이것은 매우 긴 자막으로서 최대 허용 시간을 초과하는 긴 문장을 포함하고 있습니다
"""

# 겹치는 자막 — 겹침 해소 대상
OVERLAPPING_SRT = """\
1
00:00:01,000 --> 00:00:05,000
첫 번째 자막

2
00:00:04,000 --> 00:00:08,000
두 번째 자막
"""


# ── 시간 변환 테스트 ──

class TestTimeConversion:
    """타임코드 ↔ 밀리초 변환 테스트."""

    def test_time_to_ms_basic(self):
        assert _time_to_ms("00:00:01,000") == 1000

    def test_time_to_ms_complex(self):
        assert _time_to_ms("01:30:45,123") == 5445123

    def test_time_to_ms_zero(self):
        assert _time_to_ms("00:00:00,000") == 0

    def test_ms_to_time_basic(self):
        assert _ms_to_time(1000) == "00:00:01,000"

    def test_ms_to_time_complex(self):
        assert _ms_to_time(5445123) == "01:30:45,123"

    def test_ms_to_time_zero(self):
        assert _ms_to_time(0) == "00:00:00,000"

    def test_ms_to_time_negative_clamps(self):
        """음수 → 0으로 클램프."""
        assert _ms_to_time(-100) == "00:00:00,000"

    def test_roundtrip(self):
        """타임코드 → ms → 타임코드 왕복 변환."""
        original = "02:15:30,456"
        ms = _time_to_ms(original)
        assert _ms_to_time(ms) == original

    def test_time_to_ms_invalid_format(self):
        with pytest.raises(ValueError, match="잘못된 타임코드"):
            _time_to_ms("invalid")

    def test_time_to_ms_dot_separator(self):
        """마침표 구분자도 허용."""
        assert _time_to_ms("00:00:01.500") == 1500


# ── SRT 파싱 테스트 ──

class TestParseSrt:
    """SRT 문자열 파싱 테스트."""

    def test_parse_simple(self):
        entries = parse_srt(SIMPLE_SRT)
        assert len(entries) == 3
        assert entries[0].index == 1
        assert entries[0].start_time == "00:00:01,000"
        assert entries[0].end_time == "00:00:04,000"
        assert entries[0].text == "안녕하세요, 첫 번째 자막입니다."

    def test_parse_empty_string(self):
        assert parse_srt("") == []

    def test_parse_whitespace_only(self):
        assert parse_srt("   \n\n  ") == []

    def test_parse_bom(self):
        """BOM이 있는 SRT도 파싱."""
        bom_srt = "\ufeff" + SIMPLE_SRT
        entries = parse_srt(bom_srt)
        assert len(entries) == 3

    def test_parse_multiline_text(self):
        """여러 줄 자막 텍스트."""
        srt = "1\n00:00:01,000 --> 00:00:04,000\n첫 번째 줄\n두 번째 줄\n"
        entries = parse_srt(srt)
        assert len(entries) == 1
        assert entries[0].text == "첫 번째 줄\n두 번째 줄"

    def test_parse_dot_separator(self):
        """마침표 구분자 타임코드."""
        srt = "1\n00:00:01.000 --> 00:00:04.000\n텍스트\n"
        entries = parse_srt(srt)
        assert len(entries) == 1
        # 마침표 → 쉼표로 정규화
        assert entries[0].start_time == "00:00:01,000"


# ── SRT 직렬화 테스트 ──

class TestEntriesToSrt:
    """SrtEntry → SRT 문자열 직렬화 테스트."""

    def test_serialize_single(self):
        entries = [SrtEntry(1, "00:00:01,000", "00:00:04,000", "테스트")]
        result = entries_to_srt(entries)
        assert "1\n00:00:01,000 --> 00:00:04,000\n테스트\n" == result

    def test_serialize_empty(self):
        assert entries_to_srt([]) == ""

    def test_roundtrip_parse_serialize(self):
        """파싱 → 직렬화 왕복 일관성."""
        entries = parse_srt(SIMPLE_SRT)
        srt_out = entries_to_srt(entries)
        re_parsed = parse_srt(srt_out)
        assert len(re_parsed) == len(entries)
        for orig, re in zip(entries, re_parsed):
            assert orig.start_time == re.start_time
            assert orig.end_time == re.end_time
            assert orig.text == re.text

    def test_reindex_on_serialize(self):
        """직렬화 시 인덱스는 1부터 순차 할당."""
        entries = [
            SrtEntry(10, "00:00:01,000", "00:00:02,000", "A"),
            SrtEntry(20, "00:00:03,000", "00:00:04,000", "B"),
        ]
        result = entries_to_srt(entries)
        assert result.startswith("1\n")
        assert "\n\n2\n" in result


# ── 리듬 최적화 테스트 ──

class TestOptimizeRhythm:
    """optimize_rhythm 통합 테스트."""

    def test_optimize_no_changes(self):
        """이미 최적인 자막은 변경 없음."""
        result = optimize_rhythm(SIMPLE_SRT)
        assert isinstance(result, OptimizedSrt)
        assert result.original_count == 3
        # 변경이 없거나 줄바꿈만 변경
        assert result.optimized_count >= 3

    def test_optimize_empty(self):
        result = optimize_rhythm("")
        assert result.original_count == 0
        assert result.optimized_count == 0
        assert result.changes_made == []

    def test_merge_short_subtitles(self):
        """짧은 자막(MIN_DURATION_SEC 미만)이 병합되는지 확인."""
        result = optimize_rhythm(SHORT_SUBTITLE_SRT)
        # 0.4초 자막이 다음 자막과 병합되어 1개로 줄어야 함
        assert result.optimized_count < result.original_count
        assert any("병합" in c for c in result.changes_made)

    def test_split_long_subtitles(self):
        """긴 자막(MAX_DURATION_SEC 초과)이 분할되는지 확인."""
        result = optimize_rhythm(LONG_SUBTITLE_SRT)
        assert result.optimized_count > result.original_count
        assert any("분할" in c for c in result.changes_made)

    def test_resolve_overlaps(self):
        """겹치는 자막의 타이밍이 조정되는지 확인."""
        result = optimize_rhythm(OVERLAPPING_SRT)
        # 겹침이 해소되어야 함
        for i in range(len(result.entries) - 1):
            end_ms = _time_to_ms(result.entries[i].end_time)
            start_ms = _time_to_ms(result.entries[i + 1].start_time)
            assert end_ms <= start_ms, "겹침이 해소되지 않음"

    def test_changes_made_populated(self):
        """변경이 있으면 changes_made에 기록."""
        result = optimize_rhythm(OVERLAPPING_SRT)
        assert len(result.changes_made) > 0

    def test_line_break_long_text(self):
        """42자 초과 텍스트에 줄바꿈 삽입."""
        srt = (
            "1\n00:00:00,000 --> 00:00:03,000\n"
            "이것은 매우 긴 한 줄 텍스트로서 한 줄에 표시하기에는 너무 긴 자막 문장입니다\n"
        )
        result = optimize_rhythm(srt)
        # 줄바꿈이 삽입되어야 함
        has_newline = any('\n' in e.text for e in result.entries)
        assert has_newline

    def test_entries_reindexed(self):
        """최적화 후 인덱스가 1부터 순차."""
        result = optimize_rhythm(OVERLAPPING_SRT)
        for i, entry in enumerate(result.entries, 1):
            assert entry.index == i


# ── 텍스트→컷 포인트 테스트 ──

class TestTextToCuts:
    """text_to_cuts 함수 테스트."""

    def test_single_delete(self):
        edits = [
            {"start": "00:01:30", "end": "00:02:00", "action": "delete", "text": "삭제할 텍스트"}
        ]
        cuts = text_to_cuts(edits)
        assert len(cuts) == 1
        assert cuts[0].reason == "deleted"
        assert cuts[0].original_text == "삭제할 텍스트"
        assert cuts[0].start_time == "00:01:30,000"

    def test_multiple_edits(self):
        edits = [
            {"start": "00:00:10", "end": "00:00:20", "action": "delete", "text": "A"},
            {"start": "00:01:00", "end": "00:01:30", "action": "shorten", "text": "B"},
            {"start": "00:02:00", "end": "00:02:30", "action": "rearranged", "text": "C"},
        ]
        cuts = text_to_cuts(edits)
        assert len(cuts) == 3
        assert cuts[0].reason == "deleted"
        assert cuts[1].reason == "shortened"
        assert cuts[2].reason == "rearranged"

    def test_empty_edits(self):
        assert text_to_cuts([]) == []

    def test_invalid_action_defaults_to_deleted(self):
        """유효하지 않은 action은 'deleted'로 대체."""
        edits = [{"start": "00:00:00", "end": "00:00:05", "action": "unknown", "text": "X"}]
        cuts = text_to_cuts(edits)
        assert cuts[0].reason == "deleted"

    def test_time_with_milliseconds_preserved(self):
        """이미 밀리초가 포함된 시간은 그대로 유지."""
        edits = [
            {"start": "00:01:30,500", "end": "00:02:00,750", "action": "delete", "text": "X"}
        ]
        cuts = text_to_cuts(edits)
        assert cuts[0].start_time == "00:01:30,500"
        assert cuts[0].end_time == "00:02:00,750"

    def test_missing_fields_defaults(self):
        """필드 누락 시 기본값 사용."""
        edits = [{}]
        cuts = text_to_cuts(edits)
        assert len(cuts) == 1
        assert cuts[0].start_time == "00:00:00,000"
        assert cuts[0].reason == "deleted"
        assert cuts[0].original_text == ""


# ── duration 유틸 테스트 ──

class TestDurationSec:
    """_duration_sec 유틸 테스트."""

    def test_basic_duration(self):
        entry = SrtEntry(1, "00:00:01,000", "00:00:04,000", "test")
        assert _duration_sec(entry) == 3.0

    def test_sub_second_duration(self):
        entry = SrtEntry(1, "00:00:00,000", "00:00:00,500", "test")
        assert _duration_sec(entry) == pytest.approx(0.5)
