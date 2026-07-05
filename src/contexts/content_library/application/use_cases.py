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


__all__ = [
    "SaveHistoryEntryUseCase",
]
