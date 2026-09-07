"""SupabaseUsageGateway 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.contexts.identity.application.ports import (
    IAccountRepository,
    QuotaReservation,
)
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.contexts.identity.infrastructure.supabase_usage_gateway import (
    SupabaseUsageGateway,
)
from src.shared.domain.value_objects import AccountId
from services.exceptions import ConfigurationError


@pytest.fixture
def account_id() -> AccountId:
    return AccountId("user-uuid-789")


@pytest.fixture
def accounts_mock():
    return MagicMock(spec=IAccountRepository)


@pytest.fixture
def gateway(accounts_mock):
    return SupabaseUsageGateway(accounts=accounts_mock)


class TestDailyUsageHistory:
    @staticmethod
    def _client(rows):
        client = MagicMock()
        client.rpc.return_value.execute.return_value.data = rows
        return client

    def test_account_history_uses_request_user_client(
        self,
        gateway,
        account_id,
    ):
        client = self._client([{'date': '2026-08-28', 'used_count': 2}])
        with (
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_user_supabase',
                return_value=client,
            ) as get_user_client,
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_service_supabase'
            ) as get_service_client,
        ):
            result = gateway.daily_usage_history(account_id=account_id)

        assert result == [{'date': '2026-08-28', 'used_count': 2}]
        client.rpc.assert_called_once_with(
            'get_daily_usage_history',
            {'p_user_id': str(account_id), 'p_days': 7},
        )
        get_user_client.assert_called_once_with()
        get_service_client.assert_not_called()

    def test_admin_history_requires_explicit_service_role(self, gateway):
        client = self._client([{'date': '2026-08-28', 'used_count': 7}])
        with (
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_user_supabase'
            ) as get_user_client,
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_service_supabase',
                return_value=client,
            ) as get_service_client,
        ):
            result = gateway.daily_usage_history(account_id=None)

        assert result == [{'date': '2026-08-28', 'used_count': 7}]
        client.rpc.assert_called_once_with(
            'get_daily_usage_history',
            {'p_user_id': None, 'p_days': 7},
        )
        get_service_client.assert_called_once_with()
        get_user_client.assert_not_called()

    def test_missing_user_jwt_never_falls_back_to_service_role(
        self,
        gateway,
        account_id,
    ):
        with (
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_user_supabase',
                side_effect=ConfigurationError('missing JWT'),
            ),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.get_service_supabase'
            ) as get_service_client,
            pytest.raises(ConfigurationError),
        ):
            gateway.daily_usage_history(account_id=account_id)

        get_service_client.assert_not_called()

    @pytest.mark.parametrize('days', [True, 0, 91, 1.5])
    def test_rejects_invalid_history_window(self, gateway, days):
        with pytest.raises(ValueError):
            gateway.daily_usage_history(days=days)

    def test_rejects_malformed_rpc_payload(self, gateway):
        client = self._client({'date': 'not-a-list'})
        with (
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'get_service_supabase',
                return_value=client,
            ),
            pytest.raises(RuntimeError, match='malformed'),
        ):
            gateway.daily_usage_history(account_id=None)


class TestCheckAndConsume:
    def test_single_call_when_amount_is_one(self, gateway, accounts_mock, account_id):
        """amount=1: consume_quota_atomic 1회 호출."""
        accounts_mock.consume_quota_atomic.return_value = 18
        result = gateway.check_and_consume(account_id, 1)
        assert result == 18
        accounts_mock.consume_quota_atomic.assert_called_once_with(account_id, 1)

    def test_single_atomic_call_for_amount_greater_than_one(
        self, gateway, accounts_mock, account_id
    ):
        """amount=3도 저장소의 원자 RPC 한 번으로 위임한다."""
        accounts_mock.consume_quota_atomic.return_value = 17
        result = gateway.check_and_consume(account_id, 3)
        assert result == 17
        accounts_mock.consume_quota_atomic.assert_called_once_with(account_id, 3)

    def test_propagates_quota_exceeded(self, gateway, accounts_mock, account_id):
        """저장소에서 QuotaExceeded 발생 시 그대로 전파."""
        accounts_mock.consume_quota_atomic.side_effect = QuotaExceeded("no more")
        with pytest.raises(QuotaExceeded):
            gateway.check_and_consume(account_id, 1)


class TestReservation:
    @pytest.fixture
    def reservation(self):
        return QuotaReservation(
            reservation_id="reservation-1",
            idempotency_key="client:key",
            request_fingerprint="a" * 64,
            owner_token_hash="b" * 64,
            amount=1,
            remaining=4,
            max_usage=5,
            owned=True,
            replayed=False,
        )

    def test_reserve_delegates_full_idempotency_contract(
        self, gateway, accounts_mock, account_id, reservation
    ):
        accounts_mock.reserve_quota_atomic.return_value = reservation

        result = gateway.reserve(
            account_id,
            "client:key",
            "a" * 64,
            "b" * 64,
            1,
        )

        assert result is reservation
        accounts_mock.reserve_quota_atomic.assert_called_once_with(
            account_id,
            "client:key",
            "a" * 64,
            "b" * 64,
            1,
        )

    def test_refund_delegates_exact_reservation(
        self, gateway, accounts_mock, account_id, reservation
    ):
        accounts_mock.refund_quota_reservation.return_value = 5

        assert gateway.refund(account_id, reservation) == 5
        accounts_mock.refund_quota_reservation.assert_called_once_with(
            account_id,
            reservation,
        )
