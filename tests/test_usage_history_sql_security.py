"""Static contracts for the daily usage history RPC."""
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SQL_FILES = (
    ROOT / 'supabase' / 'schema.sql',
    ROOT / 'supabase' / 'migrations' / '009_workspace_rls_security.sql',
)


@pytest.mark.parametrize('sql_path', SQL_FILES, ids=lambda path: path.name)
def test_usage_history_is_reservation_backed_and_self_scoped(sql_path: Path) -> None:
    sql = sql_path.read_text(encoding='utf-8')
    match = re.search(
        r'CREATE OR REPLACE FUNCTION public\.get_daily_usage_history\('
        r'[\s\S]+?\n\$\$;',
        sql,
    )
    assert match is not None
    function_sql = match.group(0)

    assert 'SECURITY DEFINER' in function_sql
    assert "SET search_path = ''" in function_sql
    assert "v_role <> 'service_role'" in function_sql
    assert 'v_user_id IS DISTINCT FROM p_user_id' in function_sql
    assert 'p_days < 1 OR p_days > 90' in function_sql
    assert 'FROM pg_catalog.generate_series(' in function_sql
    assert 'LEFT JOIN public.ie_usage_reservations AS reservation' in function_sql
    assert "reservation.state = 'reserved'" in function_sql

    signature = 'public.get_daily_usage_history(UUID, INT)'
    assert re.search(
        rf'REVOKE ALL ON FUNCTION {re.escape(signature)}\s+FROM PUBLIC, anon;',
        sql,
    )
    assert re.search(
        rf'GRANT EXECUTE ON FUNCTION {re.escape(signature)}\s+'
        r'TO authenticated, service_role;',
        sql,
    )
