"""Static contract tests for usage-accounting SQL security boundaries."""
from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SQL_FILES = (
    ROOT / "supabase" / "schema.sql",
    ROOT / "supabase" / "migrations" / "008_usage_reservation_idempotency.sql",
)
USAGE_ACCESS_SQL_FILES = (
    ROOT / "supabase" / "schema.sql",
    ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql",
)
RESERVATION_ACL_SQL_FILES = (
    ROOT / "supabase" / "schema.sql",
    ROOT / "supabase" / "migrations" / "008_usage_reservation_idempotency.sql",
    ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql",
)
RESERVATION_CLEANUP_SQL_FILES = (
    ROOT / "supabase" / "schema.sql",
    ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql",
)


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_legacy_decrement_rpc_is_owned_private_and_atomic(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE OR REPLACE FUNCTION public\.decrement_usage_safe\([\s\S]+?\n\$\$;",
        sql,
    )
    assert match is not None
    function_sql = match.group(0)

    assert "p_amount INT DEFAULT 1" in function_sql
    assert "auth.uid()) IS DISTINCT FROM p_user_id" in function_sql
    assert "v_role <> 'service_role'" in function_sql
    assert "usage_count = usage_count - p_amount" in function_sql
    assert "usage_count >= p_amount" in function_sql
    assert "SET search_path = ''" in function_sql

    signature = "public.decrement_usage_safe(UUID, INT)"
    assert re.search(
        rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+FROM PUBLIC, anon;",
        sql,
    )
    assert re.search(
        rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+"
        r"TO authenticated, service_role;",
        sql,
    )


@pytest.mark.parametrize(
    "sql_path", USAGE_ACCESS_SQL_FILES, ids=lambda path: path.name
)
def test_usage_lookup_rpc_initializes_and_resets_without_direct_writes(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE OR REPLACE FUNCTION public\.get_usage_safe\([\s\S]+?\n\$\$;",
        sql,
    )
    assert match is not None
    function_sql = match.group(0)

    assert "auth.uid()) IS DISTINCT FROM p_user_id" in function_sql
    assert "v_role <> 'service_role'" in function_sql
    assert "pg_advisory_xact_lock" in function_sql
    assert "INSERT INTO public.ie_usage" in function_sql
    assert "ON CONFLICT (user_id) DO UPDATE" in function_sql
    assert "last_reset_date IS DISTINCT FROM CURRENT_DATE" in function_sql
    assert "SET search_path = ''" in function_sql
    assert re.search(
        r"REVOKE ALL ON FUNCTION public\.get_usage_safe\(UUID\)\s+"
        r"FROM PUBLIC, anon;",
        sql,
    )
    assert re.search(
        r"GRANT EXECUTE ON FUNCTION public\.get_usage_safe\(UUID\)\s+"
        r"TO authenticated, service_role;",
        sql,
    )


@pytest.mark.parametrize(
    "sql_path", USAGE_ACCESS_SQL_FILES, ids=lambda path: path.name
)
def test_quota_override_rpc_is_service_role_only(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE OR REPLACE FUNCTION public\.set_usage_quota_admin\([\s\S]+?\n\$\$;",
        sql,
    )
    assert match is not None
    function_sql = match.group(0)

    assert "v_role <> 'service_role'" in function_sql
    assert "p_usage_count > p_max_usage" in function_sql
    assert "SET search_path = ''" in function_sql
    assert re.search(
        r"REVOKE ALL ON FUNCTION public\.set_usage_quota_admin\(UUID, INT, INT\)"
        r"\s+FROM PUBLIC, anon, authenticated;",
        sql,
    )
    assert re.search(
        r"GRANT EXECUTE ON FUNCTION public\.set_usage_quota_admin"
        r"\(UUID, INT, INT\)\s+TO service_role;",
        sql,
    )


def test_authenticated_users_cannot_directly_mutate_usage_rows() -> None:
    schema = USAGE_ACCESS_SQL_FILES[0].read_text(encoding="utf-8")
    migration = USAGE_ACCESS_SQL_FILES[1].read_text(encoding="utf-8")

    assert 'CREATE POLICY "Users can insert own usage"' not in schema
    assert 'CREATE POLICY "Users can update own usage"' not in schema
    assert 'DROP POLICY IF EXISTS "Users can insert own usage"' in migration
    assert 'DROP POLICY IF EXISTS "Users can update own usage"' in migration
    for sql in (schema, migration):
        assert not re.search(
            r"GRANT\s+(?:SELECT,\s*)?(?:INSERT|UPDATE)[^;]*"
            r"ON TABLE public\.ie_usage\s+TO authenticated;",
            sql,
            re.IGNORECASE,
        )


@pytest.mark.parametrize(
    "sql_path", RESERVATION_ACL_SQL_FILES, ids=lambda path: path.name
)
def test_reservation_ledger_mutation_rpcs_are_server_only(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    signatures = (
        "public.reserve_usage_safe(UUID, TEXT, TEXT, TEXT, INT)",
        "public.refund_usage_reservation_safe(UUID, TEXT, TEXT, TEXT)",
    )
    for signature in signatures:
        assert re.search(
            rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+"
            r"FROM PUBLIC, anon, authenticated;",
            sql,
        )
        assert re.search(
            rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+"
            r"TO service_role;",
            sql,
        )
        assert not re.search(
            rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+"
            r"TO[^;]*authenticated",
            sql,
        )


@pytest.mark.parametrize(
    "sql_path", RESERVATION_CLEANUP_SQL_FILES, ids=lambda path: path.name
)
def test_refunded_reservation_cleanup_is_bounded_recent_safe_and_server_only(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE OR REPLACE FUNCTION "
        r"public\.cleanup_expired_usage_reservations_on_insert\(\)"
        r"[\s\S]+?\n\$\$;",
        sql,
    )
    assert match is not None
    function_sql = match.group(0)

    assert "v_role <> 'service_role'" in function_sql
    assert "state = 'refunded'" in function_sql
    assert "refunded_at < pg_catalog.now() - INTERVAL '7 days'" in function_sql
    assert "LIMIT 100" in function_sql
    assert "FOR UPDATE SKIP LOCKED" in function_sql
    assert "state = 'reserved'" not in function_sql
    assert "SET search_path = ''" in function_sql
    assert re.search(
        r"REVOKE ALL ON FUNCTION "
        r"public\.cleanup_expired_usage_reservations_on_insert\(\)\s+"
        r"FROM PUBLIC, anon, authenticated;",
        sql,
    )
    assert "BEFORE INSERT ON public.ie_usage_reservations" in sql
    assert "WHERE state = 'refunded'" in sql
