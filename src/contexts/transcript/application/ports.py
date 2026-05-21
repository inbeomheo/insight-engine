from abc import ABC, abstractmethod
from typing import Optional

from src.contexts.transcript.domain.transcript import Transcript
from src.contexts.transcript.domain.value_objects import VideoId


class ITranscriptProvider(ABC):
    """자막 추출 제공자 (4단계 폴백의 각 단계)."""

    @abstractmethod
    def extract(self, video_id: VideoId, preferred_lang: str = "ko") -> Transcript:
        """자막 추출. 실패 시 ProviderUnavailable / UnsupportedVideo 예외."""

    @property
    @abstractmethod
    def source_type(self):
        """이 Provider가 어떤 SourceType을 반환하는가."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """이 Provider가 사용 가능한 환경인가 (API 키, SDK 설치 등)."""


class ITranscriptRepository(ABC):
    """Transcript 저장/조회 ACL."""

    @abstractmethod
    def find_by_video_id(self, video_id: VideoId) -> Optional[Transcript]:
        """캐시/저장소에서 조회."""

    @abstractmethod
    def save(self, transcript: Transcript) -> None:
        """저장 (캐시)."""


class ITranscriptCache(ABC):
    """짧은 수명 인메모리 캐시 (1시간 등)."""

    @abstractmethod
    def get(self, video_id: VideoId) -> Optional[Transcript]: ...

    @abstractmethod
    def put(self, transcript: Transcript, ttl_seconds: int = 3600) -> None: ...
