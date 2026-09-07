"""Channel monitor Supabase clients must preserve RLS request isolation."""
from unittest.mock import MagicMock, patch

from src.contexts.channel_monitoring.domain.channel_subscription import (
    ChannelSubscription,
)
from src.contexts.channel_monitoring.infrastructure.supabase_channel_repository import (
    SupabaseChannelMonitorRepository,
)


def _query_client(data: list[dict] | None = None) -> MagicMock:
    client = MagicMock()
    query = client.table.return_value
    query.insert.return_value.execute.return_value.data = data or []
    query.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
        data or []
    )
    query.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
        data or []
    )
    return client


def test_user_repository_uses_fresh_rls_helper_for_every_operation() -> None:
    repository = SupabaseChannelMonitorRepository()
    subscription = ChannelSubscription.from_dict(
        {
            "channel_id": "channel-1",
            "interval_minutes": 30,
        },
        owner_id="user-1",
    )
    client = _query_client([{"id": "monitor-1"}])

    with patch(
        "src.contexts.channel_monitoring.infrastructure."
        "supabase_channel_repository.get_user_supabase",
        return_value=client,
    ) as get_user_client:
        assert repository.register(subscription) == {"id": "monitor-1"}
        assert repository.list_for_owner("user-1") == [{"id": "monitor-1"}]
        assert repository.delete("user-1", "monitor-1") is True

    assert get_user_client.call_count == 3


def test_background_scheduler_uses_explicit_service_role_client() -> None:
    from services.data import scheduler_worker

    service_client = MagicMock()
    with (
        patch(
            "services.data.supabase_service.is_supabase_enabled",
            return_value=True,
        ),
        patch(
            "services.data.supabase_service.get_service_supabase",
            return_value=service_client,
        ) as get_service_client,
        patch(
            "services.platform.channel_monitor_service.check_monitors",
            return_value=[],
        ) as check_monitors,
    ):
        scheduler_worker._check_channel_monitors()

    get_service_client.assert_called_once_with()
    check_monitors.assert_called_once_with(service_client)
