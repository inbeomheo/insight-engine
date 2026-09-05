from services.content import note_graph_service


def _note(note_id: str, created_at: str) -> dict:
    return {
        "id": note_id,
        "title": f"Note {note_id}",
        "key_concepts": [f"concept-{note_id}"],
        "summary": f"summary {note_id}",
        "tags": ["test"],
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
        notes=[_note("a", "2026-09-01T00:00:00+00:00")],
        related_lookup=lambda note, limit: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    assert graph["edges"] == []
    assert graph["meta"]["edge_count"] == 0
