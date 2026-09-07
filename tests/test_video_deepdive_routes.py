from unittest.mock import patch

import pytest
from flask import g


def _app(tmp_path):
    import app as flask_app

    app = flask_app.create_app({"TESTING": True, "VIDEO_DEEPDIVE_DIR": str(tmp_path)})
    return app.test_client()


def _authenticated_user(token):
    g.user_id = {"token-a": "user-a", "token-b": "user-b"}[token]
    g.user_email = f"{g.user_id}@example.test"
    g.access_token = token
    return {"valid": True, "error": None, "code": None}


def _auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Origin": "http://localhost:3000",
    }


def test_create_deepdive_from_generated_result(tmp_path):
    client = _app(tmp_path)

    resp = client.post(
        "/api/video-deepdives/from-result",
        json={
            "video_id": "dQw4w9WgXcQ",
            "title": "튜토리얼 영상",
            "content": "### Step 1: 설정\n[스크린샷 1]: 설정 화면을 보여주세요.",
            "transcript_segments": [{"start": 3.2, "text": "설정 화면을 엽니다."}],
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        },
        headers={"Origin": "http://localhost:3000"},
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["item"]["id"] == "dQw4w9WgXcQ"
    assert data["item"]["visual_suggestions"][0]["description"] == "설정 화면을 보여주세요."
    assert data["viewer_url"] == "/deepdives/dQw4w9WgXcQ"

    get_resp = client.get("/api/video-deepdives/dQw4w9WgXcQ")
    assert get_resp.status_code == 200
    loaded = get_resp.get_json()
    assert loaded["meta"]["title"] == "튜토리얼 영상"
    assert loaded["body"] == "[00:00:03] 설정 화면을 엽니다."


def test_patch_deepdive_slides_updates_notes(tmp_path):
    client = _app(tmp_path)
    client.post(
        "/api/video-deepdives/from-result",
        json={"video_id": "dQw4w9WgXcQ", "title": "T", "transcript": "body"},
        headers={"Origin": "http://localhost:3000"},
    )

    resp = client.patch(
        "/api/video-deepdives/dQw4w9WgXcQ",
        json={
            "slides": [
                {
                    "idx": 1,
                    "t": 1.0,
                    "mmss": "00:01",
                    "title": "화면",
                    "note": "수정된 노트",
                    "img": "/api/video-deepdives/dQw4w9WgXcQ/media/x.jpg",
                }
            ]
        },
        headers={"Origin": "http://localhost:3000"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["item"]["slides"][0]["note"] == "수정된 노트"


def test_deepdive_routes_reject_bad_video_id(tmp_path):
    client = _app(tmp_path)

    resp = client.get("/api/video-deepdives/..%2Fsecret")

    assert resp.status_code == 400
    assert "YouTube" in resp.get_json()["error"] or "영상 ID" in resp.get_json()["error"]


def test_deepdive_routes_isolate_all_reads_writes_and_media_by_user(tmp_path):
    from services.media.video_deepdive_service import VideoDeepDiveLibrary

    client = _app(tmp_path)
    media_url = "/api/video-deepdives/dQw4w9WgXcQ/media/owned.jpg"
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=True,
    ), patch(
        "src.contexts.identity.interface.auth_decorators._validate_token",
        side_effect=_authenticated_user,
    ):
        created = client.post(
            "/api/video-deepdives/from-result",
            json={
                "video_id": "dQw4w9WgXcQ",
                "title": "A 전용",
                "slides": [{"idx": 1, "t": 1, "img": media_url}],
            },
            headers=_auth_headers("token-a"),
        )
        assert created.status_code == 201

        owner_library = VideoDeepDiveLibrary(tmp_path, owner_id="user-a")
        (owner_library.media_dir("dQw4w9WgXcQ") / "owned.jpg").write_bytes(b"owned")

        assert client.get(
            "/api/video-deepdives/dQw4w9WgXcQ",
            headers=_auth_headers("token-a"),
        ).status_code == 200
        assert client.get(
            "/api/video-deepdives/dQw4w9WgXcQ/media/owned.jpg",
            headers=_auth_headers("token-a"),
        ).data == b"owned"

        assert client.get(
            "/api/video-deepdives/dQw4w9WgXcQ",
            headers=_auth_headers("token-b"),
        ).status_code == 404
        assert client.patch(
            "/api/video-deepdives/dQw4w9WgXcQ",
            json={"slides": []},
            headers=_auth_headers("token-b"),
        ).status_code == 404
        assert client.get(
            "/api/video-deepdives/dQw4w9WgXcQ/media/owned.jpg",
            headers=_auth_headers("token-b"),
        ).status_code == 404
        assert client.get(
            "/api/video-deepdives",
            headers=_auth_headers("token-b"),
        ).get_json() == {"items": [], "total": 0}


def test_same_public_video_id_does_not_collide_between_users(tmp_path):
    client = _app(tmp_path)
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=True,
    ), patch(
        "src.contexts.identity.interface.auth_decorators._validate_token",
        side_effect=_authenticated_user,
    ):
        for token, title in (("token-a", "A 제목"), ("token-b", "B 제목")):
            response = client.post(
                "/api/video-deepdives/from-result",
                json={"video_id": "dQw4w9WgXcQ", "title": title},
                headers=_auth_headers(token),
            )
            assert response.status_code == 201

        first = client.get(
            "/api/video-deepdives/dQw4w9WgXcQ",
            headers=_auth_headers("token-a"),
        ).get_json()
        second = client.get(
            "/api/video-deepdives/dQw4w9WgXcQ",
            headers=_auth_headers("token-b"),
        ).get_json()

    assert first["meta"]["title"] == "A 제목"
    assert second["meta"]["title"] == "B 제목"


def test_extract_rejects_parallel_request_for_same_user(tmp_path):
    from services.media.video_deepdive_service import VideoDeepDiveLibrary

    client = _app(tmp_path)
    library = VideoDeepDiveLibrary(tmp_path, owner_id="local-anonymous")
    with library.extraction_slot(), patch(
        "routes.video_deepdive_routes.build_visual_deepdive_from_video"
    ) as build:
        response = client.post(
            "/api/video-deepdives/extract",
            json={"video_id": "dQw4w9WgXcQ"},
            headers={"Origin": "http://localhost:3000"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.201"},
        )

    assert response.status_code == 409
    assert response.get_json()["code"] == "VIDEO_DEEPDIVE_BUSY"
    build.assert_not_called()


def test_extract_is_rate_limited_before_repeating_expensive_work(tmp_path):
    from extensions import limiter

    client = _app(tmp_path)
    previous_enabled = limiter.enabled
    client.application.config['RATELIMIT_ENABLED'] = True
    limiter.enabled = True
    limiter.init_app(client.application)
    limiter.reset()
    result = {
        "meta": {"id": "dQw4w9WgXcQ", "slide_count": 0, "slides": []},
        "slides": [],
    }
    try:
        with patch(
            "routes.video_deepdive_routes.build_visual_deepdive_from_video",
            return_value=result,
        ) as build:
            responses = [
                client.post(
                    "/api/video-deepdives/extract",
                    json={"video_id": "dQw4w9WgXcQ"},
                    headers={"Origin": "http://localhost:3000"},
                    environ_overrides={"REMOTE_ADDR": "198.51.100.202"},
                )
                for _ in range(3)
            ]
    finally:
        limiter.reset()
        limiter.enabled = previous_enabled

    assert [response.status_code for response in responses] == [201, 201, 429]
    assert build.call_count == 2


def test_extract_preserves_usage_lock_unavailable_signal(tmp_path):
    from services.usage.usage_lock import UsageLockUnavailable

    client = _app(tmp_path)
    with patch(
        "routes.video_deepdive_routes.build_visual_deepdive_from_video",
        side_effect=UsageLockUnavailable("임대 소유권 상실"),
    ), pytest.raises(UsageLockUnavailable):
        client.post(
            "/api/video-deepdives/extract",
            json={"video_id": "dQw4w9WgXcQ"},
            headers={"Origin": "http://localhost:3000"},
            environ_overrides={"REMOTE_ADDR": "198.51.100.203"},
        )
