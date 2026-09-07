from unittest.mock import patch

import pytest
from flask import g

from app import create_app
from services.content import note_graph_service, note_index_service, note_service


def _note(note_id: str, created_at: str) -> dict:
    return {
        "id": note_id,
        "title": f"Note {note_id}",
        "key_concepts": [f"concept-{note_id}"],
        "summary": f"summary {note_id}",
        "tags": ["test"],
        "quotes": [],
        "language": "ko",
        "created_at": created_at,
        "source": {"title": f"Note {note_id}", "type": "text", "url": ""},
    }


def test_build_note_graph_is_bounded_deterministic_and_removes_invalid_edges():
    notes = [
        _note("a", "2026-09-03T00:00:00+00:00"),
        _note("b", "2026-09-02T00:00:00+00:00"),
        _note("c", "2026-09-01T00:00:00+00:00"),
        _note("d", "2026-08-31T00:00:00+00:00"),
    ]
    related = {
        "a": [
            {"id": "a", "score": 0.99},
            {"id": "b", "score": 0.91},
            {"id": "b", "score": 0.87},
            {"id": "d", "score": 0.95},
            {"id": "c", "score": 0.19},
        ],
        "b": [{"id": "a", "score": 0.82}],
        "c": [{"id": "b", "score": 0.76}],
    }

    graph = note_graph_service.build_note_graph(
        owner_id=None,
        notes=notes,
        node_limit=3,
        edge_limit=2,
        related_limit=8,
        min_score=0.2,
        related_lookup=lambda note, limit: related.get(note["id"], [])[:limit],
    )

    assert [node["id"] for node in graph["nodes"]] == ["a", "b", "c"]
    assert graph["edges"] == [
        {"source": "a", "target": "b", "score": 0.91},
        {"source": "b", "target": "a", "score": 0.82},
    ]
    assert graph["meta"]["node_count"] == 3
    assert graph["meta"]["edge_count"] == 2


def test_build_note_graph_clamps_query_controls():
    graph = note_graph_service.build_note_graph(
        owner_id=None,
        notes=[_note("a", "2026-09-01T00:00:00+00:00")],
        node_limit="999",
        edge_limit="-1",
        related_limit="999",
        min_score="2",
        related_lookup=lambda note, limit: [],
    )

    assert graph["meta"]["node_limit"] == note_graph_service.MAX_GRAPH_NODE_LIMIT
    assert graph["meta"]["edge_limit"] == 1
    assert graph["meta"]["related_limit"] == note_graph_service.MAX_GRAPH_RELATED_LIMIT
    assert graph["meta"]["min_score"] == 1.0


def test_get_note_backlinks_reverses_directed_top_k_and_keeps_target_in_scan():
    notes = [
        _note("newest", "2026-09-04T00:00:00+00:00"),
        _note("source-a", "2026-09-03T00:00:00+00:00"),
        _note("source-b", "2026-09-02T00:00:00+00:00"),
        _note("target", "2026-08-01T00:00:00+00:00"),
    ]
    related = {
        "newest": [{"id": "source-a", "score": 0.7}],
        "source-a": [{"id": "target", "score": 0.84}],
        "source-b": [
            {"id": "target", "score": 0.92},
            {"id": "target", "score": 0.88},
        ],
        "target": [{"id": "source-b", "score": 0.95}],
    }

    backlinks = note_graph_service.get_note_backlinks(
        "target",
        owner_id=None,
        notes=notes,
        scan_limit=4,
        related_limit=3,
        result_limit=10,
        min_score=0.2,
        related_lookup=lambda note, limit: related.get(note["id"], [])[:limit],
    )

    assert backlinks == [
        {"id": "source-b", "title": "Note source-b", "score": 0.92},
        {"id": "source-a", "title": "Note source-a", "score": 0.84},
    ]


def test_relationship_lookup_failure_degrades_to_empty_edges():
    graph = note_graph_service.build_note_graph(
        owner_id=None,
        notes=[_note("a", "2026-09-01T00:00:00+00:00")],
        related_lookup=lambda note, limit: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    assert graph["edges"] == []
    assert graph["meta"]["edge_count"] == 0


@pytest.mark.parametrize("owner_id", ["user-a", "user-b"])
def test_graph_and_backlinks_use_owner_scoped_real_files(tmp_path, monkeypatch, owner_id):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    for owner in ("user-a", "user-b", None):
        for note_id in ("target", "source"):
            note = _note(note_id, "2026-09-01T00:00:00+00:00")
            note["source"]["title"] = f"{owner} {note_id}"
            note_service.save_note(note, owner_id=owner)

    def related(note, *, owner_id, limit):
        assert note["title"].startswith(owner_id)
        return [{"id": "target" if note["id"] == "source" else "source", "score": 0.9}]

    with patch.object(note_index_service, "get_related_notes", side_effect=related) as lookup:
        graph = note_graph_service.build_note_graph(owner_id=owner_id)
        backlinks = note_graph_service.get_note_backlinks("target", owner_id=owner_id)

    assert {node["title"] for node in graph["nodes"]} == {
        f"{owner_id} target", f"{owner_id} source",
    }
    assert len(graph["edges"]) == 2
    assert backlinks == [{"id": "source", "title": f"{owner_id} source", "score": 0.9}]
    assert all(call.kwargs["owner_id"] == owner_id for call in lookup.call_args_list)


def test_authenticated_graph_routes_isolate_users_and_hide_foreign_targets(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    for owner in ("user-a", "user-b"):
        for kind in ("target", "source"):
            note_service.save_note(
                _note(f"{owner}-{kind}", "2026-09-01T00:00:00+00:00"), owner_id=owner,
            )
    client = create_app({"TESTING": True}).test_client()

    def validate_token(token):
        if token not in ("user-a", "user-b"):
            return {"valid": False, "error": "invalid", "code": "TOKEN_INVALID"}
        g.user_id = token
        g.access_token = token
        return {"valid": True, "error": None, "code": None}

    def related(note, *, owner_id, limit):
        assert note["id"].startswith(owner_id)
        return [{"id": f"{owner_id}-target", "score": 0.9}]

    with (
        patch("src.contexts.identity.interface.auth_decorators.is_supabase_enabled", return_value=True),
        patch("src.contexts.identity.interface.auth_decorators._validate_token", side_effect=validate_token),
        patch.object(note_index_service, "get_related_notes", side_effect=related) as lookup,
    ):
        assert client.get("/api/notes/graph").status_code == 401
        assert client.get("/api/notes/user-a-target/backlinks").status_code == 401
        for owner in ("user-a", "user-b"):
            headers = {"Authorization": f"Bearer {owner}"}
            graph = client.get("/api/notes/graph", headers=headers)
            backlinks = client.get(f"/api/notes/{owner}-target/backlinks", headers=headers)
            other = "user-b" if owner == "user-a" else "user-a"
            foreign = client.get(f"/api/notes/{other}-target/backlinks", headers=headers)
            assert graph.status_code == 200
            assert {node["id"] for node in graph.json["nodes"]} == {
                f"{owner}-target", f"{owner}-source",
            }
            assert graph.json["edges"] == [{
                "source": f"{owner}-source", "target": f"{owner}-target", "score": 0.9,
            }]
            assert backlinks.status_code == 200
            assert [note["id"] for note in backlinks.json["notes"]] == [f"{owner}-source"]
            assert foreign.status_code == 404
        assert lookup.call_count == 6


def test_backlinks_for_foreign_target_do_not_query_index(tmp_path, monkeypatch):
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path)
    note_service.save_note(_note("target", "2026-09-01T00:00:00+00:00"), owner_id="user-a")
    note_service.save_note(_note("source", "2026-09-01T00:00:00+00:00"), owner_id="user-b")
    with patch.object(note_index_service, "get_related_notes") as lookup:
        assert note_graph_service.get_note_backlinks("target", owner_id="user-b") == []
    lookup.assert_not_called()
