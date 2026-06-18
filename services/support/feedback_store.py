"""File-backed feedback ticket store for the in-app support assistant."""
from __future__ import annotations

import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TICKET_STATUSES = {
    "new",
    "answered",
    "triaged",
    "issue_created",
    "draft_pr_created",
    "handed_off",
    "closed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(text: str, fallback: str = "feedback") -> str:
    import re

    slug = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", (text or "").strip()).strip("-")
    return (slug[:80] or fallback).lower()


class FeedbackStore:
    """Small JSON store for user feedback tickets.

    This intentionally mirrors FileJobStore's file-backed style but keeps support
    feedback separate from long-running agent jobs.
    """

    def __init__(self, base_dir: str | os.PathLike[str] | None = None):
        self.base_dir = Path(base_dir or os.getenv("FEEDBACK_STORE_DIR", "./data/feedback"))
        self.items_dir = self.base_dir / "items"
        self.items_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def create_ticket(self, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        now = _now()
        ticket_id = f"fb_{uuid.uuid4().hex[:12]}"
        title = str(payload.get("title") or payload.get("message") or "사용자 피드백").strip()
        ticket = {
            "id": ticket_id,
            "kind": payload.get("kind") or "usability",
            "status": payload.get("status") or "triaged",
            "severity": payload.get("severity") or "medium",
            "title": title[:140],
            "message": str(payload.get("message") or "").strip(),
            "route": payload.get("route") or "",
            "viewport": payload.get("viewport") or None,
            "user_agent": payload.get("user_agent") or "",
            "console_errors": payload.get("console_errors") or [],
            "screenshot_url": payload.get("screenshot_url") or "",
            "related_files": payload.get("related_files") or [],
            "suggested_fix": payload.get("suggested_fix") or "",
            "github_issue_url": payload.get("github_issue_url") or "",
            "github_issue_number": payload.get("github_issue_number") or None,
            "github_pr_url": payload.get("github_pr_url") or "",
            "github_pr_number": payload.get("github_pr_number") or None,
            "labels": payload.get("labels") or [],
            "metadata": payload.get("metadata") or {},
            "user_id": user_id or "anonymous",
            "slug": _safe_slug(title),
            "created_at": now,
            "updated_at": now,
        }
        if ticket["status"] not in TICKET_STATUSES:
            ticket["status"] = "triaged"
        with self._lock:
            self._write_ticket(ticket)
        return deepcopy(ticket)

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        path = self._ticket_path(ticket_id)
        if not path.exists():
            raise KeyError(f"ticket not found: {ticket_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_tickets(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in self.items_dir.glob("*.json"):
            try:
                ticket = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if user_id is not None and ticket.get("user_id") != user_id:
                continue
            items.append(ticket)
        items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return items[: max(1, min(limit, 100))]

    def update_ticket(self, ticket_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            ticket = self.get_ticket(ticket_id)
            clean_updates = {k: deepcopy(v) for k, v in updates.items() if k not in {"id", "created_at", "user_id"}}
            if clean_updates.get("status") and clean_updates["status"] not in TICKET_STATUSES:
                clean_updates.pop("status")
            ticket.update(clean_updates)
            ticket["updated_at"] = _now()
            self._write_ticket(ticket)
            return deepcopy(ticket)

    def _ticket_path(self, ticket_id: str) -> Path:
        return self.items_dir / f"{ticket_id}.json"

    def _write_ticket(self, ticket: dict[str, Any]) -> None:
        path = self._ticket_path(ticket["id"])
        tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


_default_store = FeedbackStore()


def get_feedback_store() -> FeedbackStore:
    return _default_store
