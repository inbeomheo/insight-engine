"""Supabase Data API table grants must remain explicit and least-privileged."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from pglast import parse_sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "supabase" / "schema.sql"
MIGRATION = ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql"
SQL_FILES = (SCHEMA, MIGRATION)
ALL_SQL_FILES = (
    SCHEMA,
    *sorted((ROOT / "supabase" / "migrations").glob("*.sql")),
)

DATA_API_ROLES = ("public", "anon", "authenticated", "service_role")
CRUD = frozenset({"select", "insert", "update", "delete"})


def _grants(
    *,
    authenticated: tuple[str, ...] = (),
    service_role: tuple[str, ...] = (),
) -> dict[str, frozenset[str]]:
    return {
        "public": frozenset(),
        "anon": frozenset(),
        "authenticated": frozenset(authenticated),
        "service_role": frozenset(service_role),
    }


# Audited against the active Supabase clients. Quota mutations are RPC-only;
# authenticated users may only read their RLS-filtered usage row directly.
EXPECTED_TABLE_GRANTS = {
    "ie_usage": _grants(
        authenticated=("select",),
        service_role=("select",),
    ),
    "ie_usage_reservations": _grants(),
    "ie_histories": _grants(
        authenticated=("select", "insert"),
        service_role=("select",),
    ),
    "ie_api_keys": _grants(authenticated=("select",)),
    "ie_user_api_keys": _grants(
        authenticated=("select", "insert", "update"),
    ),
    "ie_custom_styles": _grants(),
    "ie_admins": _grants(service_role=("select",)),
    "ie_scheduled_posts": _grants(),
    "ie_workspaces": _grants(
        authenticated=("select", "insert", "update", "delete"),
    ),
    "ie_workspace_members": _grants(
        authenticated=("select", "insert", "update", "delete"),
    ),
    "ie_prompt_templates": _grants(
        authenticated=("select", "insert", "update", "delete"),
    ),
    "ie_style_profiles": _grants(
        authenticated=("select", "insert", "update"),
    ),
    "ie_snippets": _grants(),
    "ie_channel_monitors": _grants(
        authenticated=("select", "insert", "delete"),
        service_role=("select", "update"),
    ),
    "ie_workspace_contents": _grants(
        authenticated=("select", "insert", "update"),
    ),
}

EXPECTED_VIEW_GRANTS = {
    "ie_usage_with_email": _grants(service_role=("select",)),
    "ie_histories_with_email": _grants(service_role=("select",)),
}


def _roles(value: str) -> set[str]:
    return {role.strip().lower() for role in value.split(",")}


def _privileges(value: str) -> set[str]:
    privileges = {item.strip().lower() for item in value.split(",")}
    assert privileges <= CRUD
    return privileges


def _acl_section(sql: str) -> str:
    begin = "-- DATA_API_TABLE_ACL_BEGIN"
    end = "-- DATA_API_TABLE_ACL_END"
    assert sql.count(begin) == 1
    assert sql.count(end) == 1
    return sql.split(begin, 1)[1].split(end, 1)[0]


def _parse_table_grants(sql: str) -> dict[str, dict[str, set[str]]]:
    parsed: dict[str, dict[str, set[str]]] = {}
    for privileges, relation, grantees in re.findall(
        r"\bGRANT\s+([A-Z\s,]+?)\s+ON\s+TABLE\s+"
        r"public\.([a-z0-9_]+)\s+TO\s+([^;]+);",
        sql,
        re.IGNORECASE,
    ):
        relation_grants = parsed.setdefault(
            relation.lower(),
            {role: set() for role in DATA_API_ROLES},
        )
        for role in _roles(grantees):
            assert role in DATA_API_ROLES
            relation_grants[role].update(_privileges(privileges))
    return parsed


def _parse_revoke_roles(sql: str) -> dict[str, set[str]]:
    parsed: dict[str, set[str]] = {}
    for relation, grantees in re.findall(
        r"\bREVOKE\s+ALL\s+ON\s+TABLE\s+public\.([a-z0-9_]+)\s+"
        r"FROM\s+([^;]+);",
        sql,
        re.IGNORECASE,
    ):
        parsed.setdefault(relation.lower(), set()).update(_roles(grantees))
    return parsed


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_table_acl_is_complete_exact_and_equivalent(sql_path: Path) -> None:
    section = _acl_section(sql_path.read_text(encoding="utf-8"))
    grants = _parse_table_grants(section)
    revokes = _parse_revoke_roles(section)

    assert set(revokes) == set(EXPECTED_TABLE_GRANTS)
    assert set(grants) <= set(EXPECTED_TABLE_GRANTS)

    for relation, expected in EXPECTED_TABLE_GRANTS.items():
        assert revokes[relation] == set(DATA_API_ROLES)
        actual = grants.get(
            relation,
            {role: set() for role in DATA_API_ROLES},
        )
        assert actual == {
            role: set(privileges) for role, privileges in expected.items()
        }


def test_fresh_schema_covers_every_created_application_table() -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    created_tables = {
        name.lower()
        for name in re.findall(
            r"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"
            r"(?:public\.)?([a-z0-9_]+)",
            sql,
            re.IGNORECASE,
        )
    }
    assert created_tables == set(EXPECTED_TABLE_GRANTS)


def test_authenticated_grants_only_target_rls_tables() -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    rls_tables = {
        name.lower()
        for name in re.findall(
            r"\bALTER\s+TABLE\s+(?:public\.)?([a-z0-9_]+)\s+"
            r"ENABLE\s+ROW\s+LEVEL\s+SECURITY\s*;",
            sql,
            re.IGNORECASE,
        )
    }
    authenticated_tables = {
        relation
        for relation, grants in EXPECTED_TABLE_GRANTS.items()
        if grants["authenticated"]
    }
    assert authenticated_tables <= rls_tables


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_admin_views_are_service_role_read_only(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    grants = _parse_table_grants(sql)
    revokes = _parse_revoke_roles(sql)

    for relation, expected in EXPECTED_VIEW_GRANTS.items():
        assert grants[relation] == {
            role: set(privileges) for role, privileges in expected.items()
        }
        assert revokes[relation] == set(DATA_API_ROLES)


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_anon_has_no_direct_table_grant(sql_path: Path) -> None:
    grants = _parse_table_grants(sql_path.read_text(encoding="utf-8"))
    assert all(not roles["anon"] for roles in grants.values())


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_usage_reservations_remain_rpc_only(sql_path: Path) -> None:
    section = _acl_section(sql_path.read_text(encoding="utf-8"))
    grants = _parse_table_grants(section)
    assert "ie_usage_reservations" not in grants
    assert _parse_revoke_roles(section)["ie_usage_reservations"] == set(
        DATA_API_ROLES
    )


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda path: path.name)
def test_uuid_tables_require_no_sequence_grants(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    assert not re.search(
        r"\b(?:SERIAL|BIGSERIAL|SMALLSERIAL|NEXTVAL\s*\(|"
        r"GENERATED\s+[^;]+\s+AS\s+IDENTITY)\b",
        sql,
        re.IGNORECASE,
    )
    assert not re.search(
        r"\bGRANT\s+[^;]+\s+ON\s+(?:ALL\s+)?SEQUENCES?\b",
        sql,
        re.IGNORECASE,
    )


@pytest.mark.parametrize("sql_path", ALL_SQL_FILES, ids=lambda path: path.name)
def test_sql_parses_with_pglast(sql_path: Path) -> None:
    statements = parse_sql(sql_path.read_text(encoding="utf-8"))
    assert statements
