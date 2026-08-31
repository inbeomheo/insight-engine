"""Knowledge note generation and file storage.

Notes are stored per owner at ``notes/users/<owner_id>/<note_id>.json``.
Legacy files that already exist at ``notes/<note_id>.json`` are never deleted;
they are only readable through an explicit legacy/admin path.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from config import get_model_max_tokens
from prompts.styles.knowledge_note import KNOWLEDGE_NOTE_PROMPT
from services.core import ai_service, content_service
from services.core.logging_config import get_logger

NOTES_DIR = Path(os.getenv("KNOWLEDGE_NOTES_DIR", "data/notes"))
NOTE_STYLE_ID = "knowledge_note"
SOURCE_TYPES = {"youtube", "article", "text"}
URL_REQUIRED_SOURCE_TYPES = {"youtube", "article"}
LOCAL_OWNER = "_local"
LEGACY_SCOPE = "legacy"
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
_OWNER_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
logger = get_logger(__name__)


def resolve_note_owner(owner_id: str | None) -> str:
    raw = str(owner_id or "").strip()
    if not raw:
        return LOCAL_OWNER
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", raw)[:128]
    return cleaned if _OWNER_RE.fullmatch(cleaned) else LOCAL_OWNER


def is_legacy_notes_accessor(owner_id: str | None, is_admin: bool = False) -> bool:
    if is_admin:
        return True
    configured = (os.getenv("LEGACY_NOTES_OWNER_ID") or "").strip()
    return bool(configured and owner_id and configured == str(owner_id))


def validate_note(note: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a note dict without external dependencies."""
    errors: list[str] = []
    if not isinstance(note, dict):
        return False, ["노트는 JSON 객체여야 합니다."]

    required = {"id", "source", "key_concepts", "summary", "quotes", "tags", "language", "created_at"}
    missing = required - set(note.keys())
    if missing:
        errors.append(f"필수 필드가 없습니다: {', '.join(sorted(missing))}")

    note_id = note.get("id")
    if not isinstance(note_id, str) or not note_id.strip() or not _ID_RE.fullmatch(note_id):
        errors.append("id는 안전한 문자열이어야 합니다.")

    source = note.get("source")
    if not isinstance(source, dict):
        errors.append("source는 객체여야 합니다.")
    else:
        if source.get("type") not in SOURCE_TYPES:
            errors.append("source.type은 youtube, article 또는 text여야 합니다.")
        if source.get("type") in URL_REQUIRED_SOURCE_TYPES and (
            not isinstance(source.get("url"), str) or not source.get("url", "").strip()
        ):
            errors.append("source.url은 비어 있지 않은 문자열이어야 합니다.")
        elif "url" in source and not isinstance(source.get("url"), str):
            errors.append("source.url은 문자열이어야 합니다.")
        if not isinstance(source.get("title"), str) or not source.get("title", "").strip():
            errors.append("source.title은 비어 있지 않은 문자열이어야 합니다.")

    for key in ("key_concepts", "tags"):
        value = note.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{key}는 비어 있지 않은 문자열 배열이어야 합니다.")

    for key in ("learning_points",):
        value = note.get(key, [])
        if value and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
            errors.append(f"{key}는 문자열 배열이어야 합니다.")

    review_questions = note.get("review_questions", [])
    if review_questions:
        if not isinstance(review_questions, list):
            errors.append("review_questions는 배열이어야 합니다.")
        else:
            for item in review_questions:
                if not isinstance(item, dict):
                    errors.append("review_questions 항목은 객체여야 합니다.")
                    continue
                if not isinstance(item.get("question"), str) or not item.get("question", "").strip():
                    errors.append("review_questions.question은 비어 있지 않은 문자열이어야 합니다.")
                if not isinstance(item.get("answer"), str) or not item.get("answer", "").strip():
                    errors.append("review_questions.answer는 비어 있지 않은 문자열이어야 합니다.")

    if not isinstance(note.get("summary"), str) or not note.get("summary", "").strip():
        errors.append("summary는 비어 있지 않은 문자열이어야 합니다.")

    quotes = note.get("quotes")
    if not isinstance(quotes, list):
        errors.append("quotes는 배열이어야 합니다.")
    else:
        for quote in quotes:
            if not isinstance(quote, dict):
                errors.append("quotes 항목은 객체여야 합니다.")
                continue
            if not isinstance(quote.get("text"), str) or not quote.get("text", "").strip():
                errors.append("quote.text는 비어 있지 않은 문자열이어야 합니다.")
            if not isinstance(quote.get("ref"), str):
                errors.append("quote.ref는 문자열이어야 합니다.")

    if not isinstance(note.get("language"), str) or not note.get("language", "").strip():
        errors.append("language는 비어 있지 않은 문자열이어야 합니다.")

    created_at = note.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        errors.append("created_at은 ISO8601 문자열이어야 합니다.")
    else:
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("created_at은 ISO8601 형식이어야 합니다.")

    return len(errors) == 0, errors


def parse_note_response(raw: Any) -> dict[str, Any]:
    """Parse fenced JSON first, then tolerant JSON/Markdown fallbacks."""
    if isinstance(raw, dict):
        return _unwrap_note(raw)

    text = str(raw or "").strip()
    candidates = [m.group(1) for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)]
    candidates += [text, _extract_first_json_object(text)]

    for candidate in candidates:
        if not candidate:
            continue
        data = _loads_json(candidate)
        if isinstance(data, dict):
            return _unwrap_note(data)

    markdown_note = _parse_markdown_note(text)
    if markdown_note:
        return _normalize_generated_note(markdown_note)
    raise ValueError("AI 응답에서 노트 JSON을 찾을 수 없습니다.")


def save_note(note: dict[str, Any], owner_id: str | None = None) -> dict[str, Any]:
    valid, errors = validate_note(note)
    if not valid:
        raise ValueError("[노트 생성 실패] " + "; ".join(errors))

    owner = resolve_note_owner(owner_id or note.get("owner_id"))
    note = {**note, "owner_id": owner}
    path = _note_path(note["id"], owner_id=owner)
    if path is None:
        raise ValueError("[노트 생성 실패] 유효하지 않은 노트 ID입니다.")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return note


def load_note(
    note_id: str,
    owner_id: str | None = None,
    include_legacy: bool = False,
) -> dict[str, Any] | None:
    owner = resolve_note_owner(owner_id)
    path = _note_path(note_id, owner_id=owner)
    note = _read_note_file(path)
    if note is not None:
        return note
    if include_legacy:
        return _read_note_file(_legacy_note_path(note_id))
    return None


def list_notes(
    owner_id: str | None = None,
    include_legacy: bool = False,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    owner = resolve_note_owner(owner_id)
    user_dir = _user_notes_dir(owner)
    if user_dir.exists():
        for path in user_dir.glob("*.json"):
            note = _read_note_file(path)
            summary = _note_list_item(note)
            if summary:
                items.append(summary)

    if include_legacy:
        notes_dir = Path(NOTES_DIR)
        if notes_dir.exists():
            for path in notes_dir.glob("*.json"):
                note = _read_note_file(path)
                summary = _note_list_item(note, legacy=True)
                if summary:
                    items.append(summary)

    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def find_notes_by_source_url(
    source: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
    owner_id: str | None = None,
) -> list[dict[str, Any]]:
    """Find existing notes with the same canonical source URL."""
    normalized = normalize_source(source)
    target_url = _canonical_url(normalized["url"])
    if not target_url:
        return []
    duplicates: list[dict[str, Any]] = []
    source_notes = list_notes(owner_id=owner_id) if notes is None else notes

    for item in source_notes:
        item_source = item.get("source") if isinstance(item.get("source"), dict) else {}
        if _canonical_url(str(item_source.get("url", ""))) != target_url:
            continue
        duplicates.append({
            "id": item.get("id"),
            "title": item.get("title", ""),
            "created_at": item.get("created_at", ""),
            "source": item_source,
        })
    return duplicates


def generate_knowledge_note(
    content: str,
    source: dict[str, Any],
    model: str,
    language: str = "ko",
    style_prompt: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("[노트 생성 실패] 콘텐츠가 필요합니다.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("[노트 생성 실패] 모델이 필요합니다.")

    source = normalize_source(source)
    model = model.strip()
    language = str(language or "ko").strip() or "ko"
    prompt = style_prompt or KNOWLEDGE_NOTE_PROMPT
    ai_input = _build_ai_input(content, source, language)
    max_tokens = min(get_model_max_tokens(model), 50000)
    ai_input = content_service.truncate_text(ai_input, max_tokens)

    result = ai_service.create_content(
        ai_input,
        model,
        prompt,
        style_id=NOTE_STYLE_ID,
        modifiers={"language": language},
    )
    raw = result.get("content", "") if isinstance(result, dict) else result
    parsed = parse_note_response(raw)
    note = {
        **parsed,
        "id": uuid.uuid4().hex,
        "source": source,
        "language": parsed.get("language") or language,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "owner_id": resolve_note_owner(owner_id),
    }
    valid, errors = validate_note(note)
    if not valid:
        raise ValueError("[노트 생성 실패] " + "; ".join(errors))
    return save_note(note, owner_id=note["owner_id"])


def _user_notes_dir(owner_id: str) -> Path:
    return Path(NOTES_DIR) / "users" / resolve_note_owner(owner_id)


def _legacy_note_path(note_id: str) -> Path | None:
    if not isinstance(note_id, str) or not _ID_RE.fullmatch(note_id):
        return None
    return Path(NOTES_DIR) / f"{note_id}.json"


def _note_path(note_id: str, owner_id: str | None = None) -> Path | None:
    if not isinstance(note_id, str) or not _ID_RE.fullmatch(note_id):
        return None
    return _user_notes_dir(resolve_note_owner(owner_id)) / f"{note_id}.json"


def _read_note_file(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Knowledge note load failed: %s", exc)
        return None
    return data if isinstance(data, dict) else None


def _note_list_item(note: dict[str, Any] | None, legacy: bool = False) -> dict[str, Any] | None:
    if not isinstance(note, dict):
        return None
    source = note.get("source") or {}
    item = {
        "id": note.get("id"),
        "title": source.get("title", ""),
        "tags": note.get("tags", []),
        "key_concepts": note.get("key_concepts", []),
        "summary": note.get("summary", ""),
        "quote_count": len(note.get("quotes", []) if isinstance(note.get("quotes"), list) else []),
        "learning_point_count": len(note.get("learning_points", []) if isinstance(note.get("learning_points"), list) else []),
        "review_question_count": len(note.get("review_questions", []) if isinstance(note.get("review_questions"), list) else []),
        "created_at": note.get("created_at", ""),
        "source": source,
        "owner_id": note.get("owner_id") or (LEGACY_SCOPE if legacy else LOCAL_OWNER),
    }
    if legacy:
        item["legacy"] = True
    return item


def _normalize_source(source: dict[str, Any]) -> dict[str, str]:
    if not isinstance(source, dict):
        raise ValueError("[노트 생성 실패] source는 객체여야 합니다.")
    source_type = str(source.get("type", "")).strip().lower()
    url = str(source.get("url", "")).strip()
    title = str(source.get("title", "")).strip()
    if source_type not in SOURCE_TYPES:
        raise ValueError("[노트 생성 실패] source.type은 youtube, article 또는 text여야 합니다.")
    if source_type in URL_REQUIRED_SOURCE_TYPES and not url:
        raise ValueError("[노트 생성 실패] source.url이 필요합니다.")
    if source_type == "text" and not title:
        title = "직접 입력 텍스트"
    if not title:
        raise ValueError("[노트 생성 실패] source.title이 필요합니다.")
    return {"type": source_type, "url": url, "title": title}


def normalize_source(source: dict[str, Any]) -> dict[str, str]:
    return _normalize_source(source)


def _canonical_url(url: str) -> str:
    raw_url = str(url or "").strip()
    if not raw_url:
        return ""
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return raw_url.rstrip("/")

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query_pairs = _canonical_query_pairs(parsed.query)
    query = urlencode(query_pairs)

    if host in {"youtube.com", "m.youtube.com"} and parsed.path.rstrip("/") == "/watch":
        video_id = next((value for key, value in query_pairs if key == "v"), "")
        if video_id:
            return f"https://youtube.com/watch?v={video_id}"
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://youtube.com/watch?v={video_id}"

    return urlunsplit((
        parsed.scheme.lower(),
        host,
        parsed.path.rstrip("/"),
        "",
        query,
    ))


def _canonical_query_pairs(query: str) -> list[tuple[str, str]]:
    tracking_keys = {"fbclid", "gclid"}
    pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in tracking_keys:
            continue
        pairs.append((key, value))
    return sorted(pairs)


def _build_ai_input(content: str, source: dict[str, str], language: str) -> str:
    url_line = f"url: {source['url']}\n" if source.get("url") else ""
    return (
        "[source]\n"
        f"type: {source['type']}\n{url_line}title: {source['title']}\nlanguage: {language}\n\n"
        "[content]\n"
        f"{content}"
    )


def _loads_json(text: str) -> Any:
    cleaned = text.strip().lstrip("\ufeff")
    for candidate in (cleaned, re.sub(r",\s*([}\]])", r"\1", cleaned)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def _extract_first_json_object(text: str) -> str:
    for start, char in enumerate(text):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
    return ""


def _unwrap_note(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("note"), dict):
        data = data["note"]
    return _normalize_generated_note(data)


def _normalize_generated_note(note: dict[str, Any]) -> dict[str, Any]:
    note = dict(note or {})
    note["key_concepts"] = _coerce_str_list(note.get("key_concepts"))
    note["tags"] = _coerce_str_list(note.get("tags"))
    note["learning_points"] = _coerce_str_list(note.get("learning_points"))
    note["review_questions"] = _coerce_review_questions(note.get("review_questions"))
    note["quotes"] = _coerce_quotes(note.get("quotes"))
    note["summary"] = str(note.get("summary", "")).strip()
    note["language"] = str(note.get("language", "")).strip()
    return note


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = re.split(r"\n|,", value)
    else:
        items = []
    return [str(item).strip(" -•\t") for item in items if str(item).strip(" -•\t")]


def _coerce_quotes(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    quotes: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            ref = str(item.get("ref", "")).strip()
        else:
            text = str(item).strip()
            ref = ""
        if text:
            quotes.append({"text": text, "ref": ref})
    return quotes


def _coerce_review_questions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    questions: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
        else:
            text = str(item).strip()
            if "?" in text:
                question, answer = text.split("?", 1)
                question = question.strip() + "?"
                answer = answer.strip(" :-")
            else:
                question, answer = text, ""
        if question and answer:
            questions.append({"question": question, "answer": answer})
    return questions


def _parse_markdown_note(text: str) -> dict[str, Any] | None:
    summary = _markdown_section(text, "summary")
    concepts = _markdown_list_section(text, "key_concepts")
    tags = _markdown_list_section(text, "tags")
    if not summary and not concepts and not tags:
        return None
    return {
        "key_concepts": concepts,
        "summary": summary,
        "learning_points": [],
        "review_questions": [],
        "quotes": [],
        "tags": tags,
        "language": "ko",
    }


def _markdown_section(text: str, name: str) -> str:
    pattern = rf"(?im)^#+\s*{re.escape(name)}\s*$([\s\S]*?)(?=^#+\s|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _markdown_list_section(text: str, name: str) -> list[str]:
    section = _markdown_section(text, name)
    return [line.strip(" -•\t") for line in section.splitlines() if line.strip(" -•\t")]
