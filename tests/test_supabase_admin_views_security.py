"""Admin-only Supabase views must not bypass RLS for Data API users."""
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'supabase' / 'schema.sql'
MIGRATION = ROOT / 'supabase' / 'migrations' / '009_workspace_rls_security.sql'
ADMIN_VIEWS = ('ie_usage_with_email', 'ie_histories_with_email')


@pytest.mark.parametrize('view_name', ADMIN_VIEWS)
def test_schema_admin_view_is_security_invoker_and_service_only(
    view_name: str,
) -> None:
    sql = SCHEMA.read_text(encoding='utf-8')
    declaration = re.search(
        rf'CREATE OR REPLACE VIEW public\.{view_name}\s+'
        r'WITH \(security_invoker = true, security_barrier = true\) AS',
        sql,
        re.IGNORECASE,
    )
    assert declaration is not None
    _assert_service_only_acl(sql, view_name)


@pytest.mark.parametrize('view_name', ADMIN_VIEWS)
def test_migration_hardens_existing_admin_view(view_name: str) -> None:
    sql = MIGRATION.read_text(encoding='utf-8')
    assert re.search(
        rf'ALTER VIEW public\.{view_name}\s+'
        r'SET \(security_invoker = true, security_barrier = true\);',
        sql,
        re.IGNORECASE,
    )
    _assert_service_only_acl(sql, view_name)


def _assert_service_only_acl(sql: str, view_name: str) -> None:
    signature = re.escape(f'public.{view_name}')
    assert re.search(
        rf'REVOKE ALL ON TABLE {signature}\s+'
        r'FROM PUBLIC, anon, authenticated;',
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        rf'GRANT SELECT ON TABLE {signature}\s+TO service_role;',
        sql,
        re.IGNORECASE,
    )
