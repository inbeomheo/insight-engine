"""Orchestrates product support Q&A and feedback ticket creation."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from services.support.feedback_store import FeedbackStore, get_feedback_store
from services.support.feedback_triage_service import classify_message
from services.support.github_handoff_service import github_config_status
from services.support.product_knowledge_service import answer_product_question

_AUTH_HEADER_RE = re.compile(r"(?i)\bauthorization\b\s*[:=]\s*(?:bearer\s+)?[^\s,;]+")
_SECRET_RE = re.compile(
    r"(?i)\b(bearer|token|access[_-]?token|refresh[_-]?token|api[_-]?key|password|secret)\b\s*[:=]\s*[^\s,;&]+"
)
_QUERY_SECRET_RE = re.compile(
    r"(?i)([?&](?:token|access_token|refresh_token|api_key|key|sig|signature|X-Amz-Signature)=)[^&\s]+"
)
_URL_RE = re.compile(r"https?://[^\s]+")
_COMMON_TOKEN_RE = re.compile(
    r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AIza[0-9A-Za-z_-]{20,})\b"
)
_ALLOWED_SUPPORT_MODES = {"auto", "question", "feedback", "bug", "feature"}


def _redact_url(match: re.Match[str]) -> str:
    raw = match.group(0)
    try:
        parts = urlsplit(raw)
        host = parts.hostname or parts.netloc
        if parts.port:
            host = f"{host}:{parts.port}"
        safe_query = _QUERY_SECRET_RE.sub(r"\1[REDACTED]", f"?{parts.query}")[1:] if parts.query else ""
        return urlunsplit((parts.scheme, host, parts.path, safe_query, ""))
    except Exception:
        return "[REDACTED_URL]"


def redact_diagnostic(value: str, max_length: int = 500) -> str:
    text = str(value or "")
    text = _AUTH_HEADER_RE.sub("authorization=[REDACTED]", text)
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = _COMMON_TOKEN_RE.sub("[REDACTED_TOKEN]", text)
    text = _URL_RE.sub(_redact_url, text)
    return text[:max(1, max_length)]


def _clean_context_value(value: Any, max_length: int = 240) -> str:
    return redact_diagnostic(str(value or "").strip(), max_length=max_length)


def _normalize_support_mode(mode: str) -> str:
    mode = str(mode or "auto").strip()
    return mode if mode in _ALLOWED_SUPPORT_MODES else "auto"


def _build_reproduction_note(
    *,
    message: str,
    current_url: str,
    route: str,
    selected_model: str,
    generation_mode: str,
    selected_style: str,
) -> str:
    location = current_url or route or "unknown"
    state_parts = []
    if selected_model:
        state_parts.append(f"모델 `{selected_model}`")
    if generation_mode:
        state_parts.append(f"생성 모드 `{generation_mode}`")
    if selected_style:
        state_parts.append(f"스타일 `{selected_style}`")

    lines = [f"1. `{location}` 화면에서 사용자 피드백이 접수되었습니다."]
    if state_parts:
        lines.append(f"2. 당시 선택 상태: {', '.join(state_parts)}")
        lines.append(f"3. 사용자 보고 내용: {message}")
    else:
        lines.append(f"2. 사용자 보고 내용: {message}")
    return "\n".join(lines)


def sanitize_console_errors(console_errors: list[str] | None) -> list[str]:
    if not console_errors:
        return []
    return [redact_diagnostic(item) for item in console_errors[-8:]]


def handle_support_chat(
    *,
    message: str,
    route: str = "",
    current_url: str = "",
    viewport: dict[str, Any] | None = None,
    user_agent: str = "",
    console_errors: list[str] | None = None,
    screenshot_url: str = "",
    selected_provider: str = "",
    selected_model: str = "",
    generation_mode: str = "",
    selected_style: str = "",
    detail_level: str = "",
    mode: str = "auto",
    user_id: str | None = None,
    store: FeedbackStore | None = None,
) -> dict[str, Any]:
    text = (message or "").strip()
    if not text:
        raise ValueError("메시지를 입력해주세요.")

    store = store or get_feedback_store()
    intake_mode = _normalize_support_mode(mode)
    safe_text = redact_diagnostic(text, max_length=2000)
    safe_route = _clean_context_value(route)
    safe_current_url = _clean_context_value(current_url, max_length=500)
    safe_selected_provider = _clean_context_value(selected_provider, max_length=80)
    safe_selected_model = _clean_context_value(selected_model, max_length=120)
    safe_generation_mode = _clean_context_value(generation_mode, max_length=80)
    safe_selected_style = _clean_context_value(selected_style, max_length=80)
    safe_detail_level = _clean_context_value(detail_level, max_length=80)
    safe_user_agent = _clean_context_value(user_agent, max_length=300)
    safe_console_errors = sanitize_console_errors(console_errors)
    triage = classify_message(safe_text)
    forced_feedback = intake_mode in {"feedback", "bug", "feature"}
    forced_question = intake_mode == "question"

    if forced_question or (intake_mode == "auto" and triage["kind"] == "question"):
        answer = answer_product_question(safe_text, {"route": safe_route, "current_url": safe_current_url, "viewport": viewport})
        return {
            "reply": answer["answer"],
            "action": "answered",
            "triage": triage,
            "answer": answer,
            "github": github_config_status(),
            "suggested_next_actions": ["불편사항으로 접수", "GitHub 이슈 올리기", "닫기"],
        }

    support_context = {
        "support_mode": intake_mode,
        "current_url": safe_current_url,
        "route": safe_route,
        "selected_provider": safe_selected_provider,
        "selected_model": safe_selected_model,
        "generation_mode": safe_generation_mode,
        "selected_style": safe_selected_style,
        "detail_level": safe_detail_level,
    }
    reproduction = _build_reproduction_note(
        message=safe_text,
        current_url=safe_current_url,
        route=safe_route,
        selected_model=safe_selected_model,
        generation_mode=safe_generation_mode,
        selected_style=safe_selected_style,
    )

    ticket = store.create_ticket({
        "kind": triage["kind"],
        "severity": triage["severity"],
        "priority": triage["priority"],
        "title": triage["title"],
        "message": safe_text,
        "route": safe_route,
        "current_url": safe_current_url,
        "selected_provider": safe_selected_provider,
        "selected_model": safe_selected_model,
        "generation_mode": safe_generation_mode,
        "selected_style": safe_selected_style,
        "detail_level": safe_detail_level,
        "viewport": viewport,
        "user_agent": safe_user_agent,
        "console_errors": safe_console_errors,
        "screenshot_url": redact_diagnostic(screenshot_url) if screenshot_url else "",
        "related_files": triage["related_files"],
        "suggested_fix": triage["suggested_fix"],
        "labels": triage["labels"],
        "metadata": {
            "mode": intake_mode,
            "support_mode": intake_mode,
            "priority": triage["priority"],
            "classification_confidence": triage["confidence"],
            "context": support_context,
            "reproduction": reproduction,
            "expected": "사용자가 현재 화면에서 선택한 모델/모드 흐름을 막힘 없이 완료할 수 있어야 합니다.",
            "actual": safe_text,
        },
    }, user_id=user_id)

    kind_label = {
        "bug": "버그",
        "usability": "사용성 불편",
        "feature": "기능 요청",
        "ops": "운영 이슈",
    }.get(ticket["kind"], "피드백")
    file_hint = ""
    if ticket.get("related_files"):
        file_hint = f" 관련 파일 후보는 `{ticket['related_files'][0]}` 쪽으로 보여."

    return {
        "reply": f"{kind_label}로 접수했어. 심각도는 `{ticket['severity']}`로 분류했고,{file_hint} GitHub 이슈로 넘길 수 있어.",
        "action": "ticket_created",
        "ticket": ticket,
        "triage": triage,
        "github": github_config_status(),
        "suggested_next_actions": ["GitHub 이슈 올리기", "Draft PR 만들기", "닫기"],
    }
