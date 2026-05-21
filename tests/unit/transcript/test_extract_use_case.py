"""ExtractTranscriptUseCase — 4단계 폴백 조정자 단위 테스트.

Provider/Cache를 MagicMock(spec=...)으로 대체하여 다음을 검증:
- 첫 Provider 성공 시 후속 Provider 호출 안 함
- ProviderUnavailable / 예기치 못한 예외 시 다음 Provider로 폴백
- UnsupportedVideo는 폴백하지 않고 즉시 전파
- is_available=False인 Provider는 skip (attempted에도 추가 안 됨)
- 모두 실패하면 ExtractionFailed에 시도한 SourceType 목록 포함
- 캐시 hit 시 Provider 호출 안 함, miss 시 성공한 결과를 cache.put
- preferred_lang 인자가 Provider.extract 에 그대로 전달
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.contexts.transcript.application.ports import (
    ITranscriptCache,
    ITranscriptProvider,
)
from src.contexts.transcript.application.use_cases import ExtractTranscriptUseCase
from src.contexts.transcript.domain.exceptions import (
    ExtractionFailed,
    ProviderUnavailable,
    UnsupportedVideo,
)
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


def make_transcript(source_type: SourceType = SourceType.YOUTUBE_API) -> Transcript:
    seg = TranscriptSegment(TimecodeMs(0), TimecodeMs(1000), "ok")
    meta = SourceMeta(
        source_type, True, 90, "ko",
        datetime(2026, 5, 21, tzinfo=timezone.utc),
    )
    return Transcript(VID, (seg,), meta)


def make_provider(
    source_type: SourceType,
    is_available: bool = True,
    behavior: str = "success",
) -> MagicMock:
    """ITranscriptProvider mock 팩토리.

    behavior:
      - "success": extract가 정상 Transcript 반환
      - "unavailable": ProviderUnavailable (폴백)
      - "unsupported": UnsupportedVideo (즉시 전파)
      - "unexpected": RuntimeError (폴백 — UseCase가 일반 Exception도 잡음)
    """
    p = MagicMock(spec=ITranscriptProvider)
    # property는 spec mock에서 일반 속성처럼 설정
    p.source_type = source_type
    p.is_available = is_available
    if behavior == "success":
        p.extract.return_value = make_transcript(source_type)
    elif behavior == "unavailable":
        p.extract.side_effect = ProviderUnavailable("mocked unavailable")
    elif behavior == "unsupported":
        p.extract.side_effect = UnsupportedVideo("mocked unsupported")
    elif behavior == "unexpected":
        p.extract.side_effect = RuntimeError("mocked unexpected error")
    else:  # pragma: no cover
        raise AssertionError(f"unknown behavior: {behavior}")
    return p


class TestExtractUseCase:
    def test_first_provider_success(self) -> None:
        p1 = make_provider(SourceType.YOUTUBE_API)
        p2 = make_provider(SourceType.WATCH_PAGE)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        result = uc.execute(VID)

        assert result.source_meta.source_type == SourceType.YOUTUBE_API
        p1.extract.assert_called_once()
        p2.extract.assert_not_called()

    def test_fallback_to_second_on_provider_unavailable(self) -> None:
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unavailable")
        p2 = make_provider(SourceType.WATCH_PAGE)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        result = uc.execute(VID)

        assert result.source_meta.source_type == SourceType.WATCH_PAGE
        p1.extract.assert_called_once()
        p2.extract.assert_called_once()

    def test_fallback_chains_through_all_failed_providers(self) -> None:
        # 1~3순위 모두 실패, 4순위(Whisper) 성공 → 4단계 폴백 시나리오
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unavailable")
        p2 = make_provider(SourceType.WATCH_PAGE, behavior="unavailable")
        p3 = make_provider(SourceType.SUPADATA, behavior="unavailable")
        p4 = make_provider(SourceType.WHISPER)
        uc = ExtractTranscriptUseCase(providers=[p1, p2, p3, p4])

        result = uc.execute(VID)

        assert result.source_meta.source_type == SourceType.WHISPER
        p4.extract.assert_called_once()

    def test_skip_unavailable_provider(self) -> None:
        # is_available=False면 extract도 호출되지 않고 attempted에도 없음
        p1 = make_provider(SourceType.YOUTUBE_API, is_available=False)
        p2 = make_provider(SourceType.WATCH_PAGE)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        uc.execute(VID)

        p1.extract.assert_not_called()
        p2.extract.assert_called_once()

    def test_unsupported_video_propagates_without_fallback(self) -> None:
        # 비공개/삭제는 어떤 Provider도 못 풀므로 즉시 전파
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unsupported")
        p2 = make_provider(SourceType.WATCH_PAGE)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        with pytest.raises(UnsupportedVideo):
            uc.execute(VID)
        p2.extract.assert_not_called()

    def test_unexpected_exception_falls_back(self) -> None:
        # ProviderUnavailable 외의 예외도 graceful 폴백
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unexpected")
        p2 = make_provider(SourceType.WATCH_PAGE)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        result = uc.execute(VID)

        assert result.source_meta.source_type == SourceType.WATCH_PAGE

    def test_all_providers_fail_raises_extraction_failed(self) -> None:
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unavailable")
        p2 = make_provider(SourceType.WATCH_PAGE, behavior="unavailable")
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        with pytest.raises(ExtractionFailed) as exc_info:
            uc.execute(VID)

        err = exc_info.value
        assert err.video_id == VID
        assert SourceType.YOUTUBE_API in err.attempted_sources
        assert SourceType.WATCH_PAGE in err.attempted_sources
        assert "watch_page_parse" in err.last_error

    def test_empty_providers_raises_extraction_failed(self) -> None:
        uc = ExtractTranscriptUseCase(providers=[])

        with pytest.raises(ExtractionFailed) as exc_info:
            uc.execute(VID)

        assert exc_info.value.attempted_sources == ()

    def test_all_unavailable_providers_skipped(self) -> None:
        # is_available=False만 있으면 attempted는 비어있고 ExtractionFailed
        p1 = make_provider(SourceType.YOUTUBE_API, is_available=False)
        p2 = make_provider(SourceType.WATCH_PAGE, is_available=False)
        uc = ExtractTranscriptUseCase(providers=[p1, p2])

        with pytest.raises(ExtractionFailed) as exc_info:
            uc.execute(VID)

        # is_available=False 였으므로 attempted에는 추가되지 않음
        assert exc_info.value.attempted_sources == ()
        p1.extract.assert_not_called()
        p2.extract.assert_not_called()

    def test_cache_hit_skips_all_providers(self) -> None:
        cached = make_transcript(SourceType.YOUTUBE_API)
        cache = MagicMock(spec=ITranscriptCache)
        cache.get.return_value = cached
        p1 = make_provider(SourceType.YOUTUBE_API)
        uc = ExtractTranscriptUseCase(providers=[p1], cache=cache)

        result = uc.execute(VID)

        assert result is cached
        p1.extract.assert_not_called()
        cache.put.assert_not_called()  # 이미 캐시에 있으므로 put 안 함

    def test_cache_miss_calls_provider_and_caches_result(self) -> None:
        cache = MagicMock(spec=ITranscriptCache)
        cache.get.return_value = None
        p1 = make_provider(SourceType.YOUTUBE_API)
        uc = ExtractTranscriptUseCase(providers=[p1], cache=cache)

        result = uc.execute(VID)

        cache.get.assert_called_once_with(VID)
        p1.extract.assert_called_once()
        cache.put.assert_called_once_with(result)

    def test_cache_not_populated_on_extraction_failure(self) -> None:
        cache = MagicMock(spec=ITranscriptCache)
        cache.get.return_value = None
        p1 = make_provider(SourceType.YOUTUBE_API, behavior="unavailable")
        uc = ExtractTranscriptUseCase(providers=[p1], cache=cache)

        with pytest.raises(ExtractionFailed):
            uc.execute(VID)

        cache.put.assert_not_called()

    def test_no_cache_works_without_errors(self) -> None:
        # cache=None (기본값) — 캐시 없이 작동
        p1 = make_provider(SourceType.YOUTUBE_API)
        uc = ExtractTranscriptUseCase(providers=[p1])

        result = uc.execute(VID)

        assert result.source_meta.source_type == SourceType.YOUTUBE_API

    def test_preferred_lang_passed_to_provider(self) -> None:
        p1 = make_provider(SourceType.YOUTUBE_API)
        uc = ExtractTranscriptUseCase(providers=[p1])

        uc.execute(VID, preferred_lang="en")

        p1.extract.assert_called_once_with(VID, "en")

    def test_default_lang_is_ko(self) -> None:
        p1 = make_provider(SourceType.YOUTUBE_API)
        uc = ExtractTranscriptUseCase(providers=[p1])

        uc.execute(VID)

        p1.extract.assert_called_once_with(VID, "ko")
