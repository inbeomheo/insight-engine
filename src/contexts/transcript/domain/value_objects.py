from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class VideoId:
    """YouTube 11자리 video ID."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or len(self.value) != 11:
            raise ValueError(f"video_id는 11자리 문자열이어야 함: {self.value}")
        if not all(c.isalnum() or c in '-_' for c in self.value):
            raise ValueError(f"video_id에 유효하지 않은 문자: {self.value}")


@dataclass(frozen=True, slots=True)
class TimecodeMs:
    """타임코드 (밀리초)."""
    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value < 0:
            raise ValueError(f"timecode는 0 이상 정수: {self.value}")

    def to_seconds(self) -> float:
        return self.value / 1000.0

    def to_mmss(self) -> str:
        total_sec = self.value // 1000
        return f"{total_sec // 60:02d}:{total_sec % 60:02d}"


class SourceType(Enum):
    """자막 소스 타입 — 폴백 우선순위와 일치."""
    YOUTUBE_API = "youtube_transcript_api"  # 1순위
    WATCH_PAGE = "watch_page_parse"          # 2순위
    SUPADATA = "supadata"                    # 3순위 (유료)
    WHISPER = "whisper_local"                # 4순위 (마지막)
