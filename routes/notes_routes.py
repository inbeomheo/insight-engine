"""Knowledge notes API routes.

Notes are user-scoped. Legacy root files stay on disk and are visible only to
the configured legacy owner/admin; other users cannot enumerate them.
"""
from flask import Blueprint, current_app, g, jsonify, request

from extensions import limiter
from routes.blog_routes import DEFAULT_MODEL
from services.content import note_index_service, note_service
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, clamp_query_int, handle_error, validate_content_length

notes_bp = Blueprint("notes", __name__, url_prefix="/api/notes")
MAX_SEARCH_QUERY_CHARS = 200
DUPLICATE_SIMILARITY_THRESHOLD = 0.92
DUPLICATE_SIMILARITY_LIMIT = 3
DUPLICATE_QUERY_MAX_CHARS = 2000


def _current_owner_id() -> str:
    return note_service.resolve_note_owner(getattr(g, "user_id", None))


def _can_access_legacy() -> bool:
    from services.usage.usage_service import UsageService

    user_id = getattr(g, "user_id", None)
    is_admin = bool(user_id and UsageService.is_admin_user(user_id))
    return note_service.is_legacy_notes_accessor(user_id, is_admin=is_admin)


def _legacy_requested() -> bool:
    scope = (request.args.get("scope") or "").strip().lower()
    return scope in {"", note_service.LEGACY_SCOPE}


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
        duplicate_reason, duplicate_notes = _find_duplicate_notes(content, source)
        if duplicate_notes:
            return _duplicate_warning_response(duplicate_reason, duplicate_notes)

        style_prompt = current_app.config.get("STYLE_PROMPTS", {}).get(
            note_service.NOTE_STYLE_ID
        )
        owner_id = _current_owner_id()
        note = note_service.generate_knowledge_note(
            content,
            source,
            language=language,
            model=model,
            style_prompt=style_prompt,
            owner_id=owner_id,
        )
        try:
            note_index_service.index_note(note, owner_id=owner_id)
        except Exception as index_exc:
            current_app.logger.warning(
                "Knowledge note indexing failed (ignored): %s",
                index_exc,
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
    include_legacy = _legacy_requested() and _can_access_legacy()
    return jsonify({
        "notes": note_service.list_notes(
            owner_id=_current_owner_id(),
            include_legacy=include_legacy,
        )
    })


@notes_bp.route("/search", methods=["GET"])
@limiter.limit("30/minute")
@require_auth
def search_notes():
    query = (request.args.get("q") or "").strip()
    if not query:
        return api_error("[검색 실패] 검색어가 필요합니다.", 400)
    if len(query) > MAX_SEARCH_QUERY_CHARS:
        return api_error(
            f"[검색 실패] 검색어는 최대 {MAX_SEARCH_QUERY_CHARS}자까지 입력할 수 있습니다.",
            400,
        )

    limit = clamp_query_int(
        request.args.get("limit"),
        default=note_index_service.DEFAULT_SEARCH_LIMIT,
        min_val=1,
        max_val=note_index_service.MAX_SEARCH_LIMIT,
    )
    try:
        return jsonify({
            "notes": note_index_service.search_notes(
                query,
                limit=limit,
                owner_id=_current_owner_id(),
            )
        })
    except Exception as exc:
        current_app.logger.error("Knowledge note search failed: %s", exc, exc_info=True)
        return api_error("[검색 실패] 노트 검색 중 오류가 발생했습니다.", 500)


@notes_bp.route("/<note_id>", methods=["GET"])
@require_auth
def get_note(note_id):
    include_legacy = _legacy_requested() and _can_access_legacy()
    note = note_service.load_note(
        note_id,
        owner_id=_current_owner_id(),
        include_legacy=include_legacy,
    )
    if note is None:
        return api_error("[노트 조회 실패] 노트를 찾을 수 없습니다.", 404)
    try:
        note["related_notes"] = note_index_service.get_related_notes(
            note,
            limit=3,
            owner_id=_current_owner_id(),
        )
    except Exception as exc:
        current_app.logger.warning(
            "Related note lookup failed (ignored): %s",
            exc,
            exc_info=True,
        )
        note["related_notes"] = []
    return jsonify(note)


def _find_duplicate_notes(content: str, source: dict) -> tuple[str, list[dict]]:
    owner_id = _current_owner_id()
    normalized_source = note_service.normalize_source(source)
    existing_notes = note_service.list_notes(owner_id=owner_id)
    same_url_notes = note_service.find_notes_by_source_url(
        normalized_source, notes=existing_notes, owner_id=owner_id
    )
    if same_url_notes:
        return "same_url", same_url_notes

    if not existing_notes:
        return "", []

    query = str(content or "").strip()[:DUPLICATE_QUERY_MAX_CHARS]
    if not query:
        return "", []

    try:
        similar_notes = [
            note
            for note in note_index_service.search_notes(
                query, limit=DUPLICATE_SIMILARITY_LIMIT, owner_id=owner_id
            )
            if float(note.get("score") or 0) > DUPLICATE_SIMILARITY_THRESHOLD
        ]
    except Exception as exc:
        current_app.logger.warning(
            "Duplicate note similarity lookup failed (ignored): %s",
            exc,
            exc_info=True,
        )
        return "", []
    return ("similar_content", similar_notes) if similar_notes else ("", [])


def _duplicate_warning_response(reason: str, duplicate_notes: list[dict]):
    reason_label = "동일 URL" if reason == "same_url" else "유사 콘텐츠"
    return jsonify({
        "error": "[재학습 경고] 이미 학습한 소스와 중복될 수 있습니다.",
        "warning": f"[재학습 경고] {reason_label}로 보이는 기존 노트가 있습니다.",
        "next_action": "새 노트를 만들기보다 기존 노트를 열어 관련 개념을 이어서 확인하세요.",
        "duplicate_reason": reason,
        "duplicate_notes": duplicate_notes,
    }), 409
