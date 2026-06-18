"""Support assistant API routes.

These endpoints power the in-app product Q&A / feedback intake assistant.
They do not modify application code; GitHub handoff endpoints only create Issues
or docs-only Draft PRs for separate worker agents.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from services.support.feedback_store import get_feedback_store
from services.support.github_handoff_service import (
    GitHubHandoffError,
    create_draft_pr,
    create_github_issue,
    github_config_status,
)
from services.support.support_agent_service import handle_support_chat
from src.contexts.identity.interface.auth_decorators import require_auth

support_bp = Blueprint("support", __name__)


def _current_user_id() -> str:
    return getattr(g, "user_id", None) or "anonymous"


def _owns(ticket: dict) -> bool:
    return ticket.get("user_id") == _current_user_id()


def _payload() -> dict:
    return request.get_json(silent=True) or {}


@support_bp.route("/api/support/chat", methods=["POST"])
@require_auth
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
@require_auth
def list_support_tickets():
    limit = min(request.args.get("limit", 50, type=int), 100)
    tickets = get_feedback_store().list_tickets(user_id=_current_user_id(), limit=limit)
    return jsonify({"tickets": tickets, "github": github_config_status()})


@support_bp.route("/api/support/tickets/<ticket_id>", methods=["GET"])
@require_auth
def get_support_ticket(ticket_id: str):
    try:
        ticket = get_feedback_store().get_ticket(ticket_id)
    except KeyError:
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    if not _owns(ticket):
        return jsonify({"error": "피드백을 찾을 수 없습니다."}), 404
    return jsonify({"ticket": ticket, "github": github_config_status()})


@support_bp.route("/api/support/tickets/<ticket_id>/create-github-issue", methods=["POST"])
@require_auth
def create_support_github_issue(ticket_id: str):
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
@require_auth
def create_support_draft_pr(ticket_id: str):
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
