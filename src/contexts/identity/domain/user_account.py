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
from typing import Iterable, Optional

from src.contexts.identity.domain.constants import (
    DEFAULT_DAILY_LIMIT,
    DEFAULT_INITIAL_CREDITS,
)
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

    daily_limit: int = DEFAULT_DAILY_LIMIT
    used_today: int = 0
    reset_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.daily_limit < 0:
            raise ValueError("UsageQuota.daily_limit must be non-negative")
        if self.used_today < 0:
            raise ValueError("UsageQuota.used_today must be non-negative")

    @classmethod
    def create_default(cls, used_today: int = 0) -> "UsageQuota":
        """기본 일일 한도(`DEFAULT_DAILY_LIMIT`)로 UsageQuota를 생성.

        한도를 환경/플랜별로 바꿔야 할 때는 `daily_limit`을 직접 넘기거나,
        Phase 5+에서 `IConfigGateway` 같은 포트를 통해 외부화 예정.
        """
        return cls(daily_limit=DEFAULT_DAILY_LIMIT, used_today=used_today)

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

    balance: int = DEFAULT_INITIAL_CREDITS

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


class UserAccount:
    """Identity & Access Aggregate Root.

    UserAccount는 인증 가능한 사용자 단위. Supabase `auth.users.id`를
    `AccountId`로 사용한다.

    자식 엔티티: ApiKey[], UsageQuota, CreditBalance, RbacRole[].

    이 객체는 비즈니스 불변식(invariant)을 보장하는 단위로,
    모든 사용량/크레딧/키 관련 상태 변경은 본 객체의 메서드를 거쳐야 한다.

    캡슐화
    ------
    `api_keys`, `roles`는 외부에서 직접 mutation할 수 없다 (`tuple` property).
    추가/제거는 반드시 `add_api_key`, `remove_api_key`, `add_role` 등 메서드를
    거쳐야 한다. 생성자 호환을 위해 `api_keys=[...]`, `roles=[...]` 키워드
    인자는 그대로 받지만, 내부에서 private list로 복사된다.

    참고: 일반 dataclass 대신 명시적 `__init__`을 정의한다 — property와 동일
    이름의 dataclass field는 충돌하기 때문.
    """

    __slots__ = (
        "account_id",
        "email",
        "quota",
        "credits",
        "_api_keys",
        "_roles",
    )

    def __init__(
        self,
        account_id: AccountId | str,
        email: str,
        quota: UsageQuota,
        credits: CreditBalance,
        api_keys: Optional[Iterable[ApiKey]] = None,
        roles: Optional[Iterable[RbacRole]] = None,
    ) -> None:
        # AccountId 자동 변환 (호출 편의)
        if isinstance(account_id, str):
            account_id = AccountId(value=account_id)
        if not isinstance(email, str) or "@" not in email:
            raise ValueError(f"UserAccount.email is invalid: {email!r}")
        if not isinstance(quota, UsageQuota):
            raise TypeError("UserAccount.quota must be UsageQuota")
        if not isinstance(credits, CreditBalance):
            raise TypeError("UserAccount.credits must be CreditBalance")

        self.account_id: AccountId = account_id
        self.email: str = email
        self.quota: UsageQuota = quota
        self.credits: CreditBalance = credits
        # 외부 참조 격리: 생성자가 받은 list/iterable을 내부 list로 복사
        self._api_keys: list[ApiKey] = list(api_keys or [])
        self._roles: list[RbacRole] = list(roles or [])

    def __repr__(self) -> str:  # 디버깅 편의
        return (
            f"UserAccount(account_id={self.account_id!r}, email={self.email!r}, "
            f"quota={self.quota!r}, credits={self.credits!r}, "
            f"api_keys=<{len(self._api_keys)} keys>, roles=<{len(self._roles)} roles>)"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserAccount):
            return NotImplemented
        return (
            self.account_id == other.account_id
            and self.email == other.email
            and self.quota == other.quota
            and self.credits == other.credits
            and self._api_keys == other._api_keys
            and self._roles == other._roles
        )

    __hash__ = None  # type: ignore[assignment]  # 가변 Aggregate라 hash 불가

    # ----- Role -----
    @property
    def roles(self) -> tuple[RbacRole, ...]:
        """역할 튜플 (외부 mutation 불가)."""
        return tuple(self._roles)

    def add_role(self, role: RbacRole) -> None:
        """역할 추가 (중복 시 무시)."""
        if not isinstance(role, RbacRole):
            raise TypeError("add_role expects RbacRole instance")
        if role not in self._roles:
            self._roles.append(role)

    def is_admin(self) -> bool:
        """admin 역할 보유 여부."""
        return any(role.is_admin() for role in self._roles)

    # ----- API Keys -----
    @property
    def api_keys(self) -> tuple[ApiKey, ...]:
        """BYO API 키 튜플 (외부 mutation 불가)."""
        return tuple(self._api_keys)

    def add_api_key(self, key: ApiKey) -> None:
        """BYO API 키 추가. 동일 (provider, label) 중복 금지."""
        if not isinstance(key, ApiKey):
            raise TypeError("add_api_key expects ApiKey instance")
        for existing in self._api_keys:
            if existing.provider == key.provider and existing.label == key.label:
                raise InvalidApiKey(
                    f"duplicate API key: provider={key.provider}, label={key.label}"
                )
        self._api_keys.append(key)

    def remove_api_key(self, provider: str, label: str) -> None:
        """지정된 (provider, label) 키 제거."""
        for idx, existing in enumerate(self._api_keys):
            if existing.provider == provider and existing.label == label:
                del self._api_keys[idx]
                return
        raise InvalidApiKey(f"API key not found: provider={provider}, label={label}")

    def get_active_key(self, provider: str) -> Optional[ApiKey]:
        """주어진 프로바이더의 활성 키 중 가장 먼저 등록된 것 반환."""
        for key in self._api_keys:
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
