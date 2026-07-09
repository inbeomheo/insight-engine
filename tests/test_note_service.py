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


def test_save_load_round_trip_utf8(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note()

    note_service.save_note(note)

    assert note_service.load_note("note-1") == note
    raw = (tmp_path / "note-1.json").read_text(encoding="utf-8")
    assert "요약입니다." in raw
    assert "\\uc694" not in raw


def test_save_note_invalid_id_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note = _note("../x")

    with pytest.raises(ValueError):
        note_service.save_note(note)


def test_list_notes_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("old", "2026-07-03T12:00:00Z"))
    note_service.save_note(_note("new", "2026-07-04T12:00:00Z"))

    notes = note_service.list_notes()

    assert [item["id"] for item in notes] == ["new", "old"]
    assert notes[0] == {
        "id": "new",
        "title": "테스트 글",
        "tags": ["학습", "테스트"],
        "key_concepts": ["개념 A", "개념 B"],
        "summary": "요약입니다.",
        "quote_count": 1,
        "learning_point_count": 1,
        "created_at": "2026-07-04T12:00:00Z",
        "source": {"type": "article", "url": "https://example.com/a", "title": "테스트 글"},
    }


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
