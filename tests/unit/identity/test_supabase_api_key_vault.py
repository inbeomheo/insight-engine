"""SupabaseApiKeyVault 단위 테스트.

Supabase 클라이언트는 mock으로 대체하고, 마스킹 로직과
store/reveal/revoke의 흐름만 검증한다.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.identity.domain.exceptions import InvalidApiKey
from src.contexts.identity.infrastructure.supabase_api_key_vault import (
    SupabaseApiKeyVault,
)
from src.shared.domain.value_objects import AccountId


@pytest.fixture
def account_id() -> AccountId:
    return AccountId("user-uuid-123")


# ---------------------------------------------------------------------------
# _mask 함수
# ---------------------------------------------------------------------------


class TestMask:
    def test_mask_long_key_reveals_last_four(self):
        """8자 이상 키는 마지막 4자만 노출."""
        assert SupabaseApiKeyVault._mask("sk-test-12345678") == "************5678"

    def test_mask_short_key_fully_masked(self):
        """8자 미만 키는 전부 마스킹."""
        assert SupabaseApiKeyVault._mask("short") == "********"

    def test_mask_empty_string(self):
        """빈 문자열도 안전하게 마스킹."""
        assert SupabaseApiKeyVault._mask("") == "********"

    def test_mask_exactly_eight_chars(self):
        """딱 8자 — 뒷 4자만 노출."""
        assert SupabaseApiKeyVault._mask("abcdwxyz") == "****wxyz"


# ---------------------------------------------------------------------------
# Supabase 비활성 (개발 모드) — store/reveal/revoke 동작
# ---------------------------------------------------------------------------


class TestVaultWithoutSupabase:
    def test_store_returns_masked_api_key_when_supabase_disabled(self, account_id):
        """Supabase 비활성: 저장 없이 마스킹된 ApiKey VO만 반환."""
        vault = SupabaseApiKeyVault()
        with patch.object(vault, "_get_client", return_value=None):
            key = vault.store(account_id, "gemini", "sk-test-12345678", "default")

        assert key.provider == "gemini"
        assert key.label == "default"
        assert key.is_active is True
        assert "5678" in key.masked_key
        assert "*" in key.masked_key
        # M1: datetime.utcnow() deprecated → datetime.now(timezone.utc)
        # created_at은 timezone-aware여야 함 (tzinfo 존재)
        assert key.created_at.tzinfo is not None, (
            "ApiKey.created_at은 timezone-aware datetime이어야 함 "
            "(datetime.utcnow() 사용 금지)"
        )

    def test_store_raises_on_short_key(self, account_id):
        """8자 미만 키는 InvalidApiKey."""
        vault = SupabaseApiKeyVault()
        with pytest.raises(InvalidApiKey, match="키 길이가 너무 짧음"):
            vault.store(account_id, "gemini", "short", "default")

    def test_reveal_falls_back_to_env_var(self, account_id, monkeypatch):
        """Supabase 비활성 + 환경변수 있음: 환경변수 값 반환."""
        monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key-value")
        vault = SupabaseApiKeyVault()
        with patch.object(vault, "_get_client", return_value=None):
            result = vault.reveal(account_id, "gemini", "default")
        assert result == "env-gemini-key-value"

    def test_reveal_raises_when_no_env_fallback(self, account_id, monkeypatch):
        """Supabase 비활성 + 환경변수도 없음: InvalidApiKey."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        vault = SupabaseApiKeyVault()
        with patch.object(vault, "_get_client", return_value=None):
            with pytest.raises(InvalidApiKey, match="환경변수 fallback도 없음"):
                vault.reveal(account_id, "gemini", "default")

    def test_revoke_noop_when_supabase_disabled(self, account_id):
        """Supabase 비활성: revoke는 경고만 + no-op (예외 없음)."""
        vault = SupabaseApiKeyVault()
        with patch.object(vault, "_get_client", return_value=None):
            # 예외 없이 통과해야 함
            vault.revoke(account_id, "gemini", "default")


# ---------------------------------------------------------------------------
# Supabase mock: 정상 케이스
# ---------------------------------------------------------------------------


class TestVaultWithMockedSupabase:
    def _make_client(self):
        client = MagicMock()
        # client.table().upsert().execute() 체인 모킹
        table = MagicMock()
        client.table.return_value = table
        return client, table

    def test_store_calls_supabase_upsert(self, account_id):
        """정상 케이스: 암호화된 키가 upsert에 전달됨."""
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        table.upsert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

        with patch.object(vault, "_get_client", return_value=client), \
             patch.object(vault, "_encrypt", return_value="ENC(sk-test-12345678)"):
            key = vault.store(account_id, "deepseek", "sk-test-12345678", "default")

        # 호출 인자 확인
        called_payload = table.upsert.call_args.args[0]
        assert called_payload["user_id"] == "user-uuid-123"
        assert called_payload["provider"] == "deepseek"
        assert called_payload["encrypted_key"] == "ENC(sk-test-12345678)"
        assert called_payload["is_active"] is True
        # 반환 VO 검증
        assert key.provider == "deepseek"
        assert "5678" in key.masked_key
        # M1: created_at은 timezone-aware
        assert key.created_at.tzinfo is not None

    def test_reveal_decrypts_active_key(self, account_id):
        """정상: 활성 행을 찾아 _decrypt 결과를 반환."""
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        # client.table().select().eq().eq().eq().limit().execute() 체인
        chain = table.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(
            data=[{"encrypted_key": "ENC(plain)", "is_active": True}]
        )

        with patch.object(vault, "_get_client", return_value=client), \
             patch.object(vault, "_decrypt", return_value="plain-key") as dec:
            result = vault.reveal(account_id, "gemini", "default")
        assert result == "plain-key"
        dec.assert_called_once_with("ENC(plain)")

    def test_reveal_raises_when_decrypt_returns_empty(self, account_id):
        """복호화 실패(None/empty)는 평문 키로 취급하지 않는다."""
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        chain = table.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(
            data=[{"encrypted_key": "bad-token", "is_active": True}]
        )

        with patch.object(vault, "_get_client", return_value=client), \
             patch.object(vault, "_decrypt", return_value=None):
            with pytest.raises(InvalidApiKey, match="키 복호화 실패"):
                vault.reveal(account_id, "gemini", "default")

    def test_reveal_raises_when_no_active_row(self, account_id):
        """행이 없거나 is_active=False면 InvalidApiKey."""
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        chain = table.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(data=[])

        with patch.object(vault, "_get_client", return_value=client):
            with pytest.raises(InvalidApiKey, match="활성 키 없음"):
                vault.reveal(account_id, "gemini", "default")

    def test_reveal_raises_when_row_inactive(self, account_id):
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        chain = table.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value
        chain.execute.return_value = MagicMock(
            data=[{"encrypted_key": "ENC(x)", "is_active": False}]
        )

        with patch.object(vault, "_get_client", return_value=client):
            with pytest.raises(InvalidApiKey, match="활성 키 없음"):
                vault.reveal(account_id, "gemini", "default")

    def test_revoke_calls_supabase_update(self, account_id):
        """정상: is_active=False로 update 호출."""
        vault = SupabaseApiKeyVault()
        client, table = self._make_client()
        chain = table.update.return_value.eq.return_value.eq.return_value.eq.return_value
        chain.execute.return_value = MagicMock(data=[])

        with patch.object(vault, "_get_client", return_value=client):
            vault.revoke(account_id, "gemini", "default")

        # update 호출 인자가 is_active=False인지 확인
        table.update.assert_called_once_with({"is_active": False})
