"""Knowledge note ChromaDB indexing/search service."""
from __future__ import annotations

import re
from typing import Any

from config import CHROMA_DB_PATH
from services.core.logging_config import get_logger
from services.rag.chroma_client_factory import get_chroma_client

NOTES_COLLECTION_NAME = "knowledge_notes"
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20
DEFAULT_RELATED_LIMIT = 3
MAX_RELATED_LIMIT = MAX_SEARCH_LIMIT - 1
SNIPPET_MAX_CHARS = 180

logger = get_logger(__name__)


def index_note(note: dict[str, Any]) -> None:
    """Upsert one knowledge note into the dedicated notes collection."""
    note_id = _required_note_id(note)
    document = _build_searchable_text(note)
    if not document:
        raise ValueError("[노트 인덱싱 실패] 검색 가능한 내용이 없습니다.")

    _get_collection().upsert(
        ids=[note_id],
        documents=[document],
        metadatas=[_build_metadata(note)],
    )
    logger.info("Knowledge note indexed: %s", note_id)


def remove_note(note_id: str) -> None:
    """Remove a note from the notes collection."""
    note_id = str(note_id or "").strip()
    if not note_id:
        raise ValueError("[노트 인덱싱 실패] 노트 ID가 필요합니다.")
    _get_collection().delete(ids=[note_id])


def search_notes(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[dict[str, Any]]:
    """Search similar notes by ChromaDB text query."""
    query = str(query or "").strip()
    if not query:
        return []

    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    n_results = min(_normalize_limit(limit), count)
    results = collection.query(query_texts=[query], n_results=n_results)
    return _map_results(results)


def get_related_notes(
    note: dict[str, Any],
    limit: int = DEFAULT_RELATED_LIMIT,
) -> list[dict[str, Any]]:
    """Return similar notes, excluding the note itself."""
    note_id = _required_note_id(note)
    query = _build_searchable_text(note)
    if not query:
        return []

    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    normalized_limit = _normalize_related_limit(limit)
    n_results = min(normalized_limit + 1, count, MAX_SEARCH_LIMIT)
    results = collection.query(query_texts=[query], n_results=n_results)
    related = [
        result
        for result in _map_results(results)
        if result.get("id") and result.get("id") != note_id
    ]
    return related[:normalized_limit]


def _get_collection():
    client = get_chroma_client(CHROMA_DB_PATH)
    # hnsw:space is immutable after collection creation; notes rely on cosine distances for scoring.
    return client.get_or_create_collection(
        name=NOTES_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _required_note_id(note: dict[str, Any]) -> str:
    if not isinstance(note, dict):
        raise ValueError("[노트 인덱싱 실패] 노트 객체가 필요합니다.")
    note_id = str(note.get("id", "")).strip()
    if not note_id:
        raise ValueError("[노트 인덱싱 실패] 노트 ID가 필요합니다.")
    return note_id


def _build_searchable_text(note: dict[str, Any]) -> str:
    concepts = _str_list(note.get("key_concepts"))
    tags = _str_list(note.get("tags"))
    summary = str(note.get("summary", "")).strip()

    parts: list[str] = []
    if concepts:
        parts.append("핵심 개념: " + ", ".join(concepts))
    if summary:
        parts.append("요약: " + summary)
    if tags:
        parts.append("태그: " + ", ".join(tags))
    return "\n".join(parts).strip()


def _build_metadata(note: dict[str, Any]) -> dict[str, str]:
    source = note.get("source") if isinstance(note.get("source"), dict) else {}
    return {
        "title": str(source.get("title", "")).strip(),
        "source_url": str(source.get("url", "")).strip(),
        "created_at": str(note.get("created_at", "")).strip(),
    }


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = DEFAULT_SEARCH_LIMIT
    return max(1, min(value, MAX_SEARCH_LIMIT))


def _normalize_related_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = DEFAULT_RELATED_LIMIT
    return max(1, min(value, MAX_RELATED_LIMIT))


def _map_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    ids = _first_result_list(results, "ids")
    documents = _first_result_list(results, "documents")
    metadatas = _first_result_list(results, "metadatas")
    distances = _first_result_list(results, "distances")

    mapped: list[dict[str, Any]] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        note_id = str(ids[idx]) if idx < len(ids) else ""
        distance = distances[idx] if idx < len(distances) else None
        mapped.append({
            "id": note_id,
            "title": str(metadata.get("title", "")),
            "score": _score_from_distance(distance),
            "snippet": _snippet(document),
        })
    return mapped


def _first_result_list(results: dict[str, Any], key: str) -> list[Any]:
    value = results.get(key) if isinstance(results, dict) else None
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    return []


def _score_from_distance(distance: Any) -> float:
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, 1.0 - value)), 3)


def _snippet(text: Any) -> str:
    snippet = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(snippet) <= SNIPPET_MAX_CHARS:
        return snippet
    return snippet[: SNIPPET_MAX_CHARS - 1] + "…"
