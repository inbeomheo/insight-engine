"""Transcript BC 인프라스트럭처 어댑터.

4단계 폴백 Provider (YouTube API → Watch Page → Supadata → Whisper) +
인메모리 캐시. 각 Provider는 ITranscriptProvider 구현이며 기존
services/transcript/ 헬퍼를 lazy import 하여 wrapping한다.
"""
from src.contexts.transcript.infrastructure.in_memory_transcript_cache import (
    InMemoryTranscriptCache,
)
from src.contexts.transcript.infrastructure.supadata_provider import (
    SupadataProvider,
)
from src.contexts.transcript.infrastructure.watch_page_provider import (
    WatchPageProvider,
)
from src.contexts.transcript.infrastructure.whisper_provider import (
    WhisperProvider,
)
from src.contexts.transcript.infrastructure.youtube_api_provider import (
    YouTubeApiProvider,
)

__all__ = [
    "YouTubeApiProvider",
    "WatchPageProvider",
    "SupadataProvider",
    "WhisperProvider",
    "InMemoryTranscriptCache",
]
