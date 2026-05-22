"""Channel Monitoring 도메인 VO 단위 테스트."""
from __future__ import annotations

import pytest

from src.contexts.channel_monitoring.domain.value_objects import (
    ChannelId,
    Interval,
    MonitorOwnerId,
)


class TestChannelId:
    def test_valid(self):
        cid = ChannelId("UCabc123")
        assert str(cid) == "UCabc123"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="ChannelId"):
            ChannelId("")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="ChannelId"):
            ChannelId(None)  # type: ignore[arg-type]

    def test_frozen(self):
        cid = ChannelId("UC1")
        with pytest.raises(AttributeError):
            cid.value = "UC2"  # type: ignore[misc]


class TestMonitorOwnerId:
    def test_valid(self):
        oid = MonitorOwnerId("user-1")
        assert str(oid) == "user-1"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="MonitorOwnerId"):
            MonitorOwnerId("")


class TestInterval:
    def test_valid(self):
        iv = Interval(minutes=30)
        assert iv.minutes == 30

    def test_min_boundary(self):
        Interval(minutes=5)  # OK
        with pytest.raises(ValueError, match="최소"):
            Interval(minutes=4)

    def test_max_boundary(self):
        Interval(minutes=1440)  # OK
        with pytest.raises(ValueError, match="최대"):
            Interval(minutes=1441)

    def test_non_int_raises(self):
        with pytest.raises(ValueError, match="정수"):
            Interval(minutes="30")  # type: ignore[arg-type]

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="최소"):
            Interval(minutes=-1)
