"""Admin membership lookup must use the explicit server-only client."""
from unittest.mock import MagicMock, patch

from services.data.supabase_admin.admin_queries import is_admin


def _service_client(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    (
        client.table.return_value.select.return_value.eq.return_value
        .limit.return_value.execute.return_value.data
    ) = rows
    return client


def test_admin_lookup_uses_service_role_and_matches_uuid() -> None:
    client = _service_client([{'user_id': 'admin-1'}])

    with patch(
        'services.data.supabase_service.get_service_supabase',
        return_value=client,
    ) as get_service_client:
        assert is_admin('admin-1') is True

    get_service_client.assert_called_once_with()
    client.table.assert_called_once_with('ie_admins')
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        'user_id',
        'admin-1',
    )


def test_admin_lookup_fails_closed_without_service_role() -> None:
    with patch(
        'services.data.supabase_service.get_service_supabase',
        side_effect=RuntimeError('service role unavailable'),
    ):
        assert is_admin('user-1') is False


def test_admin_lookup_does_not_open_client_for_missing_user() -> None:
    with patch(
        'services.data.supabase_service.get_service_supabase',
    ) as get_service_client:
        assert is_admin('') is False

    get_service_client.assert_not_called()
