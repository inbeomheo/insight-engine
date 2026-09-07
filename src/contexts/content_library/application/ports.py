"""Content/Library BC 외부 의존성 포트."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.history_entry import HistoryEntry


class IHistoryRepository(ABC):
    """HistoryEntry 영속화 포트.

    구현체는 인프라 계층에서 제공 (Supabase / In-Memory).
    """

    @abstractmethod
    def save(
        self,
        entry: HistoryEntry,
        *,
        validated_access_token: str | None = None,
    ) -> dict | None:
        """검증된 사용자 권한으로 저장하고 Supabase row dict를 반환한다."""

    @abstractmethod
    def save_many(self, entries: list[HistoryEntry]) -> int:
        """다수 HistoryEntry를 단일 트랜잭션으로 저장. 저장된 개수 반환.

        구현체는 단일 INSERT (Supabase batch) 또는 fallback (N회 save)로 처리.
        """

__all__ = ["IHistoryRepository"]
