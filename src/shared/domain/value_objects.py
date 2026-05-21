"""BC 공통 값 객체 (Value Object) 정의.

모든 VO는 불변(frozen=True)이며, 생성 시점에 자체 검증을 수행한다.
ID 타입은 `@dataclass(frozen=True)` 기반 강타입 래퍼로 정의하여
str/UUID와 혼동되지 않도록 한다.

설계 원칙
---------
- 자체 검증: `__post_init__`에서 유효성을 보장 (raise ValueError)
- 불변성: frozen=True
- 동등성: dataclass 기본 `__eq__` + `__hash__` 사용
- 직렬화: `str(...)` 로 평탄화 (DB 영속화 시 자동 호환)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Identifier Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UserId:
    """플랫폼 단위의 사용자 식별자 (auth provider native ID).

    실제 값은 Supabase `auth.users.id` UUID 문자열을 보관한다.
    `AccountId`와 의미는 동일하지만, 인증 계층(Auth Provider)에서 사용되는
    네이밍을 유지하기 위해 별도 타입으로 둔다.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("UserId.value must be a non-empty string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AccountId:
    """Identity & Access BC의 Aggregate Root 식별자.

    내부적으로 `auth.users.id` UUID 문자열을 사용한다.
    Domain 계층은 이 타입에만 의존하고, 인프라 계층에서 str로 풀어서 사용한다.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("AccountId.value must be a non-empty string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class WorkspaceId:
    """Workspace BC의 Aggregate Root 식별자."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("WorkspaceId.value must be a non-empty string")

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Money / Credit Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Money:
    """통화 금액 (정수 최소 단위 = cents/원).

    API 사양
    --------
    - `amount_cents`는 **항상 정수**이며 통화의 최소 단위로 표현된다.
      - USD/EUR: cents (예: `Money(1000, "USD")` = $10.00)
      - KRW: 원 단위 정수 (KRW는 분수 단위가 없으므로 `Money(1000, "KRW")` = ₩1,000)
      - JPY: 엔 단위 정수 (JPY도 분수 단위 미사용)
    - 부동소수점 오차를 회피하기 위해 float 입력은 금지된다.

    생성 방법
    --------
    - 직접 생성: `Money(amount_cents=1000, currency="USD")` (저수준, 명시적)
    - 팩토리: `Money.from_won(1000)` / `Money.from_cents(1000)` (의도 명확)
    - `bool` 입력은 `int` 서브타입이지만 명백히 의미가 다르므로 금지된다.
    """

    amount_cents: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        # bool은 int의 서브타입이지만 의도된 사용이 아님
        if isinstance(self.amount_cents, bool) or not isinstance(self.amount_cents, int):
            raise ValueError("Money.amount_cents must be an integer (cents/원)")
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValueError("Money.currency must be a 3-letter ISO code")

    # ----- 팩토리 메서드 -------------------------------------------------
    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        """정수 cents (또는 통화의 최소 단위)로부터 생성.

        예: `Money.from_cents(1000, "USD")` → $10.00
        """
        return cls(amount_cents=cents, currency=currency)

    @classmethod
    def from_won(cls, won: int) -> "Money":
        """원(KRW) 단위 정수로부터 생성.

        KRW는 분수 단위가 없으므로 `won` 그대로 `amount_cents`에 저장된다.
        예: `Money.from_won(1000)` → ₩1,000
        """
        return cls(amount_cents=won, currency="KRW")

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot operate on different currencies: {self.currency} vs {other.currency}"
            )

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount_cents + other.amount_cents, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount_cents - other.amount_cents, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount_cents < other.amount_cents

    def __le__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount_cents <= other.amount_cents

    def __gt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount_cents > other.amount_cents

    def __ge__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount_cents >= other.amount_cents

    def is_zero(self) -> bool:
        return self.amount_cents == 0

    def is_negative(self) -> bool:
        return self.amount_cents < 0


@dataclass(frozen=True, slots=True)
class CreditAmount:
    """크레딧 수량 (양수=충전, 음수=소진 추적용).

    `CreditBalance.balance`와는 다르게 이 VO는 부호 있는 정수를 허용하여
    "차감/충전 이벤트"를 표현한다 (예: `CreditAmount(-5)` = 5 차감).
    """

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise ValueError("CreditAmount.value must be an integer")

    def __add__(self, other: "CreditAmount") -> "CreditAmount":
        return CreditAmount(self.value + other.value)

    def __neg__(self) -> "CreditAmount":
        return CreditAmount(-self.value)

    def is_debit(self) -> bool:
        """차감 이벤트 여부 (음수)."""
        return self.value < 0

    def is_credit(self) -> bool:
        """충전 이벤트 여부 (양수)."""
        return self.value > 0


__all__ = [
    "AccountId",
    "CreditAmount",
    "Money",
    "UserId",
    "WorkspaceId",
]
