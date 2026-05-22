"""ChannelSubscription Aggregate 단위 테스트."""
from __future__ import annotations

import pytest

from src.contexts.channel_monitoring.domain.channel_subscription import (
    ChannelSubscription,
)


class TestFromDict:
    def test_basic(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "UC1", "channel_title": "T", "style_id": "blog_seo"},
            owner_id="user-1",
        )
        assert str(sub.channel_id) == "UC1"
        assert sub.channel_title == "T"
        assert sub.style_id == "blog_seo"
        assert sub.is_active is True

    def test_missing_channel_id(self):
        with pytest.raises(ValueError, match="channel_id"):
            ChannelSubscription.from_dict({}, owner_id="user-1")

    def test_empty_channel_id(self):
        with pytest.raises(ValueError, match="channel_id"):
            ChannelSubscription.from_dict({"channel_id": "   "}, owner_id="u")

    def test_default_modifiers(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "UC1"}, owner_id="u"
        )
        assert sub.modifiers == {
            "length": "medium",
            "writing_style": "conversational",
            "language": "ko",
        }

    def test_custom_modifiers(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "UC1", "modifiers": {"language": "en"}},
            owner_id="u",
        )
        assert sub.modifiers == {"language": "en"}

    def test_default_interval_30(self):
        sub = ChannelSubscription.from_dict({"channel_id": "UC1"}, "u")
        assert sub.interval.minutes == 30

    def test_custom_interval(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "UC1", "interval_minutes": 60}, "u"
        )
        assert sub.interval.minutes == 60

    def test_invalid_interval_propagates(self):
        with pytest.raises(ValueError, match="최소"):
            ChannelSubscription.from_dict(
                {"channel_id": "UC1", "interval_minutes": 1}, "u"
            )

    def test_title_strip(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "UC1", "channel_title": "  hi  "}, "u"
        )
        assert sub.channel_title == "hi"

    def test_channel_id_strip(self):
        sub = ChannelSubscription.from_dict(
            {"channel_id": "  UC1  "}, "u"
        )
        assert str(sub.channel_id) == "UC1"


class TestToRow:
    def test_serialization(self):
        sub = ChannelSubscription.from_dict(
            {
                "channel_id": "UC1",
                "channel_title": "T",
                "style_id": "summary",
                "interval_minutes": 60,
            },
            owner_id="user-1",
        )
        row = sub.to_row()
        assert row["user_id"] == "user-1"
        assert row["channel_id"] == "UC1"
        assert row["channel_title"] == "T"
        assert row["style_id"] == "summary"
        assert row["interval_minutes"] == 60
        assert row["is_active"] is True
        assert "modifiers" in row
