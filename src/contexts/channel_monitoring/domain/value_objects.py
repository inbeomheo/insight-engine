"""Channel Monitoring 도메인 VO."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelId:
    """YouTube 채널 식별자. UCxxxx 형태가 일반적이지만 형식 검증은 하지 않음
    (외부 표기 변경에 유연하게)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ChannelId는 비어있지 않은 문자열이어야 합니다.")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class MonitorOwnerId:
    """모니터 소유 사용자 — Identity BC AccountId 값."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError(
                "MonitorOwnerId는 비어있지 않은 문자열이어야 합니다."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Interval:
    """폴링 간격 (분). 최소 5분."""

    minutes: int

    MIN_MINUTES = 5
    MAX_MINUTES = 1440  # 24h

    def __post_init__(self) -> None:
        if not isinstance(self.minutes, int):
            raise ValueError("Interval은 정수여야 합니다.")
        if self.minutes < self.MIN_MINUTES:
            raise ValueError(
                f"Interval은 최소 {self.MIN_MINUTES}분 이상이어야 합니다."
            )
        if self.minutes > self.MAX_MINUTES:
            raise ValueError(
                f"Interval은 최대 {self.MAX_MINUTES}분 이하여야 합니다."
            )


__all__ = ["ChannelId", "MonitorOwnerId", "Interval"]
