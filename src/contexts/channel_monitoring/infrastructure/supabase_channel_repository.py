"""SupabaseChannelMonitorRepository — IChannelMonitorRepository 구현.

Phase 5-c — `routes/auth/channel_monitoring.py`의 직접 `.table()` 호출 5건을
이 어댑터로 흡수. 기존 `services/data/supabase_service.py`에는 채널 모니터
함수가 없었으므로 lazy wrap이 아닌 직접 `.table()` 호출로 작성.
"""
from __future__ import annotations

import logging

from src.shared.infrastructure.supabase_client import get_supabase

from ..application.ports import IChannelMonitorRepository
from ..domain.channel_subscription import ChannelSubscription

logger = logging.getLogger(__name__)


class SupabaseChannelMonitorRepository(IChannelMonitorRepository):
    """Supabase `ie_channel_monitors` 테이블 어댑터."""

    _TABLE = "ie_channel_monitors"

    def register(self, subscription: ChannelSubscription) -> dict | None:
        client = get_supabase()
        if client is None:
            return None
        try:
            result = client.table(self._TABLE).insert(
                subscription.to_row()
            ).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("채널 모니터 등록 실패: %s", exc)
            raise

    def list_for_owner(self, user_id: str) -> list[dict]:
        client = get_supabase()
        if client is None:
            return []
        try:
            result = (
                client.table(self._TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("채널 모니터 목록 조회 실패: %s", exc)
            raise

    def delete(self, user_id: str, monitor_id: str) -> bool:
        client = get_supabase()
        if client is None:
            return False
        try:
            result = (
                client.table(self._TABLE)
                .delete()
                .eq("id", monitor_id)
                .eq("user_id", user_id)
                .execute()
            )
            # 삭제된 행이 없으면(존재하지 않거나 타 사용자 소유) False —
            # PostgREST delete는 삭제된 행을 result.data로 반환하므로 이를 검사한다.
            # 이를 무시하고 True를 반환하면 라우트의 404 분기가 무력화된다.
            return bool(result.data)
        except Exception as exc:
            logger.error("채널 모니터 삭제 실패: %s", exc)
            raise


__all__ = ["SupabaseChannelMonitorRepository"]
