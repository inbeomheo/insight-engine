import json
from unittest.mock import patch

import pytest

from app import create_app
from services.content import note_index_service, note_service

_H = {"Origin": "http://localhost:3000"}


def _client():
    app = create_app({"TESTING": True})
    return app.test_client()


def _source():
    return {"type": "youtube", "url": "https://youtube.com/watch?v=abc", "title": "영상 제목"}


def _ai_response():
    return {
        "content": "```json\n"
        + json.dumps(
            {
                "key_concepts": ["개념"],
                "summary": "생성된 요약",
                "learning_points": ["생성된 요약을 복습한다."],
                "review_questions": [{"question": "무엇을 복습하나?", "answer": "생성된 요약입니다."}],
                "quotes": [{"text": "중요 문장", "ref": "00:01"}],
                "tags": ["학습"],
                "language": "ko",
            },
            ensure_ascii=False,
        )
        + "\n```"
    }


def _note(note_id, created_at):
    return {
        "id": note_id,
        "source": _source(),
        "key_concepts": ["개념"],
        "summary": "요약",
        "learning_points": ["요약을 복습한다."],
        "review_questions": [{"question": "무엇을 복습하나?", "answer": "요약입니다."}],
        "quotes": [{"text": "인용", "ref": "ref"}],
        "tags": ["학습"],
        "language": "ko",
        "created_at": created_at,
    }


def test_post_notes_generates_saves_and_returns_note(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes") as search_notes,
        patch("services.core.ai_service.create_content", return_value=_ai_response()) as create_content,
        patch("services.content.note_index_service.index_note") as index_note,
    ):
        resp = client.post(
            "/api/notes",
            json={"content": "원문 콘텐츠", "source": _source(), "language": "ko", "model": "gemini/test"},
            headers=_H,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"]
    assert data["source"] == _source()
    assert data["summary"] == "생성된 요약"
    assert data["learning_points"] == ["생성된 요약을 복습한다."]
    assert data["review_questions"][0]["question"] == "무엇을 복습하나?"
    assert (tmp_path / f"{data['id']}.json").exists()
    assert create_content.call_args.kwargs["style_id"] == "knowledge_note"
    assert create_content.call_args.kwargs["modifiers"]["language"] == "ko"
    assert "length" not in create_content.call_args.kwargs["modifiers"]
    indexed_note = index_note.call_args.args[0]
    assert indexed_note["id"] == data["id"]
    assert indexed_note["summary"] == "생성된 요약"
    search_notes.assert_not_called()


def test_post_notes_duplicate_url_returns_warning_without_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("existing", "2026-07-04T12:00:00Z"))
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes") as search_notes,
        patch("services.core.ai_service.create_content") as create_content,
        patch("services.content.note_index_service.index_note") as index_note,
    ):
        resp = client.post(
            "/api/notes",
            json={
                "content": "원문 콘텐츠",
                "source": {
                    "type": "youtube",
                    "url": "https://youtu.be/abc?utm_source=newsletter",
                    "title": "영상 제목",
                },
                "language": "ko",
                "model": "gemini/test",
            },
            headers=_H,
        )

    body = resp.get_json()
    assert resp.status_code == 409
    assert body["error"].startswith("[재학습 경고]")
    assert "기존 노트" in body["next_action"]
    assert body["duplicate_reason"] == "same_url"
    assert body["duplicate_notes"][0]["id"] == "existing"
    search_notes.assert_not_called()
    create_content.assert_not_called()
    index_note.assert_not_called()


def test_post_notes_similar_content_returns_warning_without_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    existing = _note("similar", "2026-07-04T12:00:00Z")
    existing["source"] = {"type": "article", "url": "https://example.com/old", "title": "기존 글"}
    note_service.save_note(existing)
    client = _client()
    similar = [{"id": "similar", "title": "기존 글", "score": 0.94, "snippet": "비슷한 요약"}]

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes", return_value=similar) as search_notes,
        patch("services.core.ai_service.create_content") as create_content,
        patch("services.content.note_index_service.index_note") as index_note,
    ):
        resp = client.post(
            "/api/notes",
            json={
                "content": "유사한 원문 콘텐츠",
                "source": {"type": "article", "url": "https://example.com/new", "title": "새 글"},
                "language": "ko",
                "model": "gemini/test",
            },
            headers=_H,
        )

    body = resp.get_json()
    assert resp.status_code == 409
    assert body["duplicate_reason"] == "similar_content"
    assert "기존 노트" in body["next_action"]
    assert body["duplicate_notes"] == similar
    search_notes.assert_called_once()
    create_content.assert_not_called()
    index_note.assert_not_called()


@pytest.mark.parametrize(
    ("score", "expected_status"),
    [
        (0.91, 200),
        (0.92, 200),
        (0.93, 409),
    ],
)
def test_post_notes_similarity_threshold_boundaries(tmp_path, monkeypatch, score, expected_status):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    existing = _note("similar", "2026-07-04T12:00:00Z")
    existing["source"] = {"type": "article", "url": "https://example.com/old", "title": "기존 글"}
    note_service.save_note(existing)
    client = _client()
    similar = [{"id": "similar", "title": "기존 글", "score": score, "snippet": "비슷한 요약"}]

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes", return_value=similar),
        patch("services.core.ai_service.create_content", return_value=_ai_response()) as create_content,
        patch("services.content.note_index_service.index_note") as index_note,
    ):
        resp = client.post(
            "/api/notes",
            json={
                "content": "유사한 원문 콘텐츠",
                "source": {"type": "article", "url": f"https://example.com/new-{score}", "title": "새 글"},
                "language": "ko",
                "model": "gemini/test",
            },
            headers=_H,
        )

    assert resp.status_code == expected_status
    if expected_status == 409:
        assert create_content.call_count == 0
        assert index_note.call_count == 0
    else:
        assert create_content.call_count == 1
        assert index_note.call_count == 1


def test_post_notes_similarity_lookup_failure_still_generates(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    existing = _note("existing", "2026-07-04T12:00:00Z")
    existing["source"] = {"type": "article", "url": "https://example.com/old", "title": "기존 글"}
    note_service.save_note(existing)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes", side_effect=Exception("chroma down")),
        patch("services.core.ai_service.create_content", return_value=_ai_response()) as create_content,
        patch("services.content.note_index_service.index_note") as index_note,
    ):
        resp = client.post(
            "/api/notes",
            json={
                "content": "새 원문 콘텐츠",
                "source": {"type": "article", "url": "https://example.com/new", "title": "새 글"},
                "language": "ko",
                "model": "gemini/test",
            },
            headers=_H,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"] == "생성된 요약"
    create_content.assert_called_once()
    index_note.assert_called_once()


def test_post_notes_invalid_source_keeps_korean_400_without_ai_or_chroma(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_service.list_notes") as list_notes,
        patch("services.content.note_index_service.search_notes") as search_notes,
        patch("services.core.ai_service.create_content") as create_content,
    ):
        resp = client.post(
            "/api/notes",
            json={
                "content": "원문 콘텐츠",
                "source": {"type": "pdf", "url": "https://example.com/a", "title": "문서"},
            },
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"].startswith("[노트 생성 실패]")
    list_notes.assert_not_called()
    search_notes.assert_not_called()
    create_content.assert_not_called()


def test_get_notes_lists_newest_first_and_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("old", "2026-07-03T12:00:00Z"))
    note_service.save_note(_note("new", "2026-07-04T12:00:00Z"))
    client = _client()

    related = [{"id": "old", "title": "이전 노트", "score": 0.7, "snippet": "요약"}]
    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.get_related_notes", return_value=related) as get_related,
    ):
        list_resp = client.get("/api/notes", headers=_H)
        detail_resp = client.get("/api/notes/new", headers=_H)

    assert list_resp.status_code == 200
    listed = list_resp.get_json()["notes"]
    assert [item["id"] for item in listed] == ["new", "old"]
    assert listed[0]["summary"] == "요약"
    assert listed[0]["key_concepts"] == ["개념"]
    assert listed[0]["quote_count"] == 1
    assert listed[0]["learning_point_count"] == 1
    assert detail_resp.status_code == 200
    detail = detail_resp.get_json()
    assert detail["id"] == "new"
    assert detail["related_notes"] == related
    get_related.assert_called_once()


def test_get_note_related_lookup_failure_returns_note_with_empty_related(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("n1", "2026-07-04T12:00:00Z"))
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.get_related_notes", side_effect=Exception("chroma down")),
    ):
        resp = client.get("/api/notes/n1", headers=_H)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == "n1"
    assert body["related_notes"] == []


def test_get_missing_note_returns_korean_404(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        resp = client.get("/api/notes/missing", headers=_H)

    assert resp.status_code == 404
    assert resp.get_json()["error"].startswith("[노트 조회 실패]")


def test_search_notes_returns_results(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()
    expected = [{"id": "n1", "title": "글", "score": 0.9, "snippet": "요약"}]

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes", return_value=expected) as search_notes,
    ):
        resp = client.get(
            "/api/notes/search",
            query_string={"q": "AI", "limit": "2"},
            headers=_H,
        )

    assert resp.status_code == 200
    assert resp.get_json()["notes"] == expected
    search_notes.assert_called_once_with("AI", limit=2)


def test_search_notes_empty_query_returns_korean_400(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        resp = client.get(
            "/api/notes/search",
            query_string={"q": "   "},
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"].startswith("[검색 실패]")


def test_search_notes_clamps_large_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.content.note_index_service.search_notes", return_value=[]) as search_notes,
    ):
        resp = client.get(
            "/api/notes/search",
            query_string={"q": "AI", "limit": "9999"},
            headers=_H,
        )

    assert resp.status_code == 200
    search_notes.assert_called_once_with("AI", limit=note_index_service.MAX_SEARCH_LIMIT)


def test_search_notes_long_query_returns_korean_400(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        resp = client.get(
            "/api/notes/search",
            query_string={"q": "가" * 201},
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"].startswith("[검색 실패]")


def test_search_notes_service_error_hides_internal_text(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch(
            "services.content.note_index_service.search_notes",
            side_effect=Exception("secret chroma stack detail"),
        ),
    ):
        resp = client.get(
            "/api/notes/search",
            query_string={"q": "AI"},
            headers=_H,
        )

    body = resp.get_json()
    assert resp.status_code == 500
    assert body["error"].startswith("[검색 실패]")
    assert "secret chroma stack detail" not in body["error"]


def test_get_note_path_traversal_attempt_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        slash_resp = client.get("/api/notes/..%2fx", headers=_H)
        backslash_resp = client.get("/api/notes/..%5Cx", headers=_H)

    assert slash_resp.status_code == 404
    assert backslash_resp.status_code == 404


def test_post_notes_invalid_body_returns_korean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        resp = client.post("/api/notes", json={"source": _source()}, headers=_H)

    assert resp.status_code == 400
    assert resp.get_json()["error"].startswith("[노트 생성 실패]")


def test_post_notes_bad_ai_response_returns_korean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.core.ai_service.create_content", return_value={"content": "not json"}),
    ):
        resp = client.post(
            "/api/notes",
            json={"content": "원문 콘텐츠", "source": _source()},
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"].startswith("[노트 생성 실패]")


def test_post_notes_index_failure_still_returns_note(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.core.ai_service.create_content", return_value=_ai_response()),
        patch("services.content.note_index_service.index_note", side_effect=Exception("boom")),
    ):
        resp = client.post(
            "/api/notes",
            json={"content": "원문 콘텐츠", "source": _source()},
            headers=_H,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"] == "생성된 요약"
    assert (tmp_path / f"{data['id']}.json").exists()


def test_post_notes_provider_prefixed_exception_uses_handle_error(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False),
        patch("services.core.ai_service.create_content", side_effect=Exception("[사용량 초과] quota")),
    ):
        resp = client.post(
            "/api/notes",
            json={"content": "원문 콘텐츠", "source": _source()},
            headers=_H,
        )

    assert resp.status_code == 429
    assert resp.get_json()["error"].startswith("[사용량 초과]")
