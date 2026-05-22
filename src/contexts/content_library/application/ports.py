"""Content/Library BC 외부 의존성 포트."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.history_entry import HistoryEntry


class IHistoryRepository(ABC):
    """HistoryEntry 영속화/조회 포트.

    구현체는 인프라 계층에서 제공 (Supabase / In-Memory).
    """

    @abstractmethod
    def save(self, entry: HistoryEntry) -> dict | None:
        """HistoryEntry 저장. 저장된 row dict 반환 (Supabase 응답 형식 호환)."""

    @abstractmethod
    def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """사용자 히스토리 페이지네이션 조회.

        관리자는 전체 사용자 데이터를 반환 (Identity BC의 RBAC 게이트는
        repository 내부에서 처리). 반환 형식은 기존 `get_histories` 호환.
        """

    @abstractmethod
    def update(self, user_id: str, report_id: str, updates: dict) -> bool:
        """부분 갱신 (마인드맵 캐싱 등). 성공 시 True."""

    @abstractmethod
    def toggle_favorite(self, user_id: str, report_id: str) -> dict:
        """is_favorite 토글. {'success': bool, 'is_favorite': bool}."""

    @abstractmethod
    def delete(self, user_id: str, report_id: str) -> bool:
        """삭제. 성공 시 True."""


__all__ = ["IHistoryRepository"]
