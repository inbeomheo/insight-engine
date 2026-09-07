"""Content/Library BC — 사용자 콘텐츠 히스토리 도메인.

Issue #19 (Phase 5-a) — `services/data/supabase_service.py`의 history CRUD
함수들을 도메인 인터페이스 계층으로 점진 이전.

편의 함수 (`save_history_entry`, `save_many_history_entries` 등)는 신규 호출처가
UseCase 인스턴스화 없이 즉시 사용할 수 있도록 제공한다. 내부 구현은
SupabaseHistoryRepository를 통해 기존 supabase_service 함수를 그대로 호출.
"""
from __future__ import annotations


def save_history_entry(
    user_id: str,
    data: dict,
    *,
    validated_access_token: str | None = None,
) -> dict | None:
    """편의 함수 — SaveHistoryEntryUseCase 단축 호출.

    Args:
        user_id: Identity BC AccountId 값
        data: 생성 결과 dict (id, url, title, style, content 등)
        validated_access_token: 요청 밖 작업에 명시 전달하는 검증 완료 JWT

    Returns:
        저장된 entry dict 또는 None (Supabase 비활성/user_id None인 경우)
    """
    from .application.use_cases import SaveHistoryEntryUseCase
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return SaveHistoryEntryUseCase(SupabaseHistoryRepository()).execute(
        user_id,
        data,
        validated_access_token=validated_access_token,
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


def fetch_admin_history_stats(days: int = 7) -> list[dict]:
    """편의 함수 — 모든 사용자 최근 N일 히스토리 raw 조회 (admin 대시보드).

    통계 가공은 호출처 담당. Supabase 비활성/예외 시 빈 리스트.
    """
    from .infrastructure.supabase_history_repository import (
        SupabaseHistoryRepository,
    )
    return SupabaseHistoryRepository().fetch_recent_for_admin(days)


__all__ = [
    "save_history_entry",
    "save_many_history_entries",
    "fetch_admin_history_stats",
]
