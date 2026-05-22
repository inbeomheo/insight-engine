"""Identity & Shared 도메인의 값 객체(VO) 단위 테스트.

- `Money`: 최소 단위(cents/원) 정수성, 통화 검증, 팩토리, 동일/다른 통화 산술
- `AccountId` / `UserId` / `WorkspaceId`: 빈/타입 검증 + 불변성(frozen)
"""

from __future__ import annotations

import pytest

from src.shared.domain.value_objects import (
    AccountId,
    CreditAmount,
    Money,
    UserId,
    WorkspaceId,
)


class TestMoney:
    def test_from_won_creates_krw_money(self) -> None:
        m = Money.from_won(1000)
        assert m.amount_cents == 1000
        assert m.currency == "KRW"

    def test_from_cents_default_usd(self) -> None:
        m = Money.from_cents(1500)
        assert m.amount_cents == 1500
        assert m.currency == "USD"

    def test_from_cents_explicit_currency(self) -> None:
        m = Money.from_cents(2000, "EUR")
        assert m.currency == "EUR"

    def test_addition_same_currency(self) -> None:
        a = Money.from_won(1000)
        b = Money.from_won(500)
        result = a + b
        assert result == Money.from_won(1500)

    def test_addition_different_currency_raises(self) -> None:
        a = Money.from_won(1000)
        b = Money.from_cents(500, "USD")
        with pytest.raises(ValueError, match="different currencies"):
            _ = a + b

    def test_subtraction(self) -> None:
        a = Money.from_won(1000)
        b = Money.from_won(300)
        assert (a - b) == Money.from_won(700)

    def test_comparison(self) -> None:
        a = Money.from_won(100)
        b = Money.from_won(200)
        assert a < b
        assert a <= b
        assert b > a
        assert b >= a

    def test_is_zero(self) -> None:
        assert Money.from_won(0).is_zero() is True
        assert Money.from_won(1).is_zero() is False

    def test_is_negative(self) -> None:
        assert Money.from_won(-1).is_negative() is True
        assert Money.from_won(0).is_negative() is False

    def test_float_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            Money(amount_cents=10.5, currency="USD")  # type: ignore[arg-type]

    def test_bool_amount_rejected(self) -> None:
        # bool은 int 서브타입이지만 의미가 다르므로 거부되어야 한다
        with pytest.raises(ValueError, match="must be an integer"):
            Money(amount_cents=True, currency="USD")  # type: ignore[arg-type]

    def test_invalid_currency_too_long(self) -> None:
        with pytest.raises(ValueError, match="3-letter ISO"):
            Money(amount_cents=100, currency="WONS")

    def test_invalid_currency_too_short(self) -> None:
        with pytest.raises(ValueError, match="3-letter ISO"):
            Money(amount_cents=100, currency="US")

    def test_frozen(self) -> None:
        m = Money.from_won(100)
        with pytest.raises((AttributeError, Exception)):
            m.amount_cents = 200  # type: ignore[misc]


class TestAccountId:
    def test_valid_construction(self) -> None:
        aid = AccountId(value="user-uuid-123")
        assert aid.value == "user-uuid-123"
        assert str(aid) == "user-uuid-123"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            AccountId(value="")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            AccountId(value="   ")

    def test_non_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            AccountId(value=123)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        aid = AccountId(value="abc")
        with pytest.raises((AttributeError, Exception)):
            aid.value = "xyz"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = AccountId(value="same")
        b = AccountId(value="same")
        assert a == b
        assert hash(a) == hash(b)


class TestUserId:
    def test_valid(self) -> None:
        uid = UserId(value="uid-1")
        assert str(uid) == "uid-1"

    def test_distinct_from_account_id(self) -> None:
        # 동일 문자열이라도 타입이 다르면 같은 값이 아니다
        uid = UserId(value="same")
        aid = AccountId(value="same")
        assert uid != aid  # 타입 다름


class TestWorkspaceId:
    def test_valid(self) -> None:
        wid = WorkspaceId(value="ws-1")
        assert str(wid) == "ws-1"

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            WorkspaceId(value="")


class TestCreditAmount:
    def test_positive_credit(self) -> None:
        c = CreditAmount(value=5)
        assert c.is_credit()
        assert not c.is_debit()

    def test_negative_debit(self) -> None:
        c = CreditAmount(value=-3)
        assert c.is_debit()
        assert not c.is_credit()

    def test_neg_operator(self) -> None:
        assert -CreditAmount(value=5) == CreditAmount(value=-5)

    def test_non_int_rejected(self) -> None:
        with pytest.raises(ValueError):
            CreditAmount(value="five")  # type: ignore[arg-type]
