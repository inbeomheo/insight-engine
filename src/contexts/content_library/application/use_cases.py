"""Content/Library UseCase — Repository 위임형."""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.history_entry import HistoryEntry
from .ports import IHistoryRepository


@dataclass(slots=True)
class SaveHistoryEntryUseCase:
    """생성 직후 호출 — dict를 HistoryEntry로 변환 후 저장.

    user_id가 None이면 비로그인 사용자로 간주, 저장 생략 + None 반환
    (기존 supabase_service.save_history 의도된 동작).
    """

    repository: IHistoryRepository

    def execute(self, user_id: str | None, data: dict) -> dict | None:
        if not user_id:
            return None
        try:
            entry = HistoryEntry.from_dict(data, user_id)
        except ValueError:
            return None
        return self.repository.save(entry)


@dataclass(slots=True)
class ListHistoryEntriesUseCase:
    """사용자 히스토리 조회 (페이지네이션)."""

    repository: IHistoryRepository

    def execute(
        self, user_id: str | None, page: int = 1, per_page: int = 20
    ) -> dict:
        if not user_id:
            return {
                "histories": [],
                "total": 0,
                "page": 1,
                "per_page": per_page,
                "total_pages": 0,
                "has_more": False,
            }
        return self.repository.list_for_user(user_id, page, per_page)


@dataclass(slots=True)
class UpdateHistoryEntryUseCase:
    """부분 갱신."""

    repository: IHistoryRepository

    def execute(
        self, user_id: str | None, report_id: str, updates: dict
    ) -> bool:
        if not user_id or not report_id:
            return False
        return self.repository.update(user_id, report_id, updates)


@dataclass(slots=True)
class ToggleFavoriteUseCase:
    """즐겨찾기 토글."""

    repository: IHistoryRepository

    def execute(self, user_id: str | None, report_id: str) -> dict:
        if not user_id or not report_id:
            return {"success": False, "error": "Not authenticated"}
        return self.repository.toggle_favorite(user_id, report_id)


@dataclass(slots=True)
class DeleteHistoryEntryUseCase:
    """삭제."""

    repository: IHistoryRepository

    def execute(self, user_id: str | None, report_id: str) -> bool:
        if not user_id or not report_id:
            return False
        return self.repository.delete(user_id, report_id)


__all__ = [
    "SaveHistoryEntryUseCase",
    "ListHistoryEntriesUseCase",
    "UpdateHistoryEntryUseCase",
    "ToggleFavoriteUseCase",
    "DeleteHistoryEntryUseCase",
]
