"""Identity & Access BC 도메인 이벤트.

각 이벤트는 불변 dataclass이며 `occurred_at` 타임스탬프를 포함한다.
이벤트는 도메인 객체 변경 후 어플리케이션 계층에서 발행하며,
다른 BC는 이벤트 버스를 통해서만 구독한다 (Phase 3+ 활성화).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.shared.domain.value_objects import AccountId


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """모든 도메인 이벤트의 베이스."""

    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AccountCreated(DomainEvent):
    """새 UserAccount가 생성됨."""

    account_id: AccountId
    email: str


@dataclass(frozen=True, slots=True)
class QuotaConsumed(DomainEvent):
    """사용량 카운터가 차감됨.

    Billing BC가 구독하여 크레딧 회수와 동기화 가능.
    """

    account_id: AccountId
    amount: int
    remaining: int


@dataclass(frozen=True, slots=True)
class ApiKeyAdded(DomainEvent):
    """BYO API 키가 새로 등록됨.

    Audit BC가 구독하여 보안 감사 로그 기록.
    """

    account_id: AccountId
    provider: str
    label: str


__all__ = [
    "AccountCreated",
    "ApiKeyAdded",
    "DomainEvent",
    "QuotaConsumed",
]
