"""AccountService 단위 테스트.

포트(IAccountRepository, IApiKeyVault, IUsageGateway)를 mock으로 대체하여
순수 비즈니스 흐름만 검증한다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.contexts.identity.application.account_service import AccountService
from src.contexts.identity.application.ports import (
    IAccountRepository,
    IApiKeyVault,
    IUsageGateway,
)
from src.contexts.identity.domain.exceptions import (
    AccountNotFound,
    InvalidApiKey,
    QuotaExceeded,
)
from src.contexts.identity.domain.user_account import (
    ApiKey,
    CreditBalance,
    UsageQuota,
    UserAccount,
)
from src.shared.domain.value_objects import AccountId


@pytest.fixture
def account_id() -> AccountId:
    return AccountId("user-uuid-456")


@pytest.fixture
def sample_account(account_id) -> UserAccount:
    return UserAccount(
        account_id=account_id,
        email="user@example.com",
        quota=UsageQuota(daily_limit=20, used_today=0),
        credits=CreditBalance(balance=0),
    )


@pytest.fixture
def service():
    return AccountService(
        accounts=MagicMock(spec=IAccountRepository),
        api_keys=MagicMock(spec=IApiKeyVault),
        usage=MagicMock(spec=IUsageGateway),
    )


# ---------------------------------------------------------------------------
# get_account
# ---------------------------------------------------------------------------


class TestGetAccount:
    def test_returns_account_when_found(self, service, account_id, sample_account):
        service.accounts.find_by_id.return_value = sample_account
        assert service.get_account(account_id) is sample_account
        service.accounts.find_by_id.assert_called_once_with(account_id)

    def test_raises_account_not_found_when_missing(self, service, account_id):
        service.accounts.find_by_id.return_value = None
        with pytest.raises(AccountNotFound, match="user-uuid-456"):
            service.get_account(account_id)


# ---------------------------------------------------------------------------
# enforce_quota
# ---------------------------------------------------------------------------


class TestEnforceQuota:
    def test_returns_remaining_from_gateway(self, service, account_id):
        service.usage.check_and_consume.return_value = 18
        assert service.enforce_quota(account_id) == 18
        service.usage.check_and_consume.assert_called_once_with(account_id, 1)

    def test_propagates_quota_exceeded(self, service, account_id):
        service.usage.check_and_consume.side_effect = QuotaExceeded("limit reached")
        with pytest.raises(QuotaExceeded):
            service.enforce_quota(account_id)

    def test_custom_amount(self, service, account_id):
        service.usage.check_and_consume.return_value = 15
        service.enforce_quota(account_id, amount=3)
        service.usage.check_and_consume.assert_called_once_with(account_id, 3)


# ---------------------------------------------------------------------------
# add_api_key / revoke_api_key
# ---------------------------------------------------------------------------


class TestApiKeyManagement:
    def test_add_api_key_delegates_to_vault(self, service, account_id):
        expected = ApiKey(
            provider="gemini",
            masked_key="****1234",
            label="default",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        service.api_keys.store.return_value = expected
        result = service.add_api_key(account_id, "gemini", "sk-test-12341234", "default")
        assert result is expected
        service.api_keys.store.assert_called_once_with(
            account_id, "gemini", "sk-test-12341234", "default"
        )

    def test_get_api_key_plaintext_delegates(self, service, account_id):
        service.api_keys.reveal.return_value = "plaintext-key"
        assert service.get_api_key_plaintext(account_id, "gemini") == "plaintext-key"
        service.api_keys.reveal.assert_called_once_with(account_id, "gemini", "default")

    def test_revoke_delegates(self, service, account_id):
        service.revoke_api_key(account_id, "gemini", "default")
        service.api_keys.revoke.assert_called_once_with(account_id, "gemini", "default")


# ---------------------------------------------------------------------------
# resolve_provider_key
# ---------------------------------------------------------------------------


class TestResolveProviderKey:
    def test_byo_key_succeeds(self, service, account_id):
        """BYO 키가 있으면 평문 즉시 반환."""
        service.api_keys.reveal.return_value = "byo-key"
        assert service.resolve_provider_key(account_id, "gemini") == "byo-key"

    def test_falls_back_to_env_var(self, service, account_id, monkeypatch):
        """BYO 실패 → 환경변수 폴백."""
        service.api_keys.reveal.side_effect = InvalidApiKey("no key")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "shared-env-key")
        assert service.resolve_provider_key(account_id, "deepseek") == "shared-env-key"

    def test_raises_when_neither_byo_nor_env(self, service, account_id, monkeypatch):
        """BYO도 환경변수도 없음 → InvalidApiKey."""
        service.api_keys.reveal.side_effect = InvalidApiKey("no key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(InvalidApiKey, match="키 해결 실패"):
            service.resolve_provider_key(account_id, "anthropic")

    def test_unknown_provider_raises(self, service, account_id):
        """매핑되지 않은 프로바이더 — BYO도 없음 → InvalidApiKey."""
        service.api_keys.reveal.side_effect = InvalidApiKey("no key")
        with pytest.raises(InvalidApiKey, match="키 해결 실패"):
            service.resolve_provider_key(account_id, "unknown_provider")
