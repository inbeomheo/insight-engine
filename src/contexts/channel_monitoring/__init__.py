"""Channel Monitoring BC — YouTube 채널 신규 업로드 감지 도메인.

Issue #19 (Phase 5-c) — `routes/auth/channel_monitoring.py`의 직접 `.table()`
호출 5건을 BC 경유로 정리.

편의 함수는 라우트가 UseCase 인스턴스화 없이 즉시 사용할 수 있도록 제공.
"""
from __future__ import annotations


def register_channel_monitor(user_id: str, data: dict) -> dict | None:
    """편의 함수 — RegisterChannelMonitorUseCase 단축 호출."""
    from .application.use_cases import RegisterChannelMonitorUseCase
    from .infrastructure.supabase_channel_repository import (
        SupabaseChannelMonitorRepository,
    )
    return RegisterChannelMonitorUseCase(
        SupabaseChannelMonitorRepository()
    ).execute(user_id, data)


def list_channel_monitors(user_id: str) -> list[dict]:
    """편의 함수 — ListChannelMonitorsUseCase 단축 호출."""
    from .application.use_cases import ListChannelMonitorsUseCase
    from .infrastructure.supabase_channel_repository import (
        SupabaseChannelMonitorRepository,
    )
    return ListChannelMonitorsUseCase(
        SupabaseChannelMonitorRepository()
    ).execute(user_id)


def delete_channel_monitor(user_id: str, monitor_id: str) -> bool:
    """편의 함수 — DeleteChannelMonitorUseCase 단축 호출."""
    from .application.use_cases import DeleteChannelMonitorUseCase
    from .infrastructure.supabase_channel_repository import (
        SupabaseChannelMonitorRepository,
    )
    return DeleteChannelMonitorUseCase(
        SupabaseChannelMonitorRepository()
    ).execute(user_id, monitor_id)


__all__ = [
    "register_channel_monitor",
    "list_channel_monitors",
    "delete_channel_monitor",
]
