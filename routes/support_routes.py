"""Support assistant API routes.

These endpoints power the in-app product Q&A / feedback intake assistant.
They do not modify application code; GitHub handoff endpoints only create Issues
or docs-only Draft PRs for separate worker agents.
"""
from __future__ import annotations

import hmac
import os
import re
from hashlib import sha256

from flask import Blueprint, g, jsonify, request

from extensions import limiter

from services.support.feedback_store import get_feedback_store
from services.support.github_handoff_service import (
    GitHubHandoffError,
    create_draft_pr,
    create_github_issue,
    github_config_status,
)
from services.support.support_agent_service import handle_support_chat

support_bp = Blueprint("support", __name__)


def _current_user_id() -> str:
    auth_user = getattr(g, "user_id", None)
    if auth_user:
        return str(auth_user)

    # Support Assistant is intentionally lighter than authenticated app APIs so
    # visitors can ask product questions and file feedback. In no-auth/dev
    # deployments, isolate tickets by a browser-generated opaque session id
    # instead of collapsing everyone into the same "anonymous" owner.
    raw_session = request.headers.get("X-Support-Session-Id", "")
    session_id = re.sub(r"[^0-9A-Za-z_-]", "", raw_session)[:80]
    if session_id:
        return f"support-session:{session_id}"

    fallback = sha256(f"{request.remote_addr}|{request.headers.get('User-Agent', '')}".encode("utf-8")).hexdigest()[:24]
    return f"support-session:fallback-{fallback}"


def _owns(ticket: dict) -> bool:
    return ticket.get("user_id") == _current_user_id()


def _payload() -> dict:
    return request.get_json(silent=True) or {}


def _handoff_authorized() -> bool:
    """Server-side approval gate for actions that spend the GitHub token."""
    secret = os.getenv("SUPPORT_HANDOFF_SECRET", "").strip()
    supplied = request.headers.get("X-Support-Handoff-Secret", "")
    return bool(secret and hmac.compare_digest(secret, supplied))


def _handoff_forbidden_response():
    return jsonify({
        "error": "GitHub handoff는 관리자 승인키가 필요합니다.",
        "code": "HANDOFF_APPROVAL_REQUIRED",
        "github": github_config_status(),
    }), 403


@support_bp.route("/api/support/chat", methods=["POST"])
@limiter.limit("20/minute;200/day")
def support_chat():
    data = _payload()
    try:
        result = handle_support_chat(
            message=data.get("message", ""),
            route=data.get("route") or request.headers.get("X-Insight-Route", ""),
            viewport=data.get("viewport") if isinstance(data.get("viewport"), dict) else None,
            user_agent=data.get("user_agent") or request.headers.get("User-Agent", ""),
            console_errors=data.get("console_errors") if isinstance(data.get("console_errors"), list) else [],
            screenshot_url=data.get("screenshot_url") or "",
            mode=data.get("mode") or "auto",
            user_id=_current_user_id(),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@support_bp.route("/api/support/tickets", methods=["GET"])
def list_support_tickets():
    limit = min(request.args.get("limit", 50, type=int), 100)
    status = request.args.get("status") or None
    tickets = get_feedback_store().list_tickets(
        user_id=_current_user_id(), limit=limit, status=status
    )
    return jsonify({"tickets": tickets, "github": github_config_status()})


@support_bp.route("/api/support/tickets/<ticket_id>", methods=["GET"])
def get_support_ticket(ticket_id: str):
    try:
        ticket = get_feedback_store().get_ticket(ticket_id)
    except KeyError:
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if not _owns(ticket):
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    return jsonify({"ticket": ticket, "github": github_config_status()})


@support_bp.route("/api/support/tickets/<ticket_id>/create-github-issue", methods=["POST"])
@limiter.limit("5/minute;30/day")
def create_support_github_issue(ticket_id: str):
    if not _handoff_authorized():
        return _handoff_forbidden_response()
    store = get_feedback_store()
    try:
        ticket = store.get_ticket(ticket_id)
    except KeyError:
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if not _owns(ticket):
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if ticket.get("github_issue_url"):
        return jsonify({"ticket": ticket, "issue": {"html_url": ticket["github_issue_url"], "number": ticket.get("github_issue_number")}})
    try:
        return jsonify(create_github_issue(ticket_id, store=store)), 201
    except GitHubHandoffError as exc:
        return jsonify({"error": str(exc), "github": github_config_status()}), 400


@support_bp.route("/api/support/tickets/<ticket_id>/create-draft-pr", methods=["POST"])
@limiter.limit("5/minute;20/day")
def create_support_draft_pr(ticket_id: str):
    if not _handoff_authorized():
        return _handoff_forbidden_response()
    store = get_feedback_store()
    try:
        ticket = store.get_ticket(ticket_id)
    except KeyError:
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if not _owns(ticket):
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if ticket.get("github_pr_url"):
        return jsonify({"ticket": ticket, "pull_request": {"html_url": ticket["github_pr_url"], "number": ticket.get("github_pr_number")}})
    try:
        return jsonify(create_draft_pr(ticket_id, store=store)), 201
    except GitHubHandoffError as exc:
        return jsonify({"error": str(exc), "github": github_config_status()}), 400
