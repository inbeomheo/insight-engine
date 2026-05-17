"""Playlist video lookup service tests."""

from services.content.playlist_video_service import PlaylistVideoService


class _FakeContentService:
    def __init__(self):
        self.playlist_calls = 0
        self.channel_calls = 0
        self.playlist_result = {"videos": [{"id": "v1"}], "total": 1}
        self.channel_result = {"videos": [{"id": "c1"}], "total": 1}

    def is_playlist_url(self, url):
        return "playlist" in url

    def is_channel_url(self, url):
        return "channel" in url

    def get_playlist_videos(self, url, max_results):
        self.playlist_calls += 1
        return dict(self.playlist_result)

    def get_channel_videos(self, url, max_results):
        self.channel_calls += 1
        return dict(self.channel_result)


def test_playlist_video_service_caches_successful_playlist_results():
    content = _FakeContentService()
    service = PlaylistVideoService(
        content_api=content,
        cache={},
        ttl_seconds=300,
        clock=lambda: 1000.0,
    )

    first_payload, first_status = service.get_videos(
        "https://youtube.com/playlist?list=PL123",
        max_results=10,
    )
    second_payload, second_status = service.get_videos(
        "https://youtube.com/playlist?list=PL123",
        max_results=10,
    )

    assert first_status == 200
    assert second_status == 200
    assert "cached" not in first_payload
    assert second_payload["cached"] is True
    assert content.playlist_calls == 1


def test_playlist_video_service_refreshes_expired_cache_entries():
    now = {"value": 1000.0}
    content = _FakeContentService()
    service = PlaylistVideoService(
        content_api=content,
        cache={},
        ttl_seconds=300,
        clock=lambda: now["value"],
    )

    service.get_videos("https://youtube.com/playlist?list=PL123", max_results=10)
    now["value"] = 1401.0
    service.get_videos("https://youtube.com/playlist?list=PL123", max_results=10)

    assert content.playlist_calls == 2


def test_playlist_video_service_rejects_non_playlist_or_channel_urls():
    service = PlaylistVideoService(
        content_api=_FakeContentService(),
        cache={},
        ttl_seconds=300,
        clock=lambda: 1000.0,
    )

    payload, status = service.get_videos("https://example.com/not-youtube", 10)

    assert status == 400
    assert payload == {"error": "유효한 채널 또는 재생목록 URL이 아닙니다."}


def test_playlist_video_service_does_not_cache_error_results():
    content = _FakeContentService()
    content.playlist_result = {"error": "lookup failed"}
    cache = {}
    service = PlaylistVideoService(
        content_api=content,
        cache=cache,
        ttl_seconds=300,
        clock=lambda: 1000.0,
    )

    payload, status = service.get_videos(
        "https://youtube.com/playlist?list=PL123",
        max_results=10,
    )

    assert status == 400
    assert payload == {"error": "lookup failed"}
    assert cache == {}
