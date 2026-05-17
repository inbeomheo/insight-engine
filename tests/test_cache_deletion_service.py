"""Cache deletion response service tests."""

from services.core.cache_deletion_service import build_cache_deletion_response


def test_build_cache_deletion_response_clears_all_when_no_video_target():
    calls = []

    payload = build_cache_deletion_response(
        {},
        get_video_id=lambda url: "unused",
        clear_cache_func=lambda video_id=None: calls.append(video_id) or 3,
    )

    assert payload == {
        "success": True,
        "message": "전체 캐시가 삭제되었습니다.",
        "deleted": 3,
    }
    assert calls == [None]


def test_build_cache_deletion_response_clears_explicit_video_id():
    calls = []

    payload = build_cache_deletion_response(
        {"videoId": "abc123"},
        get_video_id=lambda url: "unused",
        clear_cache_func=lambda video_id=None: calls.append(video_id) or 1,
    )

    assert payload == {
        "success": True,
        "message": "영상 abc123의 캐시가 삭제되었습니다.",
        "deleted": 1,
    }
    assert calls == ["abc123"]


def test_build_cache_deletion_response_extracts_video_id_from_url():
    calls = []

    payload = build_cache_deletion_response(
        {"url": "https://youtube.com/watch?v=abc123"},
        get_video_id=lambda url: "abc123",
        clear_cache_func=lambda video_id=None: calls.append(video_id) or 1,
    )

    assert payload["message"] == "영상 abc123의 캐시가 삭제되었습니다."
    assert payload["deleted"] == 1
    assert calls == ["abc123"]
