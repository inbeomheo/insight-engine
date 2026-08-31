"""노트 사용자 스코프 / 레거시 격리."""
import json

from services.content import note_service


def _note(note_id, owner=None):
    note = {
        "id": note_id,
        "source": {"type": "article", "url": f"https://example.com/{note_id}", "title": note_id},
        "key_concepts": ["개념"],
        "summary": "요약",
        "quotes": [{"text": "인용", "ref": "r"}],
        "tags": ["t"],
        "language": "ko",
        "created_at": "2026-08-31T00:00:00Z",
    }
    if owner:
        note["owner_id"] = owner
    return note


def test_notes_are_user_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("a"), owner_id="user-a")
    note_service.save_note(_note("b"), owner_id="user-b")

    listed_a = note_service.list_notes(owner_id="user-a")
    listed_b = note_service.list_notes(owner_id="user-b")
    assert [item["id"] for item in listed_a] == ["a"]
    assert [item["id"] for item in listed_b] == ["b"]
    assert note_service.load_note("a", owner_id="user-b") is None
    assert note_service.load_note("a", owner_id="user-a")["id"] == "a"
    assert (tmp_path / "users" / "user-a" / "a.json").exists()


def test_legacy_notes_stay_on_disk_and_need_explicit_path(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    legacy = _note("old")
    (tmp_path / "old.json").write_text(json.dumps(legacy), encoding="utf-8")

    assert note_service.list_notes(owner_id="user-a") == []
    assert note_service.load_note("old", owner_id="user-a") is None
    assert note_service.load_note("old", owner_id="user-a", include_legacy=True)["id"] == "old"
    listed_legacy = note_service.list_notes(owner_id="user-a", include_legacy=True)
    assert listed_legacy[0]["id"] == "old"
    assert listed_legacy[0]["legacy"] is True
    assert (tmp_path / "old.json").exists()


def test_duplicate_search_does_not_cross_users(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("shared-src"), owner_id="user-a")
    dupes = note_service.find_notes_by_source_url(
        {"type": "article", "url": "https://example.com/shared-src", "title": "x"},
        owner_id="user-b",
    )
    assert dupes == []
