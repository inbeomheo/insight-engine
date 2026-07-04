"""Knowledge notes API routes.

First slice: notes are stored in one shared local directory without per-user
separation. User-scoped storage is a follow-up slice.
"""
from flask import Blueprint, current_app, jsonify, request

from extensions import limiter
from routes.blog_routes import DEFAULT_MODEL
from services.content import note_service
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, handle_error, validate_content_length

notes_bp = Blueprint("notes", __name__, url_prefix="/api/notes")


@notes_bp.route("", methods=["POST"])
@limiter.limit("15/minute")
@require_auth
def create_note():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    source = data.get("source") or {}
    language = data.get("language") or "ko"
    model = data.get("model") or DEFAULT_MODEL

    if not isinstance(content, str) or not content.strip():
        return api_error("[노트 생성 실패] 콘텐츠가 필요합니다.", 400)
    length_error = validate_content_length(content)
    if length_error:
        return api_error(f"[노트 생성 실패] {length_error}", 400)

    try:
        style_prompt = current_app.config.get("STYLE_PROMPTS", {}).get(
            note_service.NOTE_STYLE_ID
        )
        note = note_service.generate_knowledge_note(
            content,
            source,
            language=language,
            model=model,
            style_prompt=style_prompt,
        )
        return jsonify(note)
    except ValueError as exc:
        message = str(exc)
        if not message.startswith("[노트 생성 실패]"):
            message = f"[노트 생성 실패] {message}"
        return api_error(message, 400)
    except Exception as exc:
        current_app.logger.error("Knowledge note generation failed: %s", exc, exc_info=True)
        return handle_error(str(exc))


@notes_bp.route("", methods=["GET"])
@require_auth
def list_notes():
    return jsonify({"notes": note_service.list_notes()})


@notes_bp.route("/<note_id>", methods=["GET"])
@require_auth
def get_note(note_id):
    note = note_service.load_note(note_id)
    if note is None:
        return api_error("[노트 조회 실패] 노트를 찾을 수 없습니다.", 404)
    return jsonify(note)
