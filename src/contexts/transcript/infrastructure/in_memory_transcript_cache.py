"""InMemoryTranscriptCache — 프로세스 인메모리 캐시.

ITranscriptCache 구현. TTL 기본 1시간.
스레드 안전 (`threading.Lock` 사용).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from src.contexts.transcript.application.ports import ITranscriptCache
from src.contexts.transcript.domain.transcript import Transcript
from src.contexts.transcript.domain.value_objects import VideoId

logger = logging.getLogger(__name__)


class InMemoryTranscriptCache(ITranscriptCache):
    """프로세스 인메모리 캐시 (TTL 기반).

    멀티프로세스 환경에서는 각 워커가 독립된 캐시를 갖게 됨.
    분산 환경이 필요하면 Redis 등의 외부 캐시 어댑터를 추가로 구현.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Transcript, float]] = {}
        self._lock = threading.Lock()

    def get(self, video_id: VideoId) -> Optional[Transcript]:
        with self._lock:
            entry = self._store.get(video_id.value)
            if entry is None:
                return None
            transcript, expires_at = entry
            if time.time() >= expires_at:
                # 만료 — 즉시 제거
                del self._store[video_id.value]
                logger.debug("cache expired: %s", video_id.value)
                return None
            return transcript

    def put(self, transcript: Transcript, ttl_seconds: int = 3600) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            self._store[transcript.video_id.value] = (
                transcript,
                time.time() + ttl_seconds,
            )

    def clear(self) -> None:
        """테스트/디버그용. 인터페이스 외 메서드."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """테스트/디버그용. 현재 캐시 항목 수."""
        with self._lock:
            return len(self._store)
