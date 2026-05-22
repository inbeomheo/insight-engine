"""Transcript BC 값 객체(VO) 단위 테스트.

- `VideoId`: 11자리 영숫자/언더스코어/하이픈 검증 + frozen 불변성
- `TimecodeMs`: 0 이상 정수 검증 + 변환(to_seconds, to_mmss)
- `SourceType`: 4단계 폴백 enum 값 고정
"""

from __future__ import annotations

import pytest

from src.contexts.transcript.domain.value_objects import SourceType, TimecodeMs, VideoId


class TestVideoId:
    def test_valid_11_char_id(self) -> None:
        vid = VideoId("dQw4w9WgXcQ")
        assert vid.value == "dQw4w9WgXcQ"

    def test_short_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="11자리"):
            VideoId("too_short")

    def test_long_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="11자리"):
            VideoId("this_is_way_too_long")

    def test_invalid_chars_rejected(self) -> None:
        # '!'는 영숫자/언더스코어/하이픈 외 문자
        with pytest.raises(ValueError, match="유효하지 않"):
            VideoId("dQw4w9!gXcQ")

    def test_underscore_hyphen_allowed(self) -> None:
        # 언더스코어/하이픈 혼합 11자
        vid = VideoId("abc_def-ghi")
        assert vid.value == "abc_def-ghi"

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="11자리"):
            VideoId("")

    def test_non_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="11자리"):
            VideoId(12345678901)  # type: ignore[arg-type]

    def test_immutable_frozen_slots(self) -> None:
        # frozen=True, slots=True인 dataclass는 수정 시 AttributeError 발생
        vid = VideoId("dQw4w9WgXcQ")
        with pytest.raises((AttributeError, Exception)):
            vid.value = "newvalue000"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        # frozen dataclass는 값 기반 동등성
        assert VideoId("dQw4w9WgXcQ") == VideoId("dQw4w9WgXcQ")
        assert VideoId("dQw4w9WgXcQ") != VideoId("abcdefghijk")

    def test_hashable(self) -> None:
        # frozen → hashable → set/dict 키로 사용 가능
        s = {VideoId("dQw4w9WgXcQ"), VideoId("dQw4w9WgXcQ")}
        assert len(s) == 1


class TestTimecodeMs:
    def test_zero_valid(self) -> None:
        tc = TimecodeMs(0)
        assert tc.value == 0

    def test_positive_valid(self) -> None:
        tc = TimecodeMs(123456)
        assert tc.value == 123456

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="0 이상"):
            TimecodeMs(-1)

    def test_float_rejected(self) -> None:
        with pytest.raises(ValueError, match="정수"):
            TimecodeMs(1.5)  # type: ignore[arg-type]

    def test_to_seconds(self) -> None:
        assert TimecodeMs(1500).to_seconds() == 1.5
        assert TimecodeMs(0).to_seconds() == 0.0
        assert TimecodeMs(1000).to_seconds() == 1.0

    def test_to_mmss_basic(self) -> None:
        assert TimecodeMs(75_000).to_mmss() == "01:15"

    def test_to_mmss_zero(self) -> None:
        assert TimecodeMs(0).to_mmss() == "00:00"

    def test_to_mmss_under_minute(self) -> None:
        assert TimecodeMs(5_000).to_mmss() == "00:05"

    def test_to_mmss_long(self) -> None:
        # 59분 59초
        assert TimecodeMs(3_599_000).to_mmss() == "59:59"

    def test_immutable(self) -> None:
        tc = TimecodeMs(1000)
        with pytest.raises((AttributeError, Exception)):
            tc.value = 2000  # type: ignore[misc]


class TestSourceType:
    def test_youtube_api_value(self) -> None:
        assert SourceType.YOUTUBE_API.value == "youtube_transcript_api"

    def test_watch_page_value(self) -> None:
        assert SourceType.WATCH_PAGE.value == "watch_page_parse"

    def test_supadata_value(self) -> None:
        assert SourceType.SUPADATA.value == "supadata"

    def test_whisper_value(self) -> None:
        assert SourceType.WHISPER.value == "whisper_local"

    def test_exactly_four_members(self) -> None:
        # 4단계 폴백을 그대로 반영 — 더 늘어나면 우선순위 정책 재검토 필요
        assert len(list(SourceType)) == 4
