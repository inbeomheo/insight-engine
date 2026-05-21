"""WatchPageProvider — 2순위 폴백.

`services.transcript.fallbacks.watch_page` 모듈을 lazy import 하여
YouTube watch 페이지 파싱 로직을 wrapping한다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.contexts.transcript.application.ports import ITranscriptProvider
from src.contexts.transcript.domain.exceptions import ProviderUnavailable
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

logger = logging.getLogger(__name__)


class WatchPageProvider(ITranscriptProvider):
    """YouTube watch 페이지 HTML 파싱 — 2순위 폴백.

    youtube-transcript-api가 차단당했을 때 직접 페이지를 긁어
    `ytInitialPlayerResponse` JSON에서 caption_tracks를 추출한다.

    기존 함수 `services.transcript.fallbacks.watch_page.get_transcript_from_watch_page`
    는 합쳐진 문자열만 반환 (개별 segment timestamp 없음).
    → 본 어댑터는 단일 segment (start=0, duration=0) 로 wrapping.
    """

    @property
    def source_type(self) -> SourceType:
        return SourceType.WATCH_PAGE

    @property
    def is_available(self) -> bool:
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def extract(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        if not self.is_available:
            raise ProviderUnavailable("requests 라이브러리 미설치")

        try:
            from services.transcript.fallbacks.watch_page import (
                get_transcript_from_watch_page,
            )
        except ImportError as e:
            raise ProviderUnavailable(
                f"services.transcript.fallbacks.watch_page import 실패: {e}"
            )

        try:
            result = get_transcript_from_watch_page(video_id.value)
        except Exception as e:
            raise ProviderUnavailable(
                f"watch page 파싱 호출 실패: {type(e).__name__}: {e}"
            )

        # 기존 함수는 str (성공) 또는 {'error': msg} (실패) 반환
        if isinstance(result, dict):
            err = result.get("error") or "watch page 파싱 실패"
            raise ProviderUnavailable(f"watch page: {err}")

        if not isinstance(result, str) or not result.strip():
            raise ProviderUnavailable("watch page가 빈 자막 반환")

        full_text = result.strip()
        # 합쳐진 텍스트만 가지고 있으므로 단일 segment 처리
        segments = (
            TranscriptSegment(
                start_ms=TimecodeMs(0),
                duration_ms=TimecodeMs(0),
                text=full_text,
            ),
        )

        meta = SourceMeta(
            source_type=self.source_type,
            is_auto_generated=False,  # 정확한 판별 불가 — 보수적으로 False
            quality_score=70,
            language=preferred_lang,
            extracted_at=datetime.now(timezone.utc),
        )
        return Transcript(
            video_id=video_id,
            segments=segments,
            source_meta=meta,
        )
