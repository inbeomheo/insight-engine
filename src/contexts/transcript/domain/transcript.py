from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.contexts.transcript.domain.value_objects import VideoId, TimecodeMs, SourceType


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """자막 한 줄."""
    start_ms: TimecodeMs
    duration_ms: TimecodeMs
    text: str

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("text는 빈 문자열 불가")


@dataclass(frozen=True, slots=True)
class SourceMeta:
    """자막 출처 메타데이터 (4단계 폴백별 품질 정보)."""
    source_type: SourceType
    is_auto_generated: bool       # 자동 자막 여부
    quality_score: int            # 0~100 (API=90, page=70, supadata=80, whisper=60)
    language: str                 # "ko", "en", "ja" 등
    extracted_at: datetime


@dataclass
class Transcript:
    """Transcript Aggregate Root.

    한 비디오의 자막. 4단계 폴백 중 하나가 성공하면 Transcript 객체 생성.
    """
    video_id: VideoId
    segments: tuple[TranscriptSegment, ...]
    source_meta: SourceMeta

    def __post_init__(self):
        if not self.segments:
            raise ValueError("segments는 비어있을 수 없음")
        if not isinstance(self.segments, tuple):
            object.__setattr__(self, 'segments', tuple(self.segments))

    @property
    def total_duration_ms(self) -> int:
        last = self.segments[-1]
        return last.start_ms.value + last.duration_ms.value

    @property
    def full_text(self) -> str:
        return "\n".join(s.text for s in self.segments)

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    def text_at(self, time_ms: int) -> Optional[str]:
        """특정 시점에 재생 중인 자막 텍스트."""
        for s in self.segments:
            if s.start_ms.value <= time_ms < s.start_ms.value + s.duration_ms.value:
                return s.text
        return None
