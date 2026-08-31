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
_QUERY_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

logger = get_logger(__name__)


def index_note(note: dict[str, Any], owner_id: str | None = None) -> None:
    """Upsert one knowledge note into the dedicated notes collection."""
    note_id = _required_note_id(note)
    document = _build_searchable_text(note)
    if not document:
        raise ValueError("[노트 인덱싱 실패] 검색 가능한 내용이 없습니다.")

    _get_collection().upsert(
        ids=[note_id],
        documents=[document],
        metadatas=[_build_metadata(note, owner_id=owner_id)],
    )
    logger.info("Knowledge note indexed: %s", note_id)


def remove_note(note_id: str) -> None:
    """Remove a note from the notes collection."""
    note_id = str(note_id or "").strip()
    if not note_id:
        raise ValueError("[노트 인덱싱 실패] 노트 ID가 필요합니다.")
    _get_collection().delete(ids=[note_id])


def search_notes(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    owner_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search similar notes by ChromaDB text query."""
    query = _normalize_whitespace(query)
    if not query:
        return []

    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    n_results = min(_normalize_limit(limit), count)
    query_kwargs: dict[str, Any] = {"query_texts": [query], "n_results": n_results}
    owner_filter = _owner_where(owner_id)
    if owner_filter:
        query_kwargs["where"] = owner_filter
    results = collection.query(**query_kwargs)
    return _map_results(results, query=query)


def get_related_notes(
    note: dict[str, Any],
    limit: int = DEFAULT_RELATED_LIMIT,
    owner_id: str | None = None,
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
    query_kwargs: dict[str, Any] = {"query_texts": [query], "n_results": n_results}
    owner_filter = _owner_where(owner_id or (note.get("owner_id") if isinstance(note, dict) else None))
    if owner_filter:
        query_kwargs["where"] = owner_filter
    results = collection.query(**query_kwargs)
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
    learning_points = _str_list(note.get("learning_points"))
    review_questions = _review_question_texts(note.get("review_questions"))
    quotes = _quote_texts(note.get("quotes"))
    summary = str(note.get("summary", "")).strip()

    parts: list[str] = []
    if concepts:
        parts.append("핵심 개념: " + ", ".join(concepts))
    if summary:
        parts.append("요약: " + summary)
    if learning_points:
        parts.append("학습 포인트: " + " ".join(learning_points))
    if review_questions:
        parts.append("복습 질문: " + " ".join(review_questions))
    if quotes:
        parts.append("근거 인용: " + " ".join(quotes))
    if tags:
        parts.append("태그: " + ", ".join(tags))
    return "\n".join(parts).strip()


def _build_metadata(note: dict[str, Any], owner_id: str | None = None) -> dict[str, str]:
    source = note.get("source") if isinstance(note.get("source"), dict) else {}
    owner = str(owner_id or note.get("owner_id") or "_local").strip() or "_local"
    return {
        "title": str(source.get("title", "")).strip(),
        "source_url": str(source.get("url", "")).strip(),
        "created_at": str(note.get("created_at", "")).strip(),
        "owner_id": owner,
    }


def _owner_where(owner_id: str | None) -> dict[str, str] | None:
    owner = str(owner_id or "").strip()
    if not owner:
        return None
    return {"owner_id": owner}


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _review_question_texts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    texts: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if question or answer:
            texts.append(f"{question} {answer}".strip())
    return texts


def _quote_texts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    texts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            ref = str(item.get("ref", "")).strip()
            if text:
                texts.append(f"{text} {ref}".strip())
        elif str(item).strip():
            texts.append(str(item).strip())
    return texts


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


def _map_results(
    results: dict[str, Any] | None,
    *,
    query: Any = None,
) -> list[dict[str, Any]]:
    ids = _first_result_list(results, "ids")
    documents = _first_result_list(results, "documents")
    metadatas = _first_result_list(results, "metadatas")
    distances = _first_result_list(results, "distances")

    mapped: list[dict[str, Any]] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        note_id = str(ids[idx]) if idx < len(ids) else ""
        distance = distances[idx] if idx < len(distances) else None
        snippet, highlight_ranges = _snippet_with_highlights(document, query)
        mapped.append({
            "id": note_id,
            "title": str(metadata.get("title", "")),
            "score": _score_from_distance(distance),
            "snippet": snippet,
            "highlight_ranges": highlight_ranges,
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


def _normalize_whitespace(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _query_candidates(query: Any) -> list[str]:
    normalized = _normalize_whitespace(query)
    if not normalized or not any(char.isalpha() for char in normalized):
        return []

    candidates: list[str] = []

    def add(candidate: str) -> None:
        is_duplicate = any(
            re.fullmatch(re.escape(existing), candidate, flags=re.IGNORECASE)
            for existing in candidates
        )
        if (
            not candidate
            or is_duplicate
            or not any(char.isalpha() for char in candidate)
        ):
            return
        candidates.append(candidate)

    add(normalized)
    tokens = [
        token
        for token in _QUERY_TOKEN_PATTERN.findall(normalized)
        if any(char.isalpha() for char in token)
    ]
    for token in sorted(tokens, key=lambda value: -len(value)):
        add(token)
    return candidates


def _find_query_span(text: str, query: Any) -> tuple[int, int] | None:
    for candidate in _query_candidates(query):
        match = re.search(re.escape(candidate), text, flags=re.IGNORECASE)
        if match:
            return match.span()
    return None


def _leading_snippet(text: str) -> str:
    if len(text) <= SNIPPET_MAX_CHARS:
        return text
    return text[: SNIPPET_MAX_CHARS - 1] + "…"


def _context_snippet_details(
    text: str,
    start: int,
    end: int,
) -> tuple[str, int, int, int]:
    if len(text) <= SNIPPET_MAX_CHARS:
        return text, 0, len(text), 0

    reserve = int(start > 0) + int(end < len(text))
    available = max(1, SNIPPET_MAX_CHARS - reserve)
    match_length = end - start

    if match_length >= available:
        window_start = start
        window_end = min(len(text), start + available)
    else:
        padding = available - match_length
        window_start = max(0, start - padding // 2)
        window_end = min(len(text), window_start + available)
        window_start = max(0, window_end - available)
        if start < window_start:
            window_start = start
            window_end = min(len(text), window_start + available)
        if end > window_end:
            window_end = end
            window_start = max(0, window_end - available)

    if window_start > 0:
        boundary = text.find(" ", window_start, min(start, window_start + 24))
        if boundary >= 0:
            window_start = boundary + 1
    if window_end < len(text):
        boundary = text.rfind(" ", max(end, window_end - 24), window_end)
        if boundary >= end:
            window_end = boundary

    body_start = window_start
    body_end = window_end
    while body_start < body_end and text[body_start].isspace():
        body_start += 1
    while body_end > body_start and text[body_end - 1].isspace():
        body_end -= 1
    body = text[body_start:body_end]
    prefix = "…" if window_start > 0 else ""
    suffix = "…" if window_end < len(text) else ""
    snippet = prefix + body + suffix
    return snippet[:SNIPPET_MAX_CHARS], body_start, body_end, len(prefix)


def _context_snippet(text: str, start: int, end: int) -> str:
    snippet, _, _, _ = _context_snippet_details(text, start, end)
    return snippet


def _visible_highlight_range(
    snippet: str,
    body_start: int,
    body_end: int,
    prefix_length: int,
    match_start: int,
    match_end: int,
) -> list[list[int]]:
    visible_body_length = max(0, min(len(snippet) - prefix_length, body_end - body_start))
    visible_body_end = body_start + visible_body_length
    visible_start = max(match_start, body_start)
    visible_end = min(match_end, visible_body_end)
    if visible_start >= visible_end:
        return []
    return [[
        prefix_length + visible_start - body_start,
        prefix_length + visible_end - body_start,
    ]]


def _snippet_with_highlights(
    text: Any,
    query: Any = None,
) -> tuple[str, list[list[int]]]:
    normalized = _normalize_whitespace(text)
    span = _find_query_span(normalized, query)
    if len(normalized) <= SNIPPET_MAX_CHARS:
        return normalized, [list(span)] if span is not None else []

    if span is None:
        return _leading_snippet(normalized), []

    snippet, body_start, body_end, prefix_length = _context_snippet_details(
        normalized,
        *span,
    )
    ranges = _visible_highlight_range(
        snippet,
        body_start,
        body_end,
        prefix_length,
        *span,
    )
    return snippet, ranges


def _snippet(text: Any, query: Any = None) -> str:
    snippet, _ = _snippet_with_highlights(text, query)
    return snippet
