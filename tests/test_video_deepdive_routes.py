def _app(tmp_path):
    import app as flask_app

    app = flask_app.create_app({"TESTING": True, "VIDEO_DEEPDIVE_DIR": str(tmp_path)})
    return app.test_client()


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
