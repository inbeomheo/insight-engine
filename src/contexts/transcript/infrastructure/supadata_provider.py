"""SupadataProvider — 3순위 폴백 (유료 API).

`services.transcript.fallbacks.supadata` 모듈을 lazy import 하여
Supadata API 호출 로직을 wrapping한다.
"""
from __future__ import annotations

import logging
import os
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


class SupadataProvider(ITranscriptProvider):
    """Supadata API 기반 자막 폴백 — 3순위 (유료).

    `SUPADATA_API_KEY` 환경변수 필수.
    기존 함수 `services.transcript.fallbacks.supadata.get_transcript_via_supadata`는
    성공 시 합쳐진 텍스트(str), 실패 시 None 또는 {'error': msg} 반환.
    → 본 어댑터는 단일 segment 로 wrapping.
    """

    @property
    def source_type(self) -> SourceType:
        return SourceType.SUPADATA

    @property
    def is_available(self) -> bool:
        return bool(os.getenv("SUPADATA_API_KEY"))

    def extract(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        api_key = os.getenv("SUPADATA_API_KEY", "")
        if not api_key:
            raise ProviderUnavailable("SUPADATA_API_KEY 미설정")

        try:
            from services.transcript.fallbacks.supadata import (
                get_transcript_via_supadata,
            )
        except ImportError as e:
            raise ProviderUnavailable(
                f"services.transcript.fallbacks.supadata import 실패: {e}"
            )

        try:
            result = get_transcript_via_supadata(video_id.value, api_key)
        except Exception as e:
            raise ProviderUnavailable(
                f"Supadata 호출 실패: {type(e).__name__}: {e}"
            )

        if result is None:
            raise ProviderUnavailable("Supadata가 빈 응답 반환 (None)")

        if isinstance(result, dict):
            err = (result.get("error") or "").strip()
            # 키 무효/쿼터 초과는 폴백 진행 (다른 Provider 시도)
            # 일관성을 위해 ProviderUnavailable로 통일
            raise ProviderUnavailable(f"Supadata: {err or 'unknown error'}")

        if not isinstance(result, str) or not result.strip():
            raise ProviderUnavailable("Supadata가 빈 텍스트 반환")

        full_text = result.strip()
        segments = (
            TranscriptSegment(
                start_ms=TimecodeMs(0),
                duration_ms=TimecodeMs(0),
                text=full_text,
            ),
        )

        meta = SourceMeta(
            source_type=self.source_type,
            is_auto_generated=False,
            quality_score=80,
            language=preferred_lang,
            extracted_at=datetime.now(timezone.utc),
        )
        return Transcript(
            video_id=video_id,
            segments=segments,
            source_meta=meta,
        )
