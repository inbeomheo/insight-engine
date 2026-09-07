"""YouTube collection quota calls honor the trusted usage boundary."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.core.youtube_collection_service import (
    get_channel_videos,
    get_playlist_videos,
)
from services.usage.usage_lock import UsageLockUnavailable


def _youtube_builder(youtube):
    return lambda *_args, **_kwargs: youtube


def test_playlist_callback_runs_immediately_before_execute(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    events = []
    provider_request = MagicMock()
    provider_request.execute.side_effect = lambda: (
        events.append("provider")
        or {"items": [], "pageInfo": {"totalResults": 0}}
    )
    youtube = MagicMock()
    youtube.playlistItems.return_value.list.return_value = provider_request

    with patch(
        "services.core.youtube_collection_service._get_youtube_build",
        return_value=_youtube_builder(youtube),
    ):
        result = get_playlist_videos(
            "https://youtube.com/playlist?list=PLboundary",
            on_cost_start=lambda: events.append("cost"),
        )

    assert result == {"videos": [], "total": 0}
    assert events == ["cost", "provider"]


def test_playlist_lock_loss_is_not_swallowed(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    provider_request = MagicMock()
    youtube = MagicMock()
    youtube.playlistItems.return_value.list.return_value = provider_request

    def reject_cost():
        raise UsageLockUnavailable("lease lost")

    with patch(
        "services.core.youtube_collection_service._get_youtube_build",
        return_value=_youtube_builder(youtube),
    ), pytest.raises(UsageLockUnavailable):
        get_playlist_videos(
            "https://youtube.com/playlist?list=PLboundary",
            on_cost_start=reject_cost,
        )

    provider_request.execute.assert_not_called()


def test_missing_api_key_is_free(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    on_cost_start = MagicMock()

    result = get_playlist_videos(
        "https://youtube.com/playlist?list=PLboundary",
        on_cost_start=on_cost_start,
    )

    assert "error" in result
    on_cost_start.assert_not_called()


def test_channel_marks_each_execute_boundary(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    events = []
    channel_request = MagicMock()
    playlist_request = MagicMock()
    channel_request.execute.side_effect = lambda: (
        events.append("channel-provider")
        or {
            "items": [{
                "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}},
            }],
        }
    )
    playlist_request.execute.side_effect = lambda: (
        events.append("playlist-provider")
        or {"items": [], "pageInfo": {"totalResults": 0}}
    )
    youtube = MagicMock()
    youtube.channels.return_value.list.return_value = channel_request
    youtube.playlistItems.return_value.list.return_value = playlist_request

    with patch(
        "services.core.youtube_collection_service._get_youtube_build",
        return_value=_youtube_builder(youtube),
    ):
        result = get_channel_videos(
            "https://youtube.com/channel/UCboundary",
            on_cost_start=lambda: events.append("cost"),
        )

    assert result == {"videos": [], "total": 0}
    assert events == [
        "cost",
        "channel-provider",
        "cost",
        "playlist-provider",
    ]
