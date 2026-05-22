"""Content/Library BC — 사용자 콘텐츠 히스토리 도메인.

Issue #19 (Phase 5-a) — `services/data/supabase_service.py`의 history CRUD
함수들을 도메인 인터페이스 계층으로 점진 이전.

편의 함수 (`save_history_entry`, `list_history_entries` 등)는 신규 호출처가
UseCase 인스턴스화 없이 즉시 사용할 수 있도록 제공한다. 내부 구현은
SupabaseHistoryRepository를 통해 기존 supabase_service 함수를 그대로 호출.
"""
from __future__ import annotations


def save_history_entry(user_id: str, data: dict) -> dict | None:
    """편의 함수 — SaveHistoryEntryUseCase 단축 호출.

    Args:
        user_id: Identity BC AccountId 값
        data: 생성 결과 dict (id, url, title, style, content 등)

    Returns:
        저장된 entry dict 또는 None (Supabase 비활성/user_id None인 경우)
    """
    from .application.use_cases import SaveHistoryEntryUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return SaveHistoryEntryUseCase(SupabaseHistoryRepository()).execute(
        user_id, data
    )


def save_many_history_entries(user_id: str, data_list: list[dict]) -> int:
    """편의 함수 — 다수 HistoryEntry를 단일 batch INSERT.

    각 dict에서 HistoryEntry 변환 실패 항목은 silent skip. user_id 누락 시 0.
    """
    if not user_id or not data_list:
        return 0
    from .domain.history_entry import HistoryEntry
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    entries: list[HistoryEntry] = []
    for d in data_list:
        try:
            entries.append(HistoryEntry.from_dict(d, user_id))
        except ValueError:
            continue
    return SupabaseHistoryRepository().save_many(entries)


def list_history_entries(
    user_id: str, page: int = 1, per_page: int = 20
) -> dict:
    """편의 함수 — ListHistoryEntriesUseCase 단축 호출."""
    from .application.use_cases import ListHistoryEntriesUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return ListHistoryEntriesUseCase(SupabaseHistoryRepository()).execute(
        user_id, page, per_page
    )


def update_history_entry(
    user_id: str, report_id: str, updates: dict
) -> bool:
    """편의 함수 — UpdateHistoryEntryUseCase 단축 호출."""
    from .application.use_cases import UpdateHistoryEntryUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return UpdateHistoryEntryUseCase(SupabaseHistoryRepository()).execute(
        user_id, report_id, updates
    )


def toggle_favorite(user_id: str, report_id: str) -> dict:
    """편의 함수 — ToggleFavoriteUseCase 단축 호출."""
    from .application.use_cases import ToggleFavoriteUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return ToggleFavoriteUseCase(SupabaseHistoryRepository()).execute(
        user_id, report_id
    )


def delete_history_entry(user_id: str, report_id: str) -> bool:
    """편의 함수 — DeleteHistoryEntryUseCase 단축 호출."""
    from .application.use_cases import DeleteHistoryEntryUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return DeleteHistoryEntryUseCase(SupabaseHistoryRepository()).execute(
        user_id, report_id
    )


__all__ = [
    "save_history_entry",
    "save_many_history_entries",
    "list_history_entries",
    "update_history_entry",
    "toggle_favorite",
    "delete_history_entry",
]
