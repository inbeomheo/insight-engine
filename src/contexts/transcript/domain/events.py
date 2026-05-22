from dataclasses import dataclass
from datetime import datetime

from src.contexts.transcript.domain.value_objects import VideoId, SourceType


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime


@dataclass(frozen=True)
class TranscriptExtracted(DomainEvent):
    video_id: VideoId
    source_type: SourceType
    segment_count: int
    duration_ms: int


@dataclass(frozen=True)
class ExtractionFailed(DomainEvent):
    video_id: VideoId
    attempted_sources: tuple[SourceType, ...]
    last_error: str
