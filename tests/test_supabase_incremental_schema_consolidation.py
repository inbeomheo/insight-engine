"""통합 스키마와 009 보안 수렴이 003~005 객체를 빠뜨리지 않는지 검증한다."""

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
MIGRATION_009 = (
    ROOT / "supabase" / "migrations" / "009_workspace_rls_security.sql"
).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "table",
    ("ie_snippets", "ie_channel_monitors", "ie_workspace_contents"),
)
def test_fresh_schema_contains_incremental_application_table(table: str) -> None:
    assert re.search(
        rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.{table}\b",
        SCHEMA,
        re.IGNORECASE,
    )
    assert re.search(
        rf"ALTER\s+TABLE\s+public\.{table}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
        SCHEMA,
        re.IGNORECASE,
    )


@pytest.mark.parametrize("sql", (SCHEMA, MIGRATION_009), ids=("schema", "009"))
def test_workspace_content_insert_is_draft_and_editor_scoped(sql: str) -> None:
    insert_policy = re.search(
        r"CREATE\s+POLICY\s+workspace_contents_insert.*?;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert insert_policy
    policy = insert_policy.group(0).lower()
    assert "to authenticated" in policy
    assert "author_id = (select auth.uid())" in policy
    assert "status = 'draft'" in policy
    assert "private.workspace_role(workspace_id)" in policy
    assert "('owner', 'editor')" in policy


@pytest.mark.parametrize("sql", (SCHEMA, MIGRATION_009), ids=("schema", "009"))
def test_workspace_content_transition_is_enforced_in_database(sql: str) -> None:
    compact = " ".join(sql.lower().split())
    assert "private.enforce_workspace_content_transition()" in sql
    assert "workspace content immutable fields changed" in sql
    assert "workspace content transition not allowed" in sql
    assert "old.status = 'draft' and new.status = 'review'" in compact
    assert "old.status = 'review' and new.status = 'approved'" in compact
    assert "old.status = 'review' and new.status = 'rejected'" in compact
    assert "old.status = 'approved' and new.status = 'published'" in compact
    assert "old.status in ('approved', 'rejected')" in compact
    assert re.search(
        r"CREATE\s+TRIGGER\s+ie_workspace_contents_transition\s+"
        r"BEFORE\s+UPDATE\s+ON\s+public\.ie_workspace_contents",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"REVOKE\s+ALL\s+ON\s+FUNCTION\s+"
        r"private\.enforce_workspace_content_transition\(\)\s+"
        r"FROM\s+PUBLIC,\s*anon,\s*authenticated",
        sql,
        re.IGNORECASE | re.DOTALL,
    )


def test_incremental_workspace_content_user_foreign_keys_match_fresh_schema() -> None:
    compact_schema = " ".join(SCHEMA.lower().split())
    compact_migration = " ".join(MIGRATION_009.lower().split())

    assert (
        "author_id uuid not null references auth.users(id) on delete restrict"
        in compact_schema
    )
    assert (
        "reviewer_id uuid references auth.users(id) on delete set null"
        in compact_schema
    )
    assert "ie_workspace_contents_author_id_fkey" in compact_migration
    assert "foreign key (author_id) references auth.users(id) on delete restrict" in (
        compact_migration
    )
    assert "ie_workspace_contents_reviewer_id_fkey" in compact_migration
    assert "foreign key (reviewer_id) references auth.users(id) on delete set null" in (
        compact_migration
    )
@pytest.mark.parametrize("sql", (SCHEMA, MIGRATION_009), ids=("schema", "009"))
def test_channel_monitor_user_policy_does_not_grant_update(sql: str) -> None:
    assert "channel_monitors_select_own" in sql
    assert "channel_monitors_insert_own" in sql
    assert "channel_monitors_delete_own" in sql
    assert not re.search(
        r"CREATE\s+POLICY\s+channel_monitors_update_own",
        sql,
        re.IGNORECASE,
    )


def test_fresh_user_api_key_contract_matches_migration_007() -> None:
    constraint = re.search(
        r"CONSTRAINT\s+ie_user_api_keys_row_kind\s+CHECK\s*\((.*?)\n\s*\)\n\);",
        SCHEMA,
        re.IGNORECASE | re.DOTALL,
    )
    assert constraint
    definition = " ".join(constraint.group(1).lower().split())
    assert "key_hash is not null and encrypted_key is null" in definition
    assert "key_hash is null and encrypted_key is not null" in definition

    index = re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+"
        r"uq_ie_user_api_keys_provider\s+ON\s+ie_user_api_keys"
        r"\(user_id,\s*provider,\s*label\)(.*?);",
        SCHEMA,
        re.IGNORECASE | re.DOTALL,
    )
    assert index
    assert "where" not in index.group(1).lower()
