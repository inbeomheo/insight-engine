"""Knowledge note generation and file storage.

First slice: notes are stored in one shared local directory without per-user
separation. User-scoped storage is a follow-up slice.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_model_max_tokens
from prompts.styles.knowledge_note import KNOWLEDGE_NOTE_PROMPT
from services.core import ai_service, content_service
from services.core.logging_config import get_logger

NOTES_DIR = Path(os.getenv("KNOWLEDGE_NOTES_DIR", "data/notes"))
NOTE_STYLE_ID = "knowledge_note"
SOURCE_TYPES = {"youtube", "article"}
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
logger = get_logger(__name__)


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
            errors.append("source.type은 youtube 또는 article이어야 합니다.")
        for key in ("url", "title"):
            if not isinstance(source.get(key), str) or not source.get(key, "").strip():
                errors.append(f"source.{key}는 비어 있지 않은 문자열이어야 합니다.")

    for key in ("key_concepts", "tags"):
        value = note.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{key}는 비어 있지 않은 문자열 배열이어야 합니다.")

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


def save_note(note: dict[str, Any]) -> dict[str, Any]:
    valid, errors = validate_note(note)
    if not valid:
        raise ValueError("[노트 생성 실패] " + "; ".join(errors))

    notes_dir = Path(NOTES_DIR)
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = _note_path(note["id"])
    if path is None:
        raise ValueError("[노트 생성 실패] 유효하지 않은 노트 ID입니다.")

    tmp = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return note


def load_note(note_id: str) -> dict[str, Any] | None:
    path = _note_path(note_id)
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Knowledge note load failed: %s", exc)
        return None


def list_notes() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    notes_dir = Path(NOTES_DIR)
    if not notes_dir.exists():
        return items

    for path in notes_dir.glob("*.json"):
        note = load_note(path.stem)
        if not isinstance(note, dict):
            continue
        source = note.get("source") or {}
        items.append({
            "id": note.get("id"),
            "title": source.get("title", ""),
            "tags": note.get("tags", []),
            "created_at": note.get("created_at", ""),
            "source": source,
        })
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def generate_knowledge_note(
    content: str,
    source: dict[str, Any],
    model: str,
    language: str = "ko",
    style_prompt: str | None = None,
) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("[노트 생성 실패] 콘텐츠가 필요합니다.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("[노트 생성 실패] 모델이 필요합니다.")

    source = _normalize_source(source)
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
    }
    valid, errors = validate_note(note)
    if not valid:
        raise ValueError("[노트 생성 실패] " + "; ".join(errors))
    return save_note(note)


def _note_path(note_id: str) -> Path | None:
    if not isinstance(note_id, str) or not _ID_RE.fullmatch(note_id):
        return None
    return Path(NOTES_DIR) / f"{note_id}.json"


def _normalize_source(source: dict[str, Any]) -> dict[str, str]:
    if not isinstance(source, dict):
        raise ValueError("[노트 생성 실패] source는 객체여야 합니다.")
    source_type = str(source.get("type", "")).strip().lower()
    url = str(source.get("url", "")).strip()
    title = str(source.get("title", "")).strip()
    if source_type not in SOURCE_TYPES:
        raise ValueError("[노트 생성 실패] source.type은 youtube 또는 article이어야 합니다.")
    if not url or not title:
        raise ValueError("[노트 생성 실패] source.url과 source.title이 필요합니다.")
    return {"type": source_type, "url": url, "title": title}


def _build_ai_input(content: str, source: dict[str, str], language: str) -> str:
    return (
        "[source]\n"
        f"type: {source['type']}\nurl: {source['url']}\ntitle: {source['title']}\nlanguage: {language}\n\n"
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


def _parse_markdown_note(text: str) -> dict[str, Any] | None:
    summary = _markdown_section(text, "summary")
    concepts = _markdown_list_section(text, "key_concepts")
    tags = _markdown_list_section(text, "tags")
    if not summary and not concepts and not tags:
        return None
    return {
        "key_concepts": concepts,
        "summary": summary,
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
