"""ChannelSubscription Aggregate Root."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .value_objects import ChannelId, Interval, MonitorOwnerId


@dataclass(slots=True)
class ChannelSubscription:
    """YouTube 채널 1건 모니터링 등록 = 1 레코드."""

    owner_id: MonitorOwnerId
    channel_id: ChannelId
    channel_title: str = ""
    style_id: str = "blog_seo"
    modifiers: dict[str, Any] = field(default_factory=dict)
    interval: Interval = field(default_factory=lambda: Interval(minutes=30))
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict, owner_id: str) -> "ChannelSubscription":
        """프론트엔드 요청 dict → ChannelSubscription 변환.

        필수: channel_id. 모디파이어/스타일/간격은 기본값 적용.
        """
        channel_id_value = (data.get("channel_id") or "").strip()
        if not channel_id_value:
            raise ValueError("channel_id가 필요합니다.")

        modifiers = data.get("modifiers") or {
            "length": "medium",
            "writing_style": "conversational",
            "language": "ko",
        }
        interval_minutes = int(data.get("interval_minutes") or 30)

        return cls(
            owner_id=MonitorOwnerId(owner_id),
            channel_id=ChannelId(channel_id_value),
            channel_title=(data.get("channel_title") or "").strip(),
            style_id=data.get("style_id") or "blog_seo",
            modifiers=modifiers,
            interval=Interval(minutes=interval_minutes),
            is_active=True,
        )

    def to_row(self) -> dict:
        """Supabase INSERT용 row."""
        return {
            "user_id": str(self.owner_id),
            "channel_id": str(self.channel_id),
            "channel_title": self.channel_title,
            "style_id": self.style_id,
            "modifiers": self.modifiers,
            "interval_minutes": self.interval.minutes,
            "is_active": self.is_active,
        }


__all__ = ["ChannelSubscription"]
