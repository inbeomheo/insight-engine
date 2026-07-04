import json
from unittest.mock import patch

from app import create_app
from services.content import note_service

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
        patch("services.core.ai_service.create_content", return_value=_ai_response()) as create_content,
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
    assert (tmp_path / f"{data['id']}.json").exists()
    assert create_content.call_args.kwargs["style_id"] == "knowledge_note"
    assert create_content.call_args.kwargs["modifiers"]["language"] == "ko"
    assert "length" not in create_content.call_args.kwargs["modifiers"]


def test_get_notes_lists_newest_first_and_detail(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("old", "2026-07-03T12:00:00Z"))
    note_service.save_note(_note("new", "2026-07-04T12:00:00Z"))
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        list_resp = client.get("/api/notes", headers=_H)
        detail_resp = client.get("/api/notes/new", headers=_H)

    assert list_resp.status_code == 200
    assert [item["id"] for item in list_resp.get_json()["notes"]] == ["new", "old"]
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["id"] == "new"


def test_get_missing_note_returns_korean_404(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    client = _client()

    with patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=False):
        resp = client.get("/api/notes/missing", headers=_H)

    assert resp.status_code == 404
    assert resp.get_json()["error"].startswith("[노트 조회 실패]")


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
