"""YouTubeApiProvider — 1순위 폴백.

`services.transcript.fallbacks.youtube_api` 모듈의 기존 헬퍼를 lazy import 하여
youtube-transcript-api 라이브러리 호출을 wrapping한다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.contexts.transcript.application.ports import ITranscriptProvider
from src.contexts.transcript.domain.exceptions import (
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

logger = logging.getLogger(__name__)


class YouTubeApiProvider(ITranscriptProvider):
    """youtube-transcript-api 라이브러리 기반 1순위 폴백.

    빠르고 무료. YouTube가 IP/요청 차단하면 ProviderUnavailable로 폴백 진행.
    내부적으로 services/transcript/fallbacks/youtube_api.py의 헬퍼를 lazy import.
    """

    @property
    def source_type(self) -> SourceType:
        return SourceType.YOUTUBE_API

    @property
    def is_available(self) -> bool:
        try:
            import youtube_transcript_api  # noqa: F401
            return True
        except ImportError:
            return False

    def extract(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        if not self.is_available:
            raise ProviderUnavailable("youtube-transcript-api 미설치")

        # 기존 헬퍼 lazy import
        try:
            from services.transcript.fallbacks.youtube_api import (
                build_ytt_api,
                detect_auto_caption,
                extract_segments_from_transcript,
                fetch_transcript_with_api,
            )
        except ImportError as e:
            raise ProviderUnavailable(
                f"services.transcript.fallbacks.youtube_api import 실패: {e}"
            )

        # 라이브러리 내부 예외 lazy import (버전 호환성)
        try:
            from youtube_transcript_api._errors import (  # type: ignore
                VideoUnavailable,
            )
        except ImportError:
            VideoUnavailable = None  # type: ignore

        try:
            ytt_api = build_ytt_api()
            fetched = fetch_transcript_with_api(ytt_api, video_id.value)
        except Exception as e:
            # VideoUnavailable는 폴백해도 무의미 → UnsupportedVideo로 승격
            if VideoUnavailable is not None and isinstance(e, VideoUnavailable):
                raise UnsupportedVideo(
                    f"video unavailable: {video_id.value}: {e}"
                )
            raise ProviderUnavailable(
                f"YouTube API 호출 실패: {type(e).__name__}: {e}"
            )

        if not fetched:
            raise ProviderUnavailable("YouTube API가 자막 없음/빈 결과 반환")

        # 세그먼트 추출 (timestamp 포함)
        raw_segments = extract_segments_from_transcript(fetched)
        if not raw_segments:
            raise ProviderUnavailable("YouTube API 자막에서 세그먼트 추출 실패")

        segments: list[TranscriptSegment] = []
        for item in raw_segments:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            start_sec = float(item.get("start", 0) or 0)
            dur_sec = float(item.get("duration", 0) or 0)
            segments.append(
                TranscriptSegment(
                    start_ms=TimecodeMs(max(0, int(start_sec * 1000))),
                    duration_ms=TimecodeMs(max(0, int(dur_sec * 1000))),
                    text=text,
                )
            )

        if not segments:
            raise ProviderUnavailable(
                "YouTube API 세그먼트가 모두 빈 텍스트"
            )

        # 자동 자막 여부 판별 (실패해도 False로 fallback)
        try:
            is_auto = detect_auto_caption(ytt_api, video_id.value)
        except Exception:
            is_auto = False

        meta = SourceMeta(
            source_type=self.source_type,
            is_auto_generated=is_auto,
            quality_score=90,
            language=preferred_lang,
            extracted_at=datetime.now(timezone.utc),
        )
        return Transcript(
            video_id=video_id,
            segments=tuple(segments),
            source_meta=meta,
        )
