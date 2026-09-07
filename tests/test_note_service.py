import json

import pytest

from services.content import note_service


def _note(note_id="note-1", created_at="2026-07-04T12:00:00Z"):
    return {
        "id": note_id,
        "source": {"type": "article", "url": "https://example.com/a", "title": "테스트 글"},
        "key_concepts": ["개념 A", "개념 B"],
        "summary": "요약입니다.",
        "learning_points": ["개념 A를 적용한다."],
        "review_questions": [{"question": "개념 A는 무엇인가?", "answer": "테스트 개념입니다."}],
        "quotes": [{"text": "원문 인용", "ref": "p1"}],
        "tags": ["학습", "테스트"],
        "language": "ko",
        "created_at": created_at,
    }


def test_validate_note_accepts_valid_note():
    valid, errors = note_service.validate_note(_note())

    assert valid is True
    assert errors == []


def test_validate_note_accepts_text_source_without_url():
    note = _note()
    note["source"] = {"type": "text", "url": "", "title": "직접 입력 텍스트"}

    valid, errors = note_service.validate_note(note)

    assert valid is True
    assert errors == []


def test_validate_note_rejects_invalid_cases():
    note = _note()
    note["source"]["type"] = "podcast"
    note["quotes"] = [{"text": ""}]
    note["created_at"] = "not-a-date"

    valid, errors = note_service.validate_note(note)

    assert valid is False
    assert any("source.type" in error for error in errors)
    assert any("quote.text" in error for error in errors)
    assert any("ISO8601" in error for error in errors)


def test_find_notes_by_source_url_ignores_text_source_without_url(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note("text-note")
    note["source"] = {"type": "text", "url": "", "title": "직접 입력 텍스트"}
    note_service.save_note(note, owner_id=None)

    duplicates = note_service.find_notes_by_source_url(
        {"type": "text", "url": "", "title": "새 텍스트"},
        owner_id=None,
    )

    assert duplicates == []


def test_save_load_round_trip_utf8(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note()

    note_service.save_note(note, owner_id=None)

    assert note_service.load_note("note-1", owner_id=None) == note
    path = tmp_path / "scopes" / "anonymous" / "note-1.json"
    raw = path.read_text(encoding="utf-8")
    assert "요약입니다." in raw
    assert "\\uc694" not in raw


def test_save_note_invalid_id_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note("../x")

    with pytest.raises(ValueError):
        note_service.save_note(note, owner_id=None)


def test_list_notes_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("old", "2026-07-03T12:00:00Z"), owner_id=None)
    note_service.save_note(_note("new", "2026-07-04T12:00:00Z"), owner_id=None)

    notes = note_service.list_notes(owner_id=None)

    assert [item["id"] for item in notes] == ["new", "old"]
    assert notes[0] == {
        "id": "new",
        "title": "테스트 글",
        "tags": ["학습", "테스트"],
        "key_concepts": ["개념 A", "개념 B"],
        "summary": "요약입니다.",
        "quote_count": 1,
        "learning_point_count": 1,
        "review_question_count": 1,
        "created_at": "2026-07-04T12:00:00Z",
        "source": {"type": "article", "url": "https://example.com/a", "title": "테스트 글"},
    }


def test_user_scoped_storage_isolated_and_path_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_a = _note("shared-id")
    note_b = _note("shared-id")
    note_a["summary"] = "사용자 A 요약"
    note_b["summary"] = "사용자 B 요약"

    note_service.save_note(note_a, owner_id="user-a")
    note_service.save_note(note_b, owner_id="../../user-b")

    assert note_service.load_note("shared-id", owner_id="user-a") == note_a
    assert note_service.load_note("shared-id", owner_id="../../user-b") == note_b
    assert note_service.load_note("shared-id", owner_id="user-c") is None
    assert [item["summary"] for item in note_service.list_notes(owner_id="user-a")] == [
        "사용자 A 요약"
    ]
    assert not (tmp_path.parent / "user-b").exists()
    assert all(path.parent.parent == tmp_path / "scopes" for path in (tmp_path / "scopes").glob("*/*.json"))


def test_authenticated_user_cannot_read_legacy_unowned_note(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    legacy = _note("legacy")
    (tmp_path / "legacy.json").write_text(
        json.dumps(legacy, ensure_ascii=False),
        encoding="utf-8",
    )

    assert note_service.load_note("legacy", owner_id=None) == legacy
    assert note_service.load_note("legacy", owner_id="user-a") is None
    assert note_service.list_notes(owner_id="user-a") == []


def test_owner_scope_metadata_mismatch_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note("tampered")
    note_service.save_note(note, owner_id="user-a")
    path = next((tmp_path / "scopes").glob("*/tampered.json"))
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored[note_service.OWNER_SCOPE_FIELD] = note_service.owner_scope_for("user-b")
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")

    assert note_service.load_note("tampered", owner_id="user-a") is None


def test_parse_note_response_prefers_fenced_json_and_tolerates_trailing_commas():
    payload = {
        "key_concepts": ["AI"],
        "summary": "핵심 요약",
        "learning_points": ["AI의 쓰임을 설명한다"],
        "review_questions": [{"question": "AI란?", "answer": "인공지능입니다."}],
        "quotes": [{"text": "인용", "ref": "00:01"}],
        "tags": ["ai"],
        "language": "ko",
    }
    raw_json = json.dumps(payload, ensure_ascii=False, indent=2).replace('"ko"\n}', '"ko",\n}')
    parsed = note_service.parse_note_response(f"설명\n```json\n{raw_json}\n```\n끝")

    assert parsed["summary"] == "핵심 요약"
    assert parsed["key_concepts"] == ["AI"]
    assert parsed["learning_points"] == ["AI의 쓰임을 설명한다"]
    assert parsed["review_questions"] == [{"question": "AI란?", "answer": "인공지능입니다."}]
    assert parsed["quotes"] == [{"text": "인용", "ref": "00:01"}]
