"""Identity & Access BC의 핵심 Aggregate — UserAccount.

UserAccount는 인증 가능한 사용자 단위이며, 다음 자식 엔티티/VO를 포함한다.

- ApiKey[]       : BYO API 키 (평문은 보유 X, masked만 보관)
- UsageQuota     : 일일 사용량 카운터
- CreditBalance  : 결제 기반 크레딧 잔액
- RbacRole[]     : 역할 (admin/owner/editor/viewer)

도메인 모델은 외부 인프라(DB, HTTP, Flask 등)에 의존하지 않는다.
영속화 어댑터(`infrastructure/`)가 본 모델 ↔ Supabase 행을 변환한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.contexts.identity.domain.exceptions import (
    InsufficientCredits,
    InvalidApiKey,
    QuotaExceeded,
)
from src.shared.domain.value_objects import AccountId


# ---------------------------------------------------------------------------
# 자식 엔티티 / 값 객체
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApiKey:
    """BYO(Bring Your Own) API 키 메타데이터.

    평문 키는 절대로 본 객체에 저장하지 않는다 (`IApiKeyVault` 경유).
    `masked_key`는 UI 표시용으로 마지막 4자리만 남긴 형태 (예: `****abcd`).
    """

    provider: str  # gemini, deepseek, zhipu, openai, anthropic, openrouter, ollama
    masked_key: str
    label: str
    is_active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.provider or not isinstance(self.provider, str):
            raise InvalidApiKey("ApiKey.provider must be a non-empty string")
        if not self.label or not isinstance(self.label, str):
            raise InvalidApiKey("ApiKey.label must be a non-empty string")
        if "*" not in self.masked_key:
            # 마스킹이 안 된 평문이 들어왔을 가능성 — 방어
            raise InvalidApiKey(
                "ApiKey.masked_key must be masked (contain '*'). "
                "Store plaintext via IApiKeyVault, not in the domain model."
            )


@dataclass
class UsageQuota:
    """일일 사용량 쿼터.

    `decrement_usage_safe` Supabase RPC와 동치인 로직을 도메인 객체로 표현한다.
    원자적 차감은 인프라 계층에서 수행하고, 이 객체는 메모리 상의 상태를 관리한다.
    """

    daily_limit: int = 20
    used_today: int = 0
    reset_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.daily_limit < 0:
            raise ValueError("UsageQuota.daily_limit must be non-negative")
        if self.used_today < 0:
            raise ValueError("UsageQuota.used_today must be non-negative")

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_today)

    def has_remaining(self) -> bool:
        """남은 사용량이 있으면 True."""
        return self.used_today < self.daily_limit

    def consume(self, amount: int = 1) -> None:
        """사용량 차감. 한도 초과 시 `QuotaExceeded` raise."""
        if amount < 1:
            raise ValueError("UsageQuota.consume amount must be >= 1")
        if self.used_today + amount > self.daily_limit:
            raise QuotaExceeded(
                f"quota exceeded: used={self.used_today}, "
                f"limit={self.daily_limit}, requested={amount}"
            )
        self.used_today += amount

    def reset(self) -> None:
        """일일 카운터 리셋 (스케줄러가 자정에 호출)."""
        self.used_today = 0


@dataclass
class CreditBalance:
    """결제 기반 크레딧 잔액.

    잔액은 음수가 될 수 없다. 차감 시 부족하면 `InsufficientCredits` raise.
    """

    balance: int = 0

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("CreditBalance.balance must be non-negative")

    def can_afford(self, amount: int) -> bool:
        if amount < 0:
            raise ValueError("CreditBalance.can_afford amount must be non-negative")
        return self.balance >= amount

    def debit(self, amount: int) -> None:
        """크레딧 차감."""
        if amount < 1:
            raise ValueError("CreditBalance.debit amount must be >= 1")
        if not self.can_afford(amount):
            raise InsufficientCredits(
                f"insufficient credits: balance={self.balance}, requested={amount}"
            )
        self.balance -= amount

    def credit(self, amount: int) -> None:
        """크레딧 충전."""
        if amount < 1:
            raise ValueError("CreditBalance.credit amount must be >= 1")
        self.balance += amount


@dataclass(frozen=True, slots=True)
class RbacRole:
    """역할 기반 접근 제어 (Role-Based Access Control) 역할."""

    name: str  # admin, owner, editor, viewer

    _VALID_ROLES = frozenset({"admin", "owner", "editor", "viewer"})

    def __post_init__(self) -> None:
        if self.name not in self._VALID_ROLES:
            raise ValueError(
                f"RbacRole.name must be one of {sorted(self._VALID_ROLES)}, "
                f"got {self.name!r}"
            )

    def is_admin(self) -> bool:
        return self.name == "admin"

    def is_owner(self) -> bool:
        return self.name == "owner"

    def can_edit(self) -> bool:
        return self.name in {"admin", "owner", "editor"}


# ---------------------------------------------------------------------------
# Aggregate Root
# ---------------------------------------------------------------------------


@dataclass
class UserAccount:
    """Identity & Access Aggregate Root.

    UserAccount는 인증 가능한 사용자 단위. Supabase `auth.users.id`를
    `AccountId`로 사용한다.

    자식 엔티티: ApiKey[], UsageQuota, CreditBalance, RbacRole[].

    이 객체는 비즈니스 불변식(invariant)을 보장하는 단위로,
    모든 사용량/크레딧/키 관련 상태 변경은 본 객체의 메서드를 거쳐야 한다.
    """

    account_id: AccountId
    email: str
    quota: UsageQuota
    credits: CreditBalance
    api_keys: list[ApiKey] = field(default_factory=list)
    roles: list[RbacRole] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or "@" not in self.email:
            raise ValueError(f"UserAccount.email is invalid: {self.email!r}")

    # ----- Role -----
    def is_admin(self) -> bool:
        """admin 역할 보유 여부."""
        return any(role.is_admin() for role in self.roles)

    # ----- API Keys -----
    def add_api_key(self, key: ApiKey) -> None:
        """BYO API 키 추가. 동일 (provider, label) 중복 금지."""
        for existing in self.api_keys:
            if existing.provider == key.provider and existing.label == key.label:
                raise InvalidApiKey(
                    f"duplicate API key: provider={key.provider}, label={key.label}"
                )
        self.api_keys.append(key)

    def remove_api_key(self, provider: str, label: str) -> None:
        """지정된 (provider, label) 키 제거."""
        for idx, existing in enumerate(self.api_keys):
            if existing.provider == provider and existing.label == label:
                del self.api_keys[idx]
                return
        raise InvalidApiKey(f"API key not found: provider={provider}, label={label}")

    def get_active_key(self, provider: str) -> Optional[ApiKey]:
        """주어진 프로바이더의 활성 키 중 가장 먼저 등록된 것 반환."""
        for key in self.api_keys:
            if key.provider == provider and key.is_active:
                return key
        return None

    # ----- Quota -----
    def enforce_quota(self) -> None:
        """남은 사용량이 없으면 `QuotaExceeded` raise.

        실제 차감은 인프라 계층(`IAccountRepository.consume_quota_atomic`)이
        원자적으로 수행한다. 본 메서드는 도메인 객체 메모리 상태 기준 검증용.
        """
        if not self.quota.has_remaining():
            raise QuotaExceeded(
                f"daily quota exceeded for {self.account_id}: "
                f"used={self.quota.used_today}, limit={self.quota.daily_limit}"
            )


__all__ = [
    "ApiKey",
    "CreditBalance",
    "RbacRole",
    "UsageQuota",
    "UserAccount",
]
