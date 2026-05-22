"""SupabaseHistoryRepository — IHistoryRepository 구현.

Phase 5-a 시점: 기존 `services/data/supabase_service.py`의 함수를 호출하는
얇은 어댑터. 후속 PR에서 직접 `.table()` 호출로 전환 + 기존 함수 제거 예정.
"""
from __future__ import annotations

from ..application.ports import IHistoryRepository
from ..domain.history_entry import HistoryEntry


class SupabaseHistoryRepository(IHistoryRepository):
    """Supabase `ie_histories` 테이블 어댑터."""

    def save(self, entry: HistoryEntry) -> dict | None:
        from services.data.supabase_service import save_history as _save
        # 기존 함수는 dict 입력. HistoryEntry → dict 역변환은 to_row 사용.
        # 다만 frontend dict 형식과 to_row 결과가 다르므로 from_dict 입력 dict로 fallback.
        data = entry.to_row()
        # `_save`는 user_id를 별도 인자로 받고 자신이 row 조립. 기존 호환을 위해
        # dict에 keys 그대로 매핑된 형식으로 전달.
        legacy_data = {
            "id": str(entry.report_id),
            "url": entry.url,
            "title": entry.title,
            "style": entry.style,
            "content": entry.content,
            "html": entry.html,
            "transcript": entry.transcript,
            "transcript_source": entry.transcript_source,
            "mindmapMarkdown": entry.mindmap_markdown,
            "keywords": entry.keywords,
            "usage": entry.usage,
            "elapsed_time": entry.elapsed_time,
        }
        return _save(str(entry.owner_id), legacy_data)

    def list_for_user(
        self, user_id: str, page: int = 1, per_page: int = 20
    ) -> dict:
        from services.data.supabase_service import get_histories as _list
        return _list(user_id, page, per_page)

    def update(self, user_id: str, report_id: str, updates: dict) -> bool:
        from services.data.supabase_service import update_history as _update
        return _update(user_id, report_id, updates)

    def toggle_favorite(self, user_id: str, report_id: str) -> dict:
        from services.data.supabase_service import toggle_favorite as _toggle
        return _toggle(user_id, report_id)

    def delete(self, user_id: str, report_id: str) -> bool:
        from services.data.supabase_service import delete_history as _delete
        return _delete(user_id, report_id)


__all__ = ["SupabaseHistoryRepository"]
