"""Identity & Access — UserAccount Aggregate / 자식 엔티티 단위 테스트.

- UsageQuota: consume / 한도 초과 / reset / create_default
- CreditBalance: debit / 부족 / credit / can_afford
- UserAccount: api_keys/roles 캡슐화 + 메서드를 통한 변경 + admin 판정
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.contexts.identity.domain.constants import DEFAULT_DAILY_LIMIT
from src.contexts.identity.domain.exceptions import (
    InsufficientCredits,
    InvalidApiKey,
    QuotaExceeded,
)
from src.contexts.identity.domain.user_account import (
    ApiKey,
    CreditBalance,
    RbacRole,
    UsageQuota,
    UserAccount,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_account(
    *,
    used_today: int = 0,
    daily_limit: int = 20,
    balance: int = 0,
    roles: list[RbacRole] | None = None,
    api_keys: list[ApiKey] | None = None,
) -> UserAccount:
    return UserAccount(
        account_id="user-uuid-1",
        email="user@example.com",
        quota=UsageQuota(daily_limit=daily_limit, used_today=used_today),
        credits=CreditBalance(balance=balance),
        roles=roles or [],
        api_keys=api_keys or [],
    )


def _make_key(provider: str = "gemini", label: str = "default") -> ApiKey:
    return ApiKey(
        provider=provider,
        masked_key="****abcd",
        label=label,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# UsageQuota
# ---------------------------------------------------------------------------


class TestUsageQuota:
    def test_create_default_uses_constant(self) -> None:
        q = UsageQuota.create_default()
        assert q.daily_limit == DEFAULT_DAILY_LIMIT
        assert q.used_today == 0

    def test_remaining(self) -> None:
        q = UsageQuota(daily_limit=10, used_today=3)
        assert q.remaining == 7

    def test_has_remaining(self) -> None:
        assert UsageQuota(daily_limit=10, used_today=9).has_remaining() is True
        assert UsageQuota(daily_limit=10, used_today=10).has_remaining() is False

    def test_consume_decreases_remaining(self) -> None:
        q = UsageQuota(daily_limit=10, used_today=0)
        q.consume(1)
        assert q.used_today == 1
        assert q.remaining == 9

    def test_consume_multiple(self) -> None:
        q = UsageQuota(daily_limit=10, used_today=0)
        q.consume(3)
        assert q.used_today == 3

    def test_consume_over_limit_raises(self) -> None:
        q = UsageQuota(daily_limit=2, used_today=1)
        with pytest.raises(QuotaExceeded):
            q.consume(2)
        # 한도 초과 시 상태 변경 없음
        assert q.used_today == 1

    def test_consume_zero_invalid(self) -> None:
        q = UsageQuota()
        with pytest.raises(ValueError):
            q.consume(0)

    def test_reset(self) -> None:
        q = UsageQuota(daily_limit=10, used_today=5)
        q.reset()
        assert q.used_today == 0

    def test_negative_limit_rejected(self) -> None:
        with pytest.raises(ValueError):
            UsageQuota(daily_limit=-1)

    def test_negative_used_rejected(self) -> None:
        with pytest.raises(ValueError):
            UsageQuota(used_today=-1)


# ---------------------------------------------------------------------------
# CreditBalance
# ---------------------------------------------------------------------------


class TestCreditBalance:
    def test_initial_zero(self) -> None:
        assert CreditBalance().balance == 0

    def test_debit_reduces_balance(self) -> None:
        cb = CreditBalance(balance=10)
        cb.debit(3)
        assert cb.balance == 7

    def test_debit_insufficient_raises(self) -> None:
        cb = CreditBalance(balance=2)
        with pytest.raises(InsufficientCredits):
            cb.debit(5)
        assert cb.balance == 2  # 상태 변경 없음

    def test_credit_increases(self) -> None:
        cb = CreditBalance(balance=5)
        cb.credit(3)
        assert cb.balance == 8

    def test_can_afford(self) -> None:
        cb = CreditBalance(balance=5)
        assert cb.can_afford(5) is True
        assert cb.can_afford(6) is False

    def test_negative_balance_rejected(self) -> None:
        with pytest.raises(ValueError):
            CreditBalance(balance=-1)

    def test_debit_zero_invalid(self) -> None:
        with pytest.raises(ValueError):
            CreditBalance(balance=10).debit(0)


# ---------------------------------------------------------------------------
# RbacRole
# ---------------------------------------------------------------------------


class TestRbacRole:
    def test_valid_roles(self) -> None:
        for name in ("admin", "owner", "editor", "viewer"):
            r = RbacRole(name=name)
            assert r.name == name

    def test_invalid_role(self) -> None:
        with pytest.raises(ValueError):
            RbacRole(name="root")

    def test_is_admin(self) -> None:
        assert RbacRole(name="admin").is_admin()
        assert not RbacRole(name="owner").is_admin()

    def test_can_edit(self) -> None:
        assert RbacRole(name="admin").can_edit()
        assert RbacRole(name="owner").can_edit()
        assert RbacRole(name="editor").can_edit()
        assert not RbacRole(name="viewer").can_edit()


# ---------------------------------------------------------------------------
# UserAccount — 캡슐화
# ---------------------------------------------------------------------------


class TestUserAccountEncapsulation:
    def test_api_keys_returns_tuple(self) -> None:
        ua = _make_account()
        assert isinstance(ua.api_keys, tuple)

    def test_roles_returns_tuple(self) -> None:
        ua = _make_account()
        assert isinstance(ua.roles, tuple)

    def test_api_keys_external_mutation_blocked(self) -> None:
        ua = _make_account()
        # tuple은 append를 지원하지 않으므로 AttributeError가 정상
        with pytest.raises((AttributeError, TypeError)):
            ua.api_keys.append("evil")  # type: ignore[attr-defined]
        # 캡슐화 확인 — 내부 list가 외부로 새지 않음
        assert len(ua.api_keys) == 0

    def test_roles_external_mutation_blocked(self) -> None:
        ua = _make_account()
        with pytest.raises((AttributeError, TypeError)):
            ua.roles.append("evil")  # type: ignore[attr-defined]
        assert len(ua.roles) == 0

    def test_constructor_copies_input_list(self) -> None:
        """생성자가 받은 list를 내부에 복사 — 외부 list 변경이 영향 X."""
        external_keys: list[ApiKey] = [_make_key("gemini")]
        ua = _make_account(api_keys=external_keys)
        # 외부 list를 변경해도 ua 내부 상태 불변
        external_keys.clear()
        assert len(ua.api_keys) == 1


class TestUserAccountApiKeys:
    def test_add_api_key(self) -> None:
        ua = _make_account()
        ua.add_api_key(_make_key("gemini"))
        assert len(ua.api_keys) == 1
        assert ua.api_keys[0].provider == "gemini"

    def test_add_duplicate_raises(self) -> None:
        ua = _make_account()
        ua.add_api_key(_make_key("gemini", label="default"))
        with pytest.raises(InvalidApiKey, match="duplicate"):
            ua.add_api_key(_make_key("gemini", label="default"))

    def test_add_same_provider_different_label_ok(self) -> None:
        ua = _make_account()
        ua.add_api_key(_make_key("gemini", label="primary"))
        ua.add_api_key(_make_key("gemini", label="backup"))
        assert len(ua.api_keys) == 2

    def test_remove_api_key(self) -> None:
        ua = _make_account()
        ua.add_api_key(_make_key("gemini", label="default"))
        ua.remove_api_key("gemini", "default")
        assert len(ua.api_keys) == 0

    def test_remove_missing_raises(self) -> None:
        ua = _make_account()
        with pytest.raises(InvalidApiKey, match="not found"):
            ua.remove_api_key("gemini", "default")

    def test_get_active_key(self) -> None:
        ua = _make_account()
        key = _make_key("gemini")
        ua.add_api_key(key)
        assert ua.get_active_key("gemini") == key
        assert ua.get_active_key("openai") is None

    def test_add_api_key_type_check(self) -> None:
        ua = _make_account()
        with pytest.raises(TypeError):
            ua.add_api_key("not-an-api-key")  # type: ignore[arg-type]


class TestUserAccountRoles:
    def test_is_admin_default_false(self) -> None:
        ua = _make_account()
        assert ua.is_admin() is False

    def test_is_admin_with_admin_role(self) -> None:
        ua = _make_account(roles=[RbacRole(name="admin")])
        assert ua.is_admin() is True

    def test_is_admin_with_owner_role(self) -> None:
        ua = _make_account(roles=[RbacRole(name="owner")])
        assert ua.is_admin() is False

    def test_add_role(self) -> None:
        ua = _make_account()
        ua.add_role(RbacRole(name="admin"))
        assert ua.is_admin()
        assert len(ua.roles) == 1

    def test_add_role_duplicate_ignored(self) -> None:
        ua = _make_account()
        ua.add_role(RbacRole(name="admin"))
        ua.add_role(RbacRole(name="admin"))
        assert len(ua.roles) == 1

    def test_add_role_type_check(self) -> None:
        ua = _make_account()
        with pytest.raises(TypeError):
            ua.add_role("admin")  # type: ignore[arg-type]


class TestUserAccountValidation:
    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValueError, match="email"):
            UserAccount(
                account_id="abc",
                email="not-an-email",
                quota=UsageQuota(),
                credits=CreditBalance(),
            )

    def test_string_account_id_converted(self) -> None:
        ua = _make_account()
        # 문자열로 넘겨도 AccountId VO로 변환되어 보관
        from src.shared.domain.value_objects import AccountId

        assert isinstance(ua.account_id, AccountId)

    def test_quota_type_check(self) -> None:
        with pytest.raises(TypeError, match="quota"):
            UserAccount(
                account_id="abc",
                email="x@y.com",
                quota="not-a-quota",  # type: ignore[arg-type]
                credits=CreditBalance(),
            )

    def test_credits_type_check(self) -> None:
        with pytest.raises(TypeError, match="credits"):
            UserAccount(
                account_id="abc",
                email="x@y.com",
                quota=UsageQuota(),
                credits=999,  # type: ignore[arg-type]
            )
