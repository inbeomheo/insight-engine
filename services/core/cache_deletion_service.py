"""Content cache deletion response helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_cache_deletion_response(
    data: Mapping[str, Any],
    *,
    get_video_id: Callable[[str], str | None],
    clear_cache_func: Callable[[str | None], int],
) -> dict[str, Any]:
    """Delete cache and build the `/api/cache` response payload."""
    video_id = data.get("videoId")

    url = data.get("url")
    if url and not video_id:
        video_id = get_video_id(url)

    deleted = clear_cache_func(video_id)

    if video_id:
        return {
            "success": True,
            "message": f"영상 {video_id}의 캐시가 삭제되었습니다.",
            "deleted": deleted,
        }

    return {
        "success": True,
        "message": "전체 캐시가 삭제되었습니다.",
        "deleted": deleted,
    }
