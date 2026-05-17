"""AI cache deletion response service tests."""

from services.core.cache_deletion_service import build_ai_cache_deletion_response


class _FakeAICache:
    def __init__(self, deleted):
        self.deleted = deleted
        self.calls = []

    def clear(self, video_id=None):
        self.calls.append(video_id)
        return self.deleted


def test_build_ai_cache_deletion_response_clears_all_when_video_id_missing():
    cache = _FakeAICache(deleted=5)

    payload = build_ai_cache_deletion_response({}, ai_cache=cache)

    assert payload == {"success": True, "deleted": 5}
    assert cache.calls == [None]


def test_build_ai_cache_deletion_response_passes_video_id_to_cache():
    cache = _FakeAICache(deleted=1)

    payload = build_ai_cache_deletion_response({"videoId": "abc123"}, ai_cache=cache)

    assert payload == {"success": True, "deleted": 1}
    assert cache.calls == ["abc123"]
