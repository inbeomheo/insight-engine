"""사용량 호환 경로가 anon Data API 권한에 의존하지 않는지 검증한다."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.data.supabase_service import decrement_usage, get_usage


def test_get_usage_uses_validated_user_client() -> None:
    query = MagicMock()
    query.execute.return_value = SimpleNamespace(data={
        'usage_count': 7,
        'max_usage': 20,
        'can_use': True,
    })
    client = MagicMock()
    client.rpc.return_value = query

    with patch(
        'services.data.supabase_service.get_user_supabase',
        return_value=client,
    ) as user_client:
        result = get_usage('user-1', validated_access_token='verified-jwt')

    user_client.assert_called_once_with(validated_access_token='verified-jwt')
    client.rpc.assert_called_once_with(
        'get_usage_safe',
        {'p_user_id': 'user-1'},
    )
    client.table.assert_not_called()
    assert result == {
        'usage_count': 7,
        'max_usage': 20,
        'can_use': True,
    }


def test_decrement_usage_uses_only_atomic_user_rpc() -> None:
    rpc_query = MagicMock()
    rpc_query.execute.return_value = SimpleNamespace(
        data={'success': True, 'new_count': 6},
    )
    client = MagicMock()
    client.rpc.return_value = rpc_query

    with patch(
        'services.data.supabase_service.get_user_supabase',
        return_value=client,
    ) as user_client:
        assert decrement_usage(
            'user-1',
            validated_access_token='verified-jwt',
        ) is True

    user_client.assert_called_once_with(validated_access_token='verified-jwt')
    client.rpc.assert_called_once_with(
        'decrement_usage_safe',
        {'p_user_id': 'user-1', 'p_amount': 1},
    )
    client.table.assert_not_called()


def test_decrement_usage_fails_closed_when_rpc_errors() -> None:
    client = MagicMock()
    client.rpc.side_effect = RuntimeError('database unavailable')

    with patch(
        'services.data.supabase_service.get_user_supabase',
        return_value=client,
    ):
        assert decrement_usage(
            'user-1',
            validated_access_token='verified-jwt',
        ) is False

    client.table.assert_not_called()
