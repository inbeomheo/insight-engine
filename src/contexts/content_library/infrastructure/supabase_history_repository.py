"""SupabaseHistoryRepository — IHistoryRepository 구현.

Phase 5-a 시점: 기존 `services/data/supabase_service.py`의 함수를 호출하는
얇은 어댑터. 후속 PR에서 직접 `.table()` 호출로 전환 + 기존 함수 제거 예정.
Phase 5-c: save_many는 batch INSERT 직접 처리 (단건 N회 호출보다 효율).
"""
from __future__ import annotations

import logging

from src.shared.infrastructure.supabase_client import get_supabase

from ..application.ports import IHistoryRepository
from ..domain.history_entry import HistoryEntry

logger = logging.getLogger(__name__)


def _sanitize_text(text: object, max_length: int) -> str:
    """배치 저장용 입력 sanitize — 비문자열은 빈 문자열, 초과는 잘라냄."""
    if not isinstance(text, str):
        return ""
    return text[:max_length]


class SupabaseHistoryRepository(IHistoryRepository):
    """Supabase `ie_histories` 테이블 어댑터."""

    _TABLE = "ie_histories"
    _BATCH_LIMITS = {
        "report_id": 100,
        "url": 500,
        "title": 500,
        "style": 50,
        "content": 100_000,
        "html": 200_000,
        "transcript": 10_000,
    }

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

    def save_many(self, entries: list[HistoryEntry]) -> int:
        """단일 트랜잭션 INSERT — sanitize 후 batch 저장.

        Supabase 비활성/빈 입력 시 0. 모든 entry는 동일 owner_id 가정 (라우트가
        per-user 호출하므로 안전). 예외 시 graceful (경고 로그 + 0).
        """
        if not entries:
            return 0
        client = get_supabase()
        if client is None:
            return 0

        batch_data = [
            {
                "user_id": str(e.owner_id),
                "report_id": _sanitize_text(
                    str(e.report_id), self._BATCH_LIMITS["report_id"]
                ),
                "url": _sanitize_text(e.url, self._BATCH_LIMITS["url"]),
                "title": _sanitize_text(e.title, self._BATCH_LIMITS["title"]),
                "style": _sanitize_text(e.style, self._BATCH_LIMITS["style"]),
                "content": _sanitize_text(
                    e.content, self._BATCH_LIMITS["content"]
                ),
                "html": _sanitize_text(e.html, self._BATCH_LIMITS["html"]),
                "transcript": _sanitize_text(
                    e.transcript, self._BATCH_LIMITS["transcript"]
                ),
                "usage": e.usage,
                "elapsed_time": e.elapsed_time,
            }
            for e in entries
        ]
        try:
            client.table(self._TABLE).insert(batch_data).execute()
            return len(batch_data)
        except Exception as exc:
            logger.warning("배치 히스토리 저장 실패: %s", exc)
            return 0

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
