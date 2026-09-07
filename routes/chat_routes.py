"""Processed content Q&A chat routes."""
from __future__ import annotations

import math
from typing import Any

from flask import Blueprint, current_app, g, jsonify, request

from extensions import limiter
from routes.blog_routes import DEFAULT_MODEL
from services.content import note_index_service
from services.core import ai_service
from services.usage import require_usage
from services.usage.usage_lock import UsageLockUnavailable
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, handle_error

chat_bp = Blueprint("chat", __name__)

MAX_QUESTION_CHARS = 500
MAX_CONTEXT_CHARS = 50_000
MAX_HISTORY_TURNS = 10
MAX_HISTORY_CONTENT_CHARS = 2_000
CHAT_ERROR_PREFIX = "[채팅 실패]"
ALLOWED_LANGUAGES = {"ko", "en", "ja"}
MIN_RAG_SOURCE_SCORE = 0.25


@chat_bp.route("/api/chat", methods=["POST"])
@limiter.limit("20/minute")
@require_auth
@require_usage
def chat():
    data = request.get_json(silent=True) or {}
    validation_error, payload = _validate_payload(data)
    if validation_error:
        return api_error(f"{CHAT_ERROR_PREFIX} {validation_error}", 400)

    question = payload["question"]
    context = payload["context"]
    history = payload["history"]
    model = payload["model"]
    language = payload["language"]

    notes = _filter_supported_notes(
        _search_related_notes(question, owner_id=g.get("user_id"))
    )
    if notes is None:
        # 유사도 기준을 통과한 근거가 없어 AI 호출 비용이 발생하지 않았다.
        g.skip_usage_decrement = True
        return jsonify({
            "answer": "[근거 부족] 관련 지식 노트의 유사도가 낮아 답변을 생성하지 않았습니다.",
            "notes": [],
            "rag_sources": [],
            "usage": {},
        })
    messages = _build_messages(
        question=question,
        context=context,
        history=history,
        notes=notes,
        language=language,
    )

    try:
        result = ai_service.create_chat_response(messages, model=model)
        return jsonify({
            "answer": result.get("answer", ""),
            "notes": notes,
            "rag_sources": _build_rag_sources(notes),
            "usage": result.get("usage", {}),
        })
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        current_app.logger.error("Chat answer generation failed: %s", exc, exc_info=True)
        return handle_error(str(exc))


def _validate_payload(data: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    from services.core.ai_service import resolve_public_model

    question = data.get("question", "")
    context = data.get("context", "")
    history = data.get("history") or []
    try:
        model = resolve_public_model(
            data.get("model"), DEFAULT_MODEL, allow_auto=False
        )
    except ValueError as exc:
        return str(exc), {}
    language = data.get("language") if isinstance(data.get("language"), str) else "ko"
    language = language.strip().lower()
    if language not in ALLOWED_LANGUAGES:
        language = "ko"

    if not isinstance(question, str) or not question.strip():
        return "질문을 입력해주세요.", {}
    question = question.strip()
    if len(question) > MAX_QUESTION_CHARS:
        return f"질문은 최대 {MAX_QUESTION_CHARS}자까지 입력할 수 있습니다.", {}

    if not isinstance(context, str) or not context.strip():
        return "답변할 자막/본문이 없습니다.", {}
    context = context.strip()
    if len(context) > MAX_CONTEXT_CHARS:
        return f"자막/본문은 최대 {MAX_CONTEXT_CHARS:,}자까지 사용할 수 있습니다.", {}

    if not isinstance(history, list):
        return "대화 기록 형식이 올바르지 않습니다.", {}
    if len(history) > MAX_HISTORY_TURNS:
        return f"대화 기록은 최대 {MAX_HISTORY_TURNS}턴까지 보낼 수 있습니다.", {}

    normalized_history: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            return "대화 기록 형식이 올바르지 않습니다.", {}
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            return "대화 기록 형식이 올바르지 않습니다.", {}
        normalized_history.append({
            "role": role,
            "content": content.strip()[:MAX_HISTORY_CONTENT_CHARS],
        })

    return None, {
        "question": question,
        "context": context,
        "history": normalized_history,
        "model": model,
        "language": language,
    }


def _search_related_notes(
    question: str,
    *,
    owner_id: str | None,
) -> list[dict[str, Any]]:
    try:
        return note_index_service.search_notes(
            question,
            owner_id=owner_id,
            limit=3,
        )
    except Exception as exc:
        current_app.logger.warning("Chat note search failed (ignored): %s", exc)
        return []


def _filter_supported_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    if not notes:
        return []
    supported = [
        note
        for note in notes
        if (_numeric_score(note.get("score")) or 0.0) >= MIN_RAG_SOURCE_SCORE
    ]
    return supported if supported else None


def _build_messages(
    question: str,
    context: str,
    history: list[dict[str, str]],
    notes: list[dict[str, Any]],
    language: str,
) -> list[dict[str, str]]:
    system = (
        "당신은 처리된 자막/본문과 관련 지식 노트만 근거로 답하는 Q&A 도우미입니다. "
        "제공된 [현재 콘텐츠]와 [관련 지식 노트]에 없는 내용은 추측하지 말고 "
        "\"자막에 없는 내용입니다\"라고 답하세요. 타임스탬프가 있으면 함께 인용하세요. "
        f"기본 답변 언어는 {language or 'ko'}이며, 한국어 요청이 없으면 한국어로 답하세요."
    )
    user_prompt = (
        f"[현재 콘텐츠]\n{context}\n\n"
        f"[관련 지식 노트]\n{_format_notes(notes)}\n\n"
        f"[질문]\n{question}"
    )
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": user_prompt}]


def _format_notes(notes: list[dict[str, Any]]) -> str:
    if not notes:
        return "관련 지식 노트 없음"
    lines: list[str] = []
    for idx, note in enumerate(notes, 1):
        title = str(note.get("title") or f"노트 {idx}").strip()
        snippet = str(note.get("snippet") or "").strip()
        score = note.get("score")
        score_text = f" (score: {score})" if score is not None else ""
        lines.append(f"{idx}. {title}{score_text}\n{snippet}")
    return "\n\n".join(lines)


def _build_rag_sources(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for note in notes:
        note_id = str(note.get("id") or "").strip()
        title = str(note.get("title") or "").strip()
        snippet = str(note.get("snippet") or "").strip()
        source = {
            "type": "knowledge_note",
            "id": note_id,
            "title": title or "지식 노트",
            "snippet": snippet,
        }
        score = _numeric_score(note.get("score"))
        if score is not None:
            source["score"] = score
        sources.append(source)
    return sources


def _numeric_score(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if math.isfinite(score) else None
