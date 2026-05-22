"""Content/Library 도메인 VO."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReportId:
    """클라이언트 발급 UUID. 동일 콘텐츠를 식별."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ReportId는 비어있지 않은 문자열이어야 합니다.")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class OwnerId:
    """소유 사용자 — Identity BC AccountId 값과 일치.

    Content/Library BC는 Identity BC에 직접 의존하지 않고 값만 보존
    (cross-BC 결합 최소화).
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            raise ValueError("OwnerId는 비어있지 않은 문자열이어야 합니다.")

    def __str__(self) -> str:
        return self.value


__all__ = ["ReportId", "OwnerId"]
