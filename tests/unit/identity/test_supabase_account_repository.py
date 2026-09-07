"""SupabaseAccountRepository 단위 테스트.

실제 Supabase 호출은 mock으로 격리한다. 검증 포인트:
- Supabase 비활성 시 동작 (find_by_id → None, consume_quota_atomic → _UNLIMITED_DEV_QUOTA)
- RPC 정상/한도 초과/예외 케이스
- find_by_id가 ie_usage + ie_api_keys + is_admin을 조합하고 크레딧은 0으로 유지
- save가 ie_usage만 upsert하며 미구현 크레딧 원장을 가장하지 않음
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.identity.domain.exceptions import (
    QuotaBackendUnavailable,
    QuotaExceeded,
)
from src.contexts.identity.domain.user_account import (
    CreditBalance,
    UsageQuota,
    UserAccount,
)
from src.contexts.identity.application.ports import (
    QuotaReservation,
    QuotaReservationConflict,
)
from src.contexts.identity.infrastructure.supabase_account_repository import (
    _UNLIMITED_DEV_QUOTA,
    SupabaseAccountRepository,
)
from src.shared.domain.value_objects import AccountId


# ---------------------------------------------------------------------------
# Supabase 비활성 (개발 모드) 시나리오
# ---------------------------------------------------------------------------


class TestSupabaseDisabled:
    """`is_supabase_enabled() == False`인 환경에서의 동작."""

    @patch(
        "services.data.supabase_service.is_supabase_enabled",
        return_value=False,
    )
    def test_find_by_id_returns_none(self, _enabled: MagicMock) -> None:
        repo = SupabaseAccountRepository()
        result = repo.find_by_id(AccountId(value="any-id"))
        assert result is None

    @patch(
        "services.data.supabase_service.is_supabase_enabled",
        return_value=False,
    )
    def test_save_is_noop(self, _enabled: MagicMock) -> None:
        repo = SupabaseAccountRepository()
        account = UserAccount(
            account_id="abc",
            email="t@x.com",
            quota=UsageQuota(),
            credits=CreditBalance(),
        )
        # 예외 없이 통과해야 함
        repo.save(account)

    @patch(
        "services.data.supabase_service.is_supabase_enabled",
        return_value=False,
    )
    def test_consume_quota_returns_unlimited(
        self, _enabled: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo = SupabaseAccountRepository()
        with caplog.at_level(
            logging.DEBUG,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ):
            result = repo.consume_quota_atomic(AccountId(value="abc"))
        assert result == _UNLIMITED_DEV_QUOTA
        # 추적용 디버그 로그가 남았는지 확인
        assert any(
            "_UNLIMITED_DEV_QUOTA fallback" in r.message for r in caplog.records
        )


class TestScopedClientSelection:
    def test_account_reads_and_writes_use_user_scoped_client(self) -> None:
        repo = SupabaseAccountRepository()
        user_client = MagicMock()

        with (
            patch(
                'src.shared.infrastructure.supabase_client.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.shared.infrastructure.supabase_client.get_user_supabase',
                return_value=user_client,
            ) as get_user_client,
        ):
            assert repo._get_client() is user_client

        get_user_client.assert_called_once_with()

    def test_admin_auth_lookup_uses_explicit_service_role(self) -> None:
        repo = SupabaseAccountRepository()
        service_client = MagicMock()

        with patch(
            'src.shared.infrastructure.supabase_client.get_service_supabase',
            return_value=service_client,
        ) as get_service_client:
            assert repo._get_admin_client() is service_client

        get_service_client.assert_called_once_with()


# ---------------------------------------------------------------------------
# consume_quota_atomic — RPC 응답 처리
# ---------------------------------------------------------------------------


class TestConsumeQuotaAtomic:
    def _make_repo_with_mock_client(
        self,
        rpc_data: object | None,
        raise_exc: Exception | None = None,
        read_data: object | None = None,
        read_raises: Exception | None = None,
    ) -> tuple[SupabaseAccountRepository, MagicMock]:
        """Supabase 활성 + RPC/읽기 폴백 응답을 제어할 수 있는 fixture."""
        mock_client = MagicMock()
        rpc_response = MagicMock()
        rpc_response.data = rpc_data
        if raise_exc is not None:
            mock_client.rpc.side_effect = raise_exc
        else:
            mock_client.rpc.return_value.execute.return_value = rpc_response

        # _read_remaining_quota의 읽기 체인:
        # table(...).select(...).eq(...).limit(...).execute()
        read_exec = (
            mock_client.table.return_value
            .select.return_value
            .eq.return_value
            .limit.return_value
            .execute
        )
        if read_raises is not None:
            read_exec.side_effect = read_raises
        else:
            read_response = MagicMock()
            read_response.data = read_data
            read_exec.return_value = read_response

        repo = SupabaseAccountRepository()
        # 요청별 JWT/service-role RPC 클라이언트 경계를 직접 패치한다.
        repo._get_usage_rpc_client = MagicMock(  # type: ignore[method-assign]
            return_value=mock_client
        )
        return repo, mock_client

    def test_success_returns_new_count(self) -> None:
        repo, client = self._make_repo_with_mock_client(
            {"success": True, "new_count": 5}
        )
        result = repo.consume_quota_atomic(AccountId(value="user-1"))
        assert result == 5
        client.rpc.assert_called_once_with(
            "decrement_usage_safe", {"p_user_id": "user-1", "p_amount": 1}
        )

    def test_multi_amount_is_sent_in_one_rpc(self) -> None:
        repo, client = self._make_repo_with_mock_client(
            {"success": True, "new_count": 2}
        )
        result = repo.consume_quota_atomic(AccountId(value="user-1"), 3)
        assert result == 2
        client.rpc.assert_called_once_with(
            "decrement_usage_safe", {"p_user_id": "user-1", "p_amount": 3}
        )

    @pytest.mark.parametrize("amount", [0, -1, True])
    def test_invalid_amount_is_rejected_before_rpc(self, amount: int) -> None:
        repo, client = self._make_repo_with_mock_client(
            {"success": True, "new_count": 5}
        )
        with pytest.raises(ValueError, match="positive integer"):
            repo.consume_quota_atomic(AccountId(value="user-1"), amount)
        client.rpc.assert_not_called()

    def test_no_usage_left_raises_quota_exceeded(self) -> None:
        repo, _ = self._make_repo_with_mock_client(
            {"success": False, "reason": "no_usage_left"}
        )
        with pytest.raises(QuotaExceeded):
            repo.consume_quota_atomic(AccountId(value="user-2"))

    def test_unexpected_payload_is_backend_unavailable(self) -> None:
        # 계약 밖 응답은 실제 한도 초과로 가장하지 않고 차감 장애로 처리한다.
        repo, _ = self._make_repo_with_mock_client({"weird": True})
        with pytest.raises(QuotaBackendUnavailable):
            repo.consume_quota_atomic(AccountId(value="user-3"))

    def test_rpc_exception_fails_closed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo, client = self._make_repo_with_mock_client(
            None,
            raise_exc=RuntimeError("network down"),
            read_data=[{"usage_count": 7}],
        )
        with caplog.at_level(
            logging.ERROR,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ), pytest.raises(QuotaBackendUnavailable):
            repo.consume_quota_atomic(AccountId(value="user-4"))
        assert any("안전하게 차감할 수 없음" in r.message for r in caplog.records)
        client.table.assert_not_called()

    def test_rpc_exception_never_falls_back_to_unlimited(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo, _ = self._make_repo_with_mock_client(
            None,
            raise_exc=RuntimeError("network down"),
            read_raises=RuntimeError("read down"),
        )
        with caplog.at_level(
            logging.ERROR,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ), pytest.raises(QuotaBackendUnavailable):
            repo.consume_quota_atomic(AccountId(value="user-5"))
        assert any("안전하게 차감할 수 없음" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# reserve/refund — 멱등 RPC 응답 처리
# ---------------------------------------------------------------------------


class TestQuotaReservationRpc:
    @staticmethod
    def _response(data: dict) -> MagicMock:
        response = MagicMock()
        response.data = data
        return response

    @staticmethod
    def _repo(client: MagicMock) -> SupabaseAccountRepository:
        repo = SupabaseAccountRepository()
        repo._get_usage_rpc_client = MagicMock(  # type: ignore[method-assign]
            return_value=client
        )
        return repo

    def test_usage_rpc_client_uses_service_role_after_validated_request(self) -> None:
        from flask import Flask, g

        app = Flask(__name__)
        service_client = MagicMock()
        repo = SupabaseAccountRepository()

        with (
            app.test_request_context('/generate'),
            patch(
                'src.shared.infrastructure.supabase_client.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.shared.infrastructure.supabase_client.get_service_supabase',
                return_value=service_client,
            ) as get_service_client,
            patch(
                'src.shared.infrastructure.supabase_client.get_user_supabase',
            ) as get_user_client,
        ):
            g.user_id = 'user-1'
            g.access_token = 'validated-jwt'
            assert repo._get_usage_rpc_client(AccountId('user-1')) is service_client

        get_service_client.assert_called_once_with()
        get_user_client.assert_not_called()

    def test_usage_rpc_client_never_escalates_missing_request_jwt(self) -> None:
        from flask import Flask, g

        app = Flask(__name__)
        repo = SupabaseAccountRepository()

        with (
            app.test_request_context('/generate'),
            patch(
                'src.shared.infrastructure.supabase_client.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.shared.infrastructure.supabase_client.get_service_supabase'
            ) as service_client,
        ):
            g.user_id = 'user-1'
            g.access_token = None
            with pytest.raises(QuotaBackendUnavailable):
                repo._get_usage_rpc_client(AccountId('user-1'))

        service_client.assert_not_called()

    def test_usage_rpc_client_rejects_authenticated_account_mismatch(self) -> None:
        from flask import Flask, g

        app = Flask(__name__)
        repo = SupabaseAccountRepository()

        with (
            app.test_request_context('/generate'),
            patch(
                'src.shared.infrastructure.supabase_client.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.shared.infrastructure.supabase_client.get_service_supabase'
            ) as service_client,
        ):
            g.user_id = 'user-1'
            g.access_token = 'validated-jwt'
            with pytest.raises(QuotaBackendUnavailable, match='does not match'):
                repo._get_usage_rpc_client(AccountId('user-2'))

        service_client.assert_not_called()

    def test_usage_rpc_background_requires_explicit_service_role(self) -> None:
        repo = SupabaseAccountRepository()
        service_client = MagicMock()

        with (
            patch(
                'src.shared.infrastructure.supabase_client.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.shared.infrastructure.supabase_client.get_service_supabase',
                return_value=service_client,
            ) as get_service_client,
        ):
            assert repo._get_usage_rpc_client(AccountId('user-1')) is service_client

        get_service_client.assert_called_once_with()

    def test_commit_then_response_loss_retry_reuses_same_reservation(self) -> None:
        """첫 RPC가 커밋 후 응답 유실돼도 같은 인자로 재시도해 한 예약으로 수렴."""
        client = MagicMock()
        client.rpc.return_value.execute.side_effect = [
            ConnectionError("response lost after commit"),
            self._response({
                "success": True,
                "reservation_id": "reservation-1",
                "new_count": 4,
                "max_usage": 5,
                "owned": True,
                "replayed": True,
            }),
        ]
        repo = self._repo(client)

        result = repo.reserve_quota_atomic(
            AccountId("user-1"),
            "client:key",
            "a" * 64,
            "b" * 64,
        )

        assert result.remaining == 4
        assert result.owned is True
        assert result.replayed is True
        assert client.rpc.call_count == 2
        assert client.rpc.call_args_list[0] == client.rpc.call_args_list[1]

    def test_same_key_replay_is_not_owned_by_second_http_request(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.return_value = self._response({
            "success": False,
            "reason": "idempotency_replay",
            "reservation_id": "reservation-1",
            "new_count": 4,
            "max_usage": 5,
        })
        repo = self._repo(client)

        result = repo.reserve_quota_atomic(
            AccountId("user-1"),
            "client:key",
            "a" * 64,
            "new-owner-token".ljust(64, "0"),
        )

        assert result.remaining == 4
        assert result.owned is False
        assert result.replayed is True

    def test_same_key_with_different_payload_is_conflict(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.return_value = self._response({
            "success": False,
            "reason": "idempotency_conflict",
        })
        repo = self._repo(client)

        with pytest.raises(QuotaReservationConflict):
            repo.reserve_quota_atomic(
                AccountId("user-1"),
                "client:key",
                "a" * 64,
                "b" * 64,
            )
        assert client.rpc.call_count == 1

    def test_two_lost_reservation_responses_trigger_owned_compensation(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.side_effect = [
            ConnectionError("first reserve response lost"),
            ConnectionError("second reserve response lost"),
            self._response({"success": True, "new_count": 5}),
        ]
        repo = self._repo(client)

        with pytest.raises(QuotaBackendUnavailable):
            repo.reserve_quota_atomic(
                AccountId("user-1"),
                "client:key",
                "a" * 64,
                "b" * 64,
            )

        assert [call.args[0] for call in client.rpc.call_args_list] == [
            "reserve_usage_safe",
            "reserve_usage_safe",
            "refund_usage_reservation_safe",
        ]

    def test_refund_retries_idempotently_after_response_loss(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.side_effect = [
            ConnectionError("refund response lost"),
            self._response({
                "success": True,
                "new_count": 5,
                "refunded": False,
                "replayed": True,
            }),
        ]
        repo = self._repo(client)
        reservation = QuotaReservation(
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

        assert repo.refund_quota_reservation(AccountId("user-1"), reservation) == 5
        assert client.rpc.call_count == 2
        assert client.rpc.call_args_list[0] == client.rpc.call_args_list[1]

    def test_replayed_request_cannot_refund_another_owner_reservation(self) -> None:
        client = MagicMock()
        repo = self._repo(client)
        reservation = QuotaReservation(
            reservation_id="reservation-1",
            idempotency_key="client:key",
            request_fingerprint="a" * 64,
            owner_token_hash="b" * 64,
            amount=1,
            remaining=4,
            max_usage=5,
            owned=False,
            replayed=True,
        )

        assert repo.refund_quota_reservation(AccountId("user-1"), reservation) == 4
        client.rpc.assert_not_called()

    def test_known_reservation_not_found_remains_fail_closed(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.return_value = self._response({
            "success": False,
            "reason": "reservation_not_found",
        })
        repo = self._repo(client)
        reservation = QuotaReservation(
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

        with pytest.raises(QuotaBackendUnavailable):
            repo.refund_quota_reservation(AccountId("user-1"), reservation)

    def test_reservation_unexpected_payload_remains_backend_unavailable(self) -> None:
        client = MagicMock()
        client.rpc.return_value.execute.return_value = self._response({"weird": True})
        repo = self._repo(client)

        with pytest.raises(QuotaBackendUnavailable):
            repo.reserve_quota_atomic(
                AccountId("user-1"),
                "client:key",
                "a" * 64,
                "b" * 64,
            )
        # 정상 HTTP 응답의 계약 위반은 예약으로 추측해 재시도하지
        # 않고, 모호한 차감만 같은 소유 토큰으로 보상 환불한다.
        assert [call.args[0] for call in client.rpc.call_args_list] == [
            "reserve_usage_safe",
            "refund_usage_reservation_safe",
        ]


def test_usage_reservation_migration_has_durable_concurrency_guards() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase"
        / "migrations"
        / "008_usage_reservation_idempotency.sql"
    ).read_text(encoding="utf-8")

    assert "UNIQUE (user_id, idempotency_key)" in migration
    assert "pg_advisory_xact_lock" in migration
    assert "FOR UPDATE" in migration
    assert "owner_token_hash" in migration
    assert "state = 'refunded'" in migration
    assert "SECURITY DEFINER" in migration
    assert "auth.jwt() ->> 'role'" in migration
    assert "IS DISTINCT FROM p_owner_token_hash" in migration
    assert "p_owner_token_hash IS NULL" in migration
    assert "ON CONFLICT (user_id) DO UPDATE" in migration
    assert "'reason', 'idempotency_replay'" in migration
    assert "SET search_path = ''" in migration


# ---------------------------------------------------------------------------
# find_by_id — 합성 시나리오
# ---------------------------------------------------------------------------


class TestFindById:
    def _build_query_response(self, rows: list[dict]) -> MagicMock:
        """`client.table(...).select(...).eq(...).limit(...).execute()` 체이닝
        에 대한 mock 응답 생성."""
        response = MagicMock()
        response.data = rows
        chain = MagicMock()
        chain.execute.return_value = response
        return chain

    def _make_repo(
        self,
        *,
        usage_rows: list[dict] | None = None,
        api_key_rows: list[dict] | None = None,
        admin_email: str = "user@example.com",
        is_admin_result: bool = False,
    ) -> SupabaseAccountRepository:
        mock_client = MagicMock()

        # API key table 조회 체인을 만든다. 사용량은 직접 테이블 쓰기/초기화가
        # 아닌 get_usage_safe RPC로 조회한다.
        def table_side_effect(name: str) -> MagicMock:
            response_rows = {
                "ie_api_keys": api_key_rows or [],
            }.get(name, [])
            response = MagicMock()
            response.data = response_rows
            tbl = MagicMock()
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                response
            )
            return tbl

        mock_client.table.side_effect = table_side_effect
        usage_response = MagicMock()
        usage_response.data = (
            (usage_rows or [])[0]
            if usage_rows
            else {"usage_count": 20, "max_usage": 20, "can_use": True}
        )
        usage_rpc = MagicMock()
        usage_rpc.execute.return_value = usage_response
        mock_client.rpc.return_value = usage_rpc

        # admin 클라이언트는 별도 mock
        mock_admin = MagicMock()
        user_mock = MagicMock()
        user_mock.user.email = admin_email
        mock_admin.auth.admin.get_user_by_id.return_value = user_mock

        repo = SupabaseAccountRepository()
        repo._get_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]
        repo._get_admin_client = MagicMock(return_value=mock_admin)  # type: ignore[method-assign]

        # is_admin은 lazy import이므로 patch
        patcher = patch(
            "services.data.supabase_service.is_admin",
            return_value=is_admin_result,
        )
        patcher.start()
        # repo가 destroy될 때 자동 정리 — 테스트마다 stopAll로 보장
        repo._cleanup_patches = [patcher]  # type: ignore[attr-defined]
        return repo

    def teardown_method(self) -> None:
        """각 테스트 후 patch 정리."""
        patch.stopall()

    def test_basic_assembly(self) -> None:
        repo = self._make_repo(
            usage_rows=[{"usage_count": 17, "max_usage": 20}],
            api_key_rows=[
                {
                    "gemini_key": "encrypted_value_xyz1234",
                    "deepseek_key": None,
                    "created_at": "2026-05-01T00:00:00+00:00",
                }
            ],
            admin_email="user@example.com",
            is_admin_result=False,
        )
        ua = repo.find_by_id(AccountId(value="user-1"))
        assert ua is not None
        assert ua.email == "user@example.com"
        assert ua.quota.daily_limit == 20
        assert ua.quota.used_today == 3  # 20 - 17
        assert ua.credits.balance == 0
        assert len(ua.api_keys) == 1
        assert ua.api_keys[0].provider == "gemini"
        # 도메인 보호 — 평문 노출 금지, 마지막 4글자 마스킹만
        assert ua.api_keys[0].masked_key == "****1234"
        # admin이 아니므로 owner 역할 부여
        assert ua.is_admin() is False
        assert any(r.name == "owner" for r in ua.roles)

    def test_admin_role_attached(self) -> None:
        repo = self._make_repo(
            usage_rows=[{"usage_count": 20, "max_usage": 20}],
            is_admin_result=True,
        )
        ua = repo.find_by_id(AccountId(value="admin-1"))
        assert ua is not None
        assert ua.is_admin() is True

    def test_email_missing_returns_none(self) -> None:
        repo = self._make_repo(admin_email="")
        ua = repo.find_by_id(AccountId(value="no-email"))
        assert ua is None

    def test_default_quota_when_no_row(self) -> None:
        repo = self._make_repo(
            usage_rows=[],
            api_key_rows=[],
        )
        ua = repo.find_by_id(AccountId(value="new-user"))
        assert ua is not None
        # 기본값 사용 (DEFAULT_DAILY_LIMIT=20)
        assert ua.quota.daily_limit == 20
        assert ua.quota.used_today == 0
        assert ua.credits.balance == 0
        assert len(ua.api_keys) == 0


# ---------------------------------------------------------------------------
# save — upsert 호출 검증
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# find_by_id — admin (service_role) 미설정 시 동작
# ---------------------------------------------------------------------------


class TestFindByIdAdminUnavailable:
    """Supabase 관리자 키 미설정 시 warning 로그 + None 반환."""

    def test_warning_logged_when_admin_none(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo = SupabaseAccountRepository()
        # client는 활성, admin은 None
        repo._get_client = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]
        repo._get_admin_client = MagicMock(return_value=None)  # type: ignore[method-assign]

        with caplog.at_level(
            logging.WARNING,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ):
            result = repo.find_by_id(AccountId(value="some-user-id"))

        assert result is None
        # 운영자가 인지할 수 있는 warning 로그
        assert any(
            "secret/service_role 키 미설정" in r.message
            for r in caplog.records
        ), f"warning 로그가 남지 않음: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# find_by_email — 페이지네이션
# ---------------------------------------------------------------------------


class TestFindByEmailPagination:
    """list_users(page, per_page) 페이지 순회 + 한도 검증."""

    def _make_user(self, user_id: str, email: str) -> MagicMock:
        u = MagicMock()
        u.id = user_id
        u.email = email
        return u

    def teardown_method(self) -> None:
        patch.stopall()

    def test_admin_none_returns_none_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo = SupabaseAccountRepository()
        repo._get_admin_client = MagicMock(return_value=None)  # type: ignore[method-assign]

        with caplog.at_level(
            logging.WARNING,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ):
            result = repo.find_by_email("anyone@example.com")

        assert result is None
        assert any(
            "secret/service_role 키 미설정" in r.message
            for r in caplog.records
        )

    def test_finds_user_in_second_page(self) -> None:
        """1000+1 사용자: 첫 페이지엔 없고 두 번째 페이지에서 발견."""
        repo = SupabaseAccountRepository()
        mock_admin = MagicMock()

        # 페이지 1: 1000명 (대상 없음), 페이지 2: 1명 (대상 있음)
        per_page = repo._FIND_BY_EMAIL_PER_PAGE
        page1_users = [
            self._make_user(f"u{i}", f"u{i}@example.com") for i in range(per_page)
        ]
        target_user = self._make_user("target-id", "target@example.com")
        page2_users = [target_user]

        def list_users_side_effect(page: int = 1, per_page: int = 1000) -> MagicMock:
            resp = MagicMock()
            if page == 1:
                resp.users = page1_users
            elif page == 2:
                resp.users = page2_users
            else:
                resp.users = []
            return resp

        mock_admin.auth.admin.list_users.side_effect = list_users_side_effect
        repo._get_admin_client = MagicMock(return_value=mock_admin)  # type: ignore[method-assign]
        # find_by_id를 가벼운 mock으로 (Aggregate 조립은 별도 테스트에서 검증)
        sentinel_account = MagicMock()
        repo.find_by_id = MagicMock(return_value=sentinel_account)  # type: ignore[method-assign]

        result = repo.find_by_email("target@example.com")

        assert result is sentinel_account
        # 두 번 호출되어야 함 (page=1, page=2)
        assert mock_admin.auth.admin.list_users.call_count == 2
        # find_by_id가 target-id로 호출되었는지
        repo.find_by_id.assert_called_once()
        called_account_id = repo.find_by_id.call_args[0][0]
        assert str(called_account_id) == "target-id"

    def test_returns_none_when_last_page_partial(self) -> None:
        """마지막 페이지(per_page 미만)에서 미발견 → 더 이상 순회 안 함."""
        repo = SupabaseAccountRepository()
        mock_admin = MagicMock()

        # 50명 (per_page=1000 미만) — 1페이지로 끝남
        users = [self._make_user(f"u{i}", f"u{i}@x.com") for i in range(50)]
        resp = MagicMock()
        resp.users = users
        mock_admin.auth.admin.list_users.return_value = resp
        repo._get_admin_client = MagicMock(return_value=mock_admin)  # type: ignore[method-assign]

        result = repo.find_by_email("notfound@x.com")

        assert result is None
        # 첫 페이지만 호출
        assert mock_admin.auth.admin.list_users.call_count == 1

    def test_page_limit_exceeded_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """모든 페이지가 가득 차고도 미발견 → MAX_PAGES warning."""
        repo = SupabaseAccountRepository()
        mock_admin = MagicMock()
        per_page = repo._FIND_BY_EMAIL_PER_PAGE
        # 항상 1000명짜리 페이지 반환 (대상 이메일 없음)
        users = [self._make_user(f"u{i}", f"u{i}@x.com") for i in range(per_page)]

        def list_users_side_effect(page: int = 1, per_page: int = 1000) -> MagicMock:
            resp = MagicMock()
            resp.users = users
            return resp

        mock_admin.auth.admin.list_users.side_effect = list_users_side_effect
        repo._get_admin_client = MagicMock(return_value=mock_admin)  # type: ignore[method-assign]

        with caplog.at_level(
            logging.WARNING,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ):
            result = repo.find_by_email("nope@x.com")

        assert result is None
        assert mock_admin.auth.admin.list_users.call_count == repo._FIND_BY_EMAIL_MAX_PAGES
        assert any(
            "페이지 한도" in r.message for r in caplog.records
        ), f"한도 초과 warning 누락: {[r.message for r in caplog.records]}"

    def test_legacy_list_users_without_kwargs(self) -> None:
        """구버전 supabase-py: list_users()가 page/per_page kwarg 미지원 → TypeError → 1회만 호출."""
        repo = SupabaseAccountRepository()
        mock_admin = MagicMock()

        target_user = self._make_user("legacy-id", "legacy@example.com")
        users = [target_user]

        call_count = {"with_kwargs": 0, "without_kwargs": 0}

        def list_users_side_effect(*args, **kwargs):
            if kwargs:
                call_count["with_kwargs"] += 1
                raise TypeError("list_users() got unexpected keyword argument")
            call_count["without_kwargs"] += 1
            resp = MagicMock()
            resp.users = users
            return resp

        mock_admin.auth.admin.list_users.side_effect = list_users_side_effect
        repo._get_admin_client = MagicMock(return_value=mock_admin)  # type: ignore[method-assign]
        sentinel = MagicMock()
        repo.find_by_id = MagicMock(return_value=sentinel)  # type: ignore[method-assign]

        result = repo.find_by_email("legacy@example.com")

        assert result is sentinel
        # kwargs 시도 1회 + 호환 모드 1회
        assert call_count["with_kwargs"] == 1
        assert call_count["without_kwargs"] == 1


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


class TestSave:
    def test_save_uses_service_role_quota_rpc(self) -> None:
        mock_client = MagicMock()
        rpc_query = MagicMock()
        rpc_query.execute.return_value.data = {
            "success": True,
            "usage_count": 15,
            "max_usage": 20,
        }
        mock_client.rpc.return_value = rpc_query

        repo = SupabaseAccountRepository()
        repo._get_admin_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]

        account = UserAccount(
            account_id="user-1",
            email="user@example.com",
            quota=UsageQuota(daily_limit=20, used_today=5),
            credits=CreditBalance(balance=42),
        )
        repo.save(account)

        mock_client.rpc.assert_called_once_with(
            "set_usage_quota_admin",
            {
                "p_user_id": "user-1",
                "p_usage_count": 15,
                "p_max_usage": 20,
            },
        )
        mock_client.table.assert_not_called()
