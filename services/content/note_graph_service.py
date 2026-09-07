"""Bounded relationship graph helpers for knowledge notes."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

from services.content import note_index_service, note_service
from services.core.logging_config import get_logger

DEFAULT_GRAPH_NODE_LIMIT = 24
MAX_GRAPH_NODE_LIMIT = 40
DEFAULT_GRAPH_EDGE_LIMIT = 80
MAX_GRAPH_EDGE_LIMIT = 160
DEFAULT_GRAPH_RELATED_LIMIT = 3
MAX_GRAPH_RELATED_LIMIT = 8
DEFAULT_GRAPH_MIN_SCORE = 0.2
DEFAULT_BACKLINK_LIMIT = 8
MAX_BACKLINK_LIMIT = 20

logger = get_logger(__name__)

RelatedLookup = Callable[[dict[str, Any], int], list[dict[str, Any]]]


def build_note_graph(
    *,
    owner_id: str | None,
    notes: Iterable[dict[str, Any]] | None = None,
    node_limit: int = DEFAULT_GRAPH_NODE_LIMIT,
    edge_limit: int = DEFAULT_GRAPH_EDGE_LIMIT,
    related_limit: int = DEFAULT_GRAPH_RELATED_LIMIT,
    min_score: float = DEFAULT_GRAPH_MIN_SCORE,
    related_lookup: RelatedLookup | None = None,
) -> dict[str, Any]:
    """Build a deterministic, bounded directed similarity graph."""
    node_limit = _bounded_int(node_limit, DEFAULT_GRAPH_NODE_LIMIT, 1, MAX_GRAPH_NODE_LIMIT)
    edge_limit = _bounded_int(edge_limit, DEFAULT_GRAPH_EDGE_LIMIT, 1, MAX_GRAPH_EDGE_LIMIT)
    related_limit = _bounded_int(
        related_limit,
        DEFAULT_GRAPH_RELATED_LIMIT,
        1,
        MAX_GRAPH_RELATED_LIMIT,
    )
    min_score = _bounded_score(min_score, DEFAULT_GRAPH_MIN_SCORE)
    source_notes = list(note_service.list_notes(owner_id=owner_id) if notes is None else notes)
    selected = _select_notes(source_notes, node_limit)
    nodes = [_graph_node(note) for note in selected]
    allowed_ids = {node["id"] for node in nodes}
    lookup = related_lookup or partial(_related_lookup, owner_id=owner_id)

    edge_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for note in selected:
        source_id = _note_id(note)
        if not source_id:
            continue
        for related in _safe_related(lookup, note, related_limit):
            target_id = _note_id(related)
            if not target_id or target_id == source_id or target_id not in allowed_ids:
                continue
            score = _score(related.get("score"))
            if score < min_score:
                continue
            key = (source_id, target_id)
            current = edge_by_key.get(key)
            if current is None or score > current["score"]:
                edge_by_key[key] = {
                    "source": source_id,
                    "target": target_id,
                    "score": score,
                }

    edges = sorted(
        edge_by_key.values(),
        key=lambda edge: (-edge["score"], edge["source"], edge["target"]),
    )[:edge_limit]
    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "node_limit": node_limit,
            "edge_limit": edge_limit,
            "related_limit": related_limit,
            "min_score": min_score,
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }


def get_note_backlinks(
    note_id: str,
    *,
    owner_id: str | None,
    notes: Iterable[dict[str, Any]] | None = None,
    scan_limit: int = DEFAULT_GRAPH_NODE_LIMIT,
    related_limit: int = DEFAULT_GRAPH_RELATED_LIMIT,
    result_limit: int = DEFAULT_BACKLINK_LIMIT,
    min_score: float = DEFAULT_GRAPH_MIN_SCORE,
    related_lookup: RelatedLookup | None = None,
) -> list[dict[str, Any]]:
    """Return notes whose bounded top-K similarity results point to ``note_id``."""
    target_id = str(note_id or "").strip()
    if not target_id:
        return []

    scan_limit = _bounded_int(scan_limit, DEFAULT_GRAPH_NODE_LIMIT, 1, MAX_GRAPH_NODE_LIMIT)
    related_limit = _bounded_int(
        related_limit,
        DEFAULT_GRAPH_RELATED_LIMIT,
        1,
        MAX_GRAPH_RELATED_LIMIT,
    )
    result_limit = _bounded_int(result_limit, DEFAULT_BACKLINK_LIMIT, 1, MAX_BACKLINK_LIMIT)
    min_score = _bounded_score(min_score, DEFAULT_GRAPH_MIN_SCORE)
    source_notes = list(note_service.list_notes(owner_id=owner_id) if notes is None else notes)
    if not any(_note_id(note) == target_id for note in source_notes):
        return []
    selected = _select_notes(source_notes, scan_limit, include_id=target_id)
    lookup = related_lookup or partial(_related_lookup, owner_id=owner_id)

    backlinks: dict[str, dict[str, Any]] = {}
    for note in selected:
        source_id = _note_id(note)
        if not source_id or source_id == target_id:
            continue
        for related in _safe_related(lookup, note, related_limit):
            if _note_id(related) != target_id:
                continue
            score = _score(related.get("score"))
            if score < min_score:
                continue
            candidate = {
                "id": source_id,
                "title": _note_title(note),
                "score": score,
            }
            current = backlinks.get(source_id)
            if current is None or score > current["score"]:
                backlinks[source_id] = candidate

    return sorted(
        backlinks.values(),
        key=lambda item: (-item["score"], item["title"], item["id"]),
    )[:result_limit]


def _select_notes(
    notes: Iterable[dict[str, Any]],
    limit: int,
    *,
    include_id: str | None = None,
) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for note in notes:
        if not isinstance(note, dict):
            continue
        note_id = _note_id(note)
        if note_id and note_id not in deduped:
            deduped[note_id] = note

    ordered = sorted(
        deduped.values(),
        key=lambda note: (str(note.get("created_at", "")), _note_id(note)),
        reverse=True,
    )
    selected = ordered[:limit]
    if include_id and include_id in deduped and all(_note_id(note) != include_id for note in selected):
        if limit <= 1:
            return [deduped[include_id]]
        selected = [*selected[:-1], deduped[include_id]]
    return sorted(
        selected,
        key=lambda note: (str(note.get("created_at", "")), _note_id(note)),
        reverse=True,
    )


def _graph_node(note: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _note_id(note),
        "title": _note_title(note),
        "key_concepts": _string_list(note.get("key_concepts"))[:6],
        "created_at": str(note.get("created_at", "")),
    }


def _related_lookup(
    note: dict[str, Any], limit: int, *, owner_id: str | None,
) -> list[dict[str, Any]]:
    return note_index_service.get_related_notes(note, owner_id=owner_id, limit=limit)


def _safe_related(
    lookup: RelatedLookup,
    note: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    try:
        result = lookup(note, limit)
        return result if isinstance(result, list) else []
    except Exception as exc:
        logger.warning("Knowledge note relationship lookup failed (ignored): %s", exc)
        return []


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _bounded_score(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return round(max(0.0, min(parsed, 1.0)), 3)


def _score(value: Any) -> float:
    return _bounded_score(value, 0.0)


def _note_id(note: dict[str, Any]) -> str:
    return str(note.get("id", "")).strip()


def _note_title(note: dict[str, Any]) -> str:
    title = str(note.get("title", "")).strip()
    if title:
        return title
    source = note.get("source") if isinstance(note.get("source"), dict) else {}
    return str(source.get("title", "")).strip() or _note_id(note)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
