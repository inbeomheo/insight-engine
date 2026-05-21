import logging
from dataclasses import dataclass

from src.contexts.transcript.application.ports import ITranscriptCache, ITranscriptProvider
from src.contexts.transcript.domain.exceptions import (
    ExtractionFailed,
    ProviderUnavailable,
    UnsupportedVideo,
)
from src.contexts.transcript.domain.transcript import Transcript
from src.contexts.transcript.domain.value_objects import SourceType, VideoId

logger = logging.getLogger(__name__)


@dataclass
class ExtractTranscriptUseCase:
    """4단계 폴백 조정자.

    우선순위: YOUTUBE_API → WATCH_PAGE → SUPADATA → WHISPER.
    각 Provider는 ITranscriptProvider 구현. is_available=False인 Provider는 건너뜀.
    """
    providers: list[ITranscriptProvider]
    cache: ITranscriptCache | None = None

    def execute(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        # 1. 캐시 우선
        if self.cache:
            cached = self.cache.get(video_id)
            if cached:
                logger.info("transcript cache hit: %s", video_id.value)
                return cached

        attempted: list[SourceType] = []
        last_error = "no provider attempted"

        # 2. 우선순위 순으로 시도
        for provider in self.providers:
            if not provider.is_available:
                logger.debug("provider unavailable, skip: %s", provider.source_type)
                continue
            attempted.append(provider.source_type)
            try:
                transcript = provider.extract(video_id, preferred_lang)
                if self.cache:
                    self.cache.put(transcript)
                return transcript
            except UnsupportedVideo:
                # 비공개/삭제 — 폴백해도 무의미
                raise
            except ProviderUnavailable as e:
                last_error = f"{provider.source_type.value}: {e}"
                logger.warning("provider failed, fallback: %s", last_error)
                continue
            except Exception as e:
                last_error = f"{provider.source_type.value}: {type(e).__name__}: {e}"
                logger.exception("provider unexpected error, fallback: %s", last_error)
                continue

        raise ExtractionFailed(video_id, tuple(attempted), last_error)
