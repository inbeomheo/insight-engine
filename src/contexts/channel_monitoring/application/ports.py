"""Channel Monitoring BC 외부 의존성 포트."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.channel_subscription import ChannelSubscription


class IChannelMonitorRepository(ABC):
    """채널 모니터 영속화 포트."""

    @abstractmethod
    def register(self, subscription: ChannelSubscription) -> dict | None:
        """신규 등록. INSERT 결과 row dict 반환 (Supabase 응답 호환)."""

    @abstractmethod
    def list_for_owner(self, user_id: str) -> list[dict]:
        """사용자 등록 모니터 목록 조회 (최신 순)."""

    @abstractmethod
    def delete(self, user_id: str, monitor_id: str) -> bool:
        """삭제. 성공 시 True."""


__all__ = ["IChannelMonitorRepository"]
