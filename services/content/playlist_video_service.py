"""Playlist/channel video lookup with TTL caching."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
import time
from typing import Any


class PlaylistVideoService:
    """Fetch playlist or channel videos and cache successful lookups."""

    def __init__(
        self,
        *,
        content_api: Any,
        cache: MutableMapping[str, dict] | None = None,
        ttl_seconds: int = 300,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.content_api = content_api
        self.cache = cache if cache is not None else {}
        self.ttl_seconds = ttl_seconds
        self.clock = clock or time.time

    def get_videos(self, url: str, max_results: int) -> tuple[dict, int]:
        """Return video lookup payload and HTTP status code."""
        cache_key = f"{url}|{max_results}"
        now = self.clock()

        cached = self.cache.get(cache_key)
        if cached and (now - cached["ts"]) < self.ttl_seconds:
            result = dict(cached["data"])
            result["cached"] = True
            return result, 200

        if self.content_api.is_playlist_url(url):
            result = self.content_api.get_playlist_videos(url, max_results)
        elif self.content_api.is_channel_url(url):
            result = self.content_api.get_channel_videos(url, max_results)
        else:
            return {"error": "유효한 채널 또는 재생목록 URL이 아닙니다."}, 400

        if "error" in result:
            return result, 400

        self.cache[cache_key] = {"data": dict(result), "ts": now}
        return result, 200
