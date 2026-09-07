"""Static contracts for workspace RLS and privileged Supabase RPCs."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_FILES = (
    ROOT / "supabase" / "schema.sql",
    ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql",
)


def _function_sql(sql: str, qualified_name: str) -> str:
    match = re.search(
        rf"CREATE OR REPLACE FUNCTION {re.escape(qualified_name)}\([^)]*\)"
        r"[\s\S]+?\n\$\$;",
        sql,
        re.IGNORECASE,
    )
    assert match is not None, f"missing function: {qualified_name}"
    return match.group(0)


def _policy_sql(sql: str, policy_name: str) -> str:
    match = re.search(
        rf"CREATE POLICY {re.escape(policy_name)}\b[\s\S]+?;",
        sql,
        re.IGNORECASE,
    )
    assert match is not None, f"missing policy: {policy_name}"
    return match.group(0)


def _execute_grantees(sql: str, signature: str) -> set[str]:
    clauses = re.findall(
        rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+TO\s+([^;]+);",
        sql,
        re.IGNORECASE,
    )
    return {
        role.strip().lower()
        for clause in clauses
        for role in clause.split(",")
    }


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_workspace_membership_helper_is_private_and_self_scoped(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    helper = _function_sql(sql, "private.is_workspace_member")
    signature = "private.is_workspace_member(UUID)"

    assert "p_workspace_id UUID" in helper
    assert "p_user_id" not in helper
    assert "SECURITY DEFINER" in helper
    assert "SET search_path = ''" in helper
    assert "FROM public.ie_workspace_members AS membership" in helper
    assert "membership.user_id = (SELECT auth.uid())" in helper

    assert re.search(
        r"REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        r"GRANT USAGE ON SCHEMA private TO authenticated;",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+FROM PUBLIC, anon;",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+TO authenticated;",
        sql,
        re.IGNORECASE,
    )
    assert _execute_grantees(sql, signature) == {"authenticated"}


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_workspace_select_policies_do_not_query_members_recursively(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")

    for policy_name in ("workspace_member_read", "member_read"):
        policy = _policy_sql(sql, policy_name)
        assert "TO authenticated" in policy
        assert "private.is_workspace_member(" in policy
        assert not re.search(
            r"\bFROM\s+(?:public\.)?ie_workspace_members\b",
            policy,
            re.IGNORECASE,
        )


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
@pytest.mark.parametrize(
    ("function_name", "qualified_relation"),
    (
        ("reset_daily_usage", "UPDATE public.ie_usage"),
        ("cleanup_expired_histories", "DELETE FROM public.ie_histories"),
    ),
)
def test_maintenance_rpcs_are_service_role_only(
    sql_path: Path,
    function_name: str,
    qualified_relation: str,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    qualified_name = f"public.{function_name}"
    function_sql = _function_sql(sql, qualified_name)
    signature = f"{qualified_name}()"

    assert "SECURITY DEFINER" in function_sql
    assert "SET search_path = ''" in function_sql
    assert qualified_relation in function_sql
    if function_name == "reset_daily_usage":
        assert "SET usage_count = 20" in function_sql
        assert "WHERE last_reset_date < CURRENT_DATE" in function_sql
    else:
        assert "INTERVAL '7 days'" in function_sql
    assert re.search(
        rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+"
        r"FROM PUBLIC, anon, authenticated;",
        sql,
        re.IGNORECASE,
    )
    assert _execute_grantees(sql, signature) == {"service_role"}
    assert re.search(
        rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+TO service_role;",
        sql,
        re.IGNORECASE,
    )


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_schema_version_rpc_is_non_mutating_and_explicitly_granted(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    function_sql = _function_sql(sql, "public.insight_engine_schema_version")
    signature = "public.insight_engine_schema_version()"

    assert "LANGUAGE sql" in function_sql
    assert "STABLE" in function_sql
    assert "SECURITY INVOKER" in function_sql
    assert "SET search_path = ''" in function_sql
    assert re.search(r"\bSELECT\s+9\s*;", function_sql, re.IGNORECASE)
    assert not re.search(
        r"\b(?:INSERT|UPDATE|DELETE|TRUNCATE)\b",
        function_sql,
        re.IGNORECASE,
    )
    assert re.search(
        rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+FROM PUBLIC;",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        rf"GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+"
        r"TO anon, authenticated, service_role;",
        sql,
        re.IGNORECASE,
    )
    assert _execute_grantees(sql, signature) == {
        "anon",
        "authenticated",
        "service_role",
    }


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_template_usage_rpc_is_hardened_and_service_role_only(
    sql_path: Path,
) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    function_sql = _function_sql(sql, "public.increment_template_usage")
    signature = "public.increment_template_usage(UUID)"

    assert "SECURITY DEFINER" in function_sql
    assert "SET search_path = ''" in function_sql
    assert "UPDATE public.ie_prompt_templates" in function_sql
    assert "IF NOT FOUND THEN" in function_sql
    assert re.search(
        rf"REVOKE ALL ON FUNCTION {re.escape(signature)}\s+"
        r"FROM PUBLIC, anon, authenticated;",
        sql,
        re.IGNORECASE,
    )
    assert _execute_grantees(sql, signature) == {"service_role"}


def test_workspace_security_migration_is_transactional() -> None:
    sql = SQL_FILES[1].read_text(encoding="utf-8").strip()
    assert re.search(r"^--[\s\S]+?\bBEGIN;", sql, re.IGNORECASE)
    assert sql.endswith("COMMIT;")
    assert "decrement_usage_safe" not in sql
    # 009 may converge execute ACLs for functions introduced by 008, but it must
    # not redefine their accounting implementation.
    assert "CREATE OR REPLACE FUNCTION public.reserve_usage_safe" not in sql
    assert "CREATE OR REPLACE FUNCTION public.refund_usage_reservation_safe" not in sql
