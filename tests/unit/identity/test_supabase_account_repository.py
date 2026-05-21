"""SupabaseAccountRepository 단위 테스트.

실제 Supabase 호출은 mock으로 격리한다. 검증 포인트:
- Supabase 비활성 시 동작 (find_by_id → None, consume_quota_atomic → _UNLIMITED_DEV_QUOTA)
- RPC 정상/한도 초과/예외 케이스
- find_by_id가 ie_usage + ie_credits + ie_api_keys + is_admin을 조합
- save가 ie_usage/ie_credits upsert 호출
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.contexts.identity.domain.user_account import (
    CreditBalance,
    UsageQuota,
    UserAccount,
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


# ---------------------------------------------------------------------------
# consume_quota_atomic — RPC 응답 처리
# ---------------------------------------------------------------------------


class TestConsumeQuotaAtomic:
    def _make_repo_with_mock_client(
        self, rpc_data: object | None, raise_exc: Exception | None = None
    ) -> tuple[SupabaseAccountRepository, MagicMock]:
        """Supabase 활성 + RPC 응답을 제어할 수 있는 fixture."""
        mock_client = MagicMock()
        rpc_response = MagicMock()
        rpc_response.data = rpc_data
        if raise_exc is not None:
            mock_client.rpc.side_effect = raise_exc
        else:
            mock_client.rpc.return_value.execute.return_value = rpc_response
        repo = SupabaseAccountRepository()
        # _get_client을 직접 패치 (lazy import 우회)
        repo._get_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]
        return repo, mock_client

    def test_success_returns_new_count(self) -> None:
        repo, client = self._make_repo_with_mock_client(
            {"success": True, "new_count": 5}
        )
        result = repo.consume_quota_atomic(AccountId(value="user-1"))
        assert result == 5
        client.rpc.assert_called_once_with(
            "decrement_usage_safe", {"p_user_id": "user-1"}
        )

    def test_no_usage_left_raises_quota_exceeded(self) -> None:
        repo, _ = self._make_repo_with_mock_client(
            {"success": False, "reason": "no_usage_left"}
        )
        with pytest.raises(QuotaExceeded):
            repo.consume_quota_atomic(AccountId(value="user-2"))

    def test_unexpected_payload_raises_quota_exceeded(self) -> None:
        # 예상치 못한 형식 — 안전을 위해 한도 초과 처리
        repo, _ = self._make_repo_with_mock_client({"weird": True})
        with pytest.raises(QuotaExceeded):
            repo.consume_quota_atomic(AccountId(value="user-3"))

    def test_rpc_exception_falls_back_to_unlimited(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo, _ = self._make_repo_with_mock_client(
            None, raise_exc=RuntimeError("network down")
        )
        with caplog.at_level(
            logging.WARNING,
            logger="src.contexts.identity.infrastructure.supabase_account_repository",
        ):
            result = repo.consume_quota_atomic(AccountId(value="user-4"))
        assert result == _UNLIMITED_DEV_QUOTA
        # warning 로그가 남아야 함
        assert any(
            "consume_quota_atomic RPC 실패" in r.message for r in caplog.records
        )


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
        credits_rows: list[dict] | None = None,
        admin_email: str = "user@example.com",
        is_admin_result: bool = False,
    ) -> SupabaseAccountRepository:
        mock_client = MagicMock()

        # table().select().eq().limit().execute() 체인을 만든다
        def table_side_effect(name: str) -> MagicMock:
            response_rows = {
                "ie_usage": usage_rows or [],
                "ie_api_keys": api_key_rows or [],
                "ie_credits": credits_rows or [],
            }.get(name, [])
            response = MagicMock()
            response.data = response_rows
            tbl = MagicMock()
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                response
            )
            return tbl

        mock_client.table.side_effect = table_side_effect

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
            credits_rows=[{"balance": 100}],
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
        assert ua.credits.balance == 100
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
            credits_rows=[],
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


class TestSave:
    def test_save_upserts_usage_and_credits(self) -> None:
        mock_client = MagicMock()
        # upsert chain
        usage_tbl = MagicMock()
        credits_tbl = MagicMock()

        def table_side_effect(name: str) -> MagicMock:
            return {"ie_usage": usage_tbl, "ie_credits": credits_tbl}[name]

        mock_client.table.side_effect = table_side_effect

        repo = SupabaseAccountRepository()
        repo._get_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]

        account = UserAccount(
            account_id="user-1",
            email="user@example.com",
            quota=UsageQuota(daily_limit=20, used_today=5),
            credits=CreditBalance(balance=42),
        )
        repo.save(account)

        # ie_usage upsert 호출 검증
        usage_tbl.upsert.assert_called_once()
        usage_payload = usage_tbl.upsert.call_args[0][0]
        assert usage_payload["user_id"] == "user-1"
        assert usage_payload["usage_count"] == 15  # 20 - 5
        assert usage_payload["max_usage"] == 20

        # ie_credits upsert 호출 검증
        credits_tbl.upsert.assert_called_once_with(
            {"user_id": "user-1", "balance": 42}
        )
