"""Channel Monitoring UseCase."""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.channel_subscription import ChannelSubscription
from .ports import IChannelMonitorRepository


@dataclass(slots=True)
class RegisterChannelMonitorUseCase:
    """신규 채널 모니터 등록."""

    repository: IChannelMonitorRepository

    def execute(self, user_id: str | None, data: dict) -> dict | None:
        if not user_id:
            return None
        try:
            subscription = ChannelSubscription.from_dict(data, user_id)
        except ValueError:
            return None
        return self.repository.register(subscription)


@dataclass(slots=True)
class ListChannelMonitorsUseCase:
    """등록 모니터 목록 조회."""

    repository: IChannelMonitorRepository

    def execute(self, user_id: str | None) -> list[dict]:
        if not user_id:
            return []
        return self.repository.list_for_owner(user_id)


@dataclass(slots=True)
class DeleteChannelMonitorUseCase:
    """모니터 삭제."""

    repository: IChannelMonitorRepository

    def execute(self, user_id: str | None, monitor_id: str) -> bool:
        if not user_id or not monitor_id:
            return False
        return self.repository.delete(user_id, monitor_id)


__all__ = [
    "RegisterChannelMonitorUseCase",
    "ListChannelMonitorsUseCase",
    "DeleteChannelMonitorUseCase",
]
