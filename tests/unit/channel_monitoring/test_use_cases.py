"""Channel Monitoring UseCase 단위 테스트 (Mock Repository)."""
from __future__ import annotations

from src.contexts.channel_monitoring.application.ports import (
    IChannelMonitorRepository,
)
from src.contexts.channel_monitoring.application.use_cases import (
    DeleteChannelMonitorUseCase,
    ListChannelMonitorsUseCase,
    RegisterChannelMonitorUseCase,
)
from src.contexts.channel_monitoring.domain.channel_subscription import (
    ChannelSubscription,
)


class FakeRepo(IChannelMonitorRepository):
    def __init__(self):
        self.registered: list[ChannelSubscription] = []
        self.list_response: list[dict] = []
        self.delete_calls: list[tuple] = []

    def register(self, subscription):
        self.registered.append(subscription)
        return {"id": "m-1", "channel_id": str(subscription.channel_id)}

    def list_for_owner(self, user_id):
        return list(self.list_response)

    def delete(self, user_id, monitor_id):
        self.delete_calls.append((user_id, monitor_id))
        return True


class TestRegister:
    def test_basic(self):
        repo = FakeRepo()
        uc = RegisterChannelMonitorUseCase(repo)
        result = uc.execute("user-1", {"channel_id": "UC1"})
        assert result == {"id": "m-1", "channel_id": "UC1"}
        assert len(repo.registered) == 1

    def test_no_user(self):
        repo = FakeRepo()
        uc = RegisterChannelMonitorUseCase(repo)
        assert uc.execute(None, {"channel_id": "UC1"}) is None
        assert not repo.registered

    def test_invalid_data(self):
        repo = FakeRepo()
        uc = RegisterChannelMonitorUseCase(repo)
        assert uc.execute("user-1", {}) is None  # channel_id 누락
        assert not repo.registered

    def test_invalid_interval(self):
        repo = FakeRepo()
        uc = RegisterChannelMonitorUseCase(repo)
        assert uc.execute("user-1", {"channel_id": "UC1", "interval_minutes": 1}) is None


class TestList:
    def test_with_user(self):
        repo = FakeRepo()
        repo.list_response = [{"id": "m-1"}, {"id": "m-2"}]
        uc = ListChannelMonitorsUseCase(repo)
        assert uc.execute("user-1") == [{"id": "m-1"}, {"id": "m-2"}]

    def test_no_user(self):
        assert ListChannelMonitorsUseCase(FakeRepo()).execute(None) == []


class TestDelete:
    def test_ok(self):
        repo = FakeRepo()
        uc = DeleteChannelMonitorUseCase(repo)
        assert uc.execute("u", "m-1") is True
        assert repo.delete_calls == [("u", "m-1")]

    def test_no_user(self):
        assert DeleteChannelMonitorUseCase(FakeRepo()).execute(None, "m-1") is False

    def test_no_monitor_id(self):
        assert DeleteChannelMonitorUseCase(FakeRepo()).execute("u", "") is False
