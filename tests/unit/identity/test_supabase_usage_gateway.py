"""SupabaseUsageGateway 단위 테스트.

IAccountRepository는 mock으로 대체. amount=1 / amount=N 분기와
refund의 no-op 동작을 검증한다.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from src.contexts.identity.application.ports import IAccountRepository
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.contexts.identity.infrastructure.supabase_usage_gateway import (
    SupabaseUsageGateway,
)
from src.shared.domain.value_objects import AccountId


@pytest.fixture
def account_id() -> AccountId:
    return AccountId("user-uuid-789")


@pytest.fixture
def accounts_mock():
    mock = MagicMock(spec=IAccountRepository)
    mock.refund_quota_atomic = MagicMock(return_value=5)
    return mock


@pytest.fixture
def gateway(accounts_mock):
    return SupabaseUsageGateway(accounts=accounts_mock)


class TestCheckAndConsume:
    def test_single_call_when_amount_is_one(self, gateway, accounts_mock, account_id):
        """amount=1: consume_quota_atomic 1회 호출."""
        accounts_mock.consume_quota_atomic.return_value = 18
        result = gateway.check_and_consume(account_id, 1)
        assert result == 18
        accounts_mock.consume_quota_atomic.assert_called_once_with(account_id, 1)

    def test_repeated_calls_for_amount_greater_than_one(
        self, gateway, accounts_mock, account_id
    ):
        """amount=3: consume_quota_atomic 3회 반복 호출 + 마지막 remaining 반환."""
        accounts_mock.consume_quota_atomic.side_effect = [19, 18, 17]
        result = gateway.check_and_consume(account_id, 3)
        assert result == 17
        assert accounts_mock.consume_quota_atomic.call_count == 3
        for call in accounts_mock.consume_quota_atomic.call_args_list:
            assert call.args == (account_id, 1)

    def test_propagates_quota_exceeded(self, gateway, accounts_mock, account_id):
        """저장소에서 QuotaExceeded 발생 시 그대로 전파."""
        accounts_mock.consume_quota_atomic.side_effect = QuotaExceeded("no more")
        with pytest.raises(QuotaExceeded):
            gateway.check_and_consume(account_id, 1)


class TestRefund:
    def test_refund_calls_repository(self, gateway, accounts_mock, account_id):
        accounts_mock.refund_quota_atomic.return_value = 5
        gateway.refund(account_id, 1)
        accounts_mock.refund_quota_atomic.assert_called_once_with(account_id)

    def test_refund_with_custom_amount(self, gateway, accounts_mock, account_id):
        accounts_mock.refund_quota_atomic.return_value = 5
        gateway.refund(account_id, 5)
        assert accounts_mock.refund_quota_atomic.call_count == 5
