"""WhisperProvider — 4순위 (최후) 폴백.

`services.transcript.whisper_service` 모듈을 lazy import 하여
faster-whisper 로컬 음성인식 로직을 wrapping한다.

기존 `extract_transcript_whisper(video_url, model_size)` 는
합쳐진 텍스트(str) 또는 None 반환. 개별 segment timestamp가 없으므로
단일 segment 로 wrapping.
"""
from __future__ import annotations

import logging
import os
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


def _whisper_enabled() -> bool:
    return os.getenv("WHISPER_ENABLED", "").lower() in ("true", "1", "yes")


class WhisperProvider(ITranscriptProvider):
    """faster-whisper 로컬 STT 기반 폴백 — 4순위 (최후).

    `WHISPER_ENABLED=true` 환경변수와 `faster-whisper` 설치가 필요.
    `WHISPER_MODEL` 환경변수로 모델 크기 지정 가능 (기본 'base').
    """

    @property
    def source_type(self) -> SourceType:
        return SourceType.WHISPER

    @property
    def is_available(self) -> bool:
        if not _whisper_enabled():
            return False
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def extract(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        if not _whisper_enabled():
            raise ProviderUnavailable("WHISPER_ENABLED 환경변수 미설정")

        try:
            import faster_whisper  # noqa: F401
        except ImportError as e:
            raise ProviderUnavailable(f"faster-whisper 미설치: {e}")

        try:
            from services.transcript.whisper_service import (
                extract_transcript_whisper,
            )
        except ImportError as e:
            raise ProviderUnavailable(
                f"services.transcript.whisper_service import 실패: {e}"
            )

        video_url = f"https://www.youtube.com/watch?v={video_id.value}"
        model_size = os.getenv("WHISPER_MODEL", "base")

        try:
            text = extract_transcript_whisper(video_url, model_size)
        except Exception as e:
            raise ProviderUnavailable(
                f"Whisper 호출 실패: {type(e).__name__}: {e}"
            )

        if not text or not str(text).strip():
            raise ProviderUnavailable("Whisper가 빈 결과 반환")

        full_text = str(text).strip()
        # 기존 함수는 segment 단위 timestamp를 노출하지 않음 → 단일 segment
        segments = (
            TranscriptSegment(
                start_ms=TimecodeMs(0),
                duration_ms=TimecodeMs(0),
                text=full_text,
            ),
        )

        meta = SourceMeta(
            source_type=self.source_type,
            is_auto_generated=True,
            quality_score=60,
            language=preferred_lang,
            extracted_at=datetime.now(timezone.utc),
        )
        return Transcript(
            video_id=video_id,
            segments=segments,
            source_meta=meta,
        )
