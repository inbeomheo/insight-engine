"""GitHub handoff for support feedback tickets.

The support assistant never edits application code. It only creates GitHub
Issues or a docs-only Draft PR that a separate worker agent can pick up.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from services.support.feedback_store import FeedbackStore, get_feedback_store


class GitHubHandoffError(RuntimeError):
    pass


def _repo_from_env() -> str:
    repo = os.getenv("SUPPORT_GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY")
    if repo:
        return repo.strip().removeprefix("https://github.com/").removesuffix(".git")
    return ""


def _token_from_env() -> str:
    return os.getenv("SUPPORT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or ""


def _github_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _token_from_env()
    repo = _repo_from_env()
    if not token:
        raise GitHubHandoffError("GitHub token이 설정되지 않았어. SUPPORT_GITHUB_TOKEN 또는 GITHUB_TOKEN을 설정해줘.")
    if not repo or "/" not in repo:
        raise GitHubHandoffError("GitHub repo가 설정되지 않았어. SUPPORT_GITHUB_REPO=owner/repo 형식으로 설정해줘.")

    url = f"https://api.github.com{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "insight-engine-support-assistant",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubHandoffError(f"GitHub API 오류 {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise GitHubHandoffError(f"GitHub API 연결 실패: {exc}") from exc


def github_config_status() -> dict[str, Any]:
    repo = _repo_from_env()
    return {
        "configured": bool(repo and _token_from_env()),
        "repo": repo,
        "has_token": bool(_token_from_env()),
        "handoff_enabled": bool(os.getenv("SUPPORT_HANDOFF_SECRET", "").strip()),
    }


def issue_labels(ticket: dict[str, Any]) -> list[str]:
    labels = list(ticket.get("labels") or [])
    priority = ticket.get("priority") or ticket.get("severity", "medium")
    for label in ["support-feedback", "needs-agent", ticket.get("kind"), f"priority:{priority}"]:
        if label and label not in labels:
            labels.append(label)
    if ticket.get("kind") == "feature" and "feature-request" not in labels:
        labels.append("feature-request")
    return [label for label in labels if label]


def _ticket_context(ticket: dict[str, Any]) -> dict[str, Any]:
    metadata = ticket.get("metadata") if isinstance(ticket.get("metadata"), dict) else {}
    context = metadata.get("context") if isinstance(metadata.get("context"), dict) else {}
    return context


def _context_value(ticket: dict[str, Any], key: str, default: str = "unknown") -> str:
    metadata = ticket.get("metadata") if isinstance(ticket.get("metadata"), dict) else {}
    context = _ticket_context(ticket)
    value = ticket.get(key) or context.get(key) or metadata.get(key) or ""
    if value is None:
        value = ""
    value = str(value).strip()
    return value or default


def _classification_confidence(ticket: dict[str, Any]) -> str:
    metadata = ticket.get("metadata") if isinstance(ticket.get("metadata"), dict) else {}
    confidence = metadata.get("classification_confidence")
    if isinstance(confidence, (int, float)):
        return f"{confidence:.2f}"
    return "unknown"


def _fallback_reproduction(ticket: dict[str, Any]) -> str:
    current_url = _context_value(ticket, "current_url")
    route = _context_value(ticket, "route")
    selected_model = _context_value(ticket, "selected_model")
    generation_mode = _context_value(ticket, "generation_mode")
    message = ticket.get("message") or ticket.get("title") or "사용자 메시지가 비어 있습니다."
    return "\n".join([
        f"1. `{current_url}` 화면에서 접수되었습니다.",
        f"2. 라우트 `{route}`, 모델 `{selected_model}`, 생성 모드 `{generation_mode}` 상태를 맞춥니다.",
        f"3. 사용자 보고 내용: {message}",
    ])


def build_issue_body(ticket: dict[str, Any]) -> str:
    viewport = ticket.get("viewport") or {}
    related = ticket.get("related_files") or []
    console_errors = ticket.get("console_errors") or []
    metadata = ticket.get("metadata") or {}
    priority = ticket.get("priority") or metadata.get("priority") or ticket.get("severity", "medium")
    reproduction = metadata.get("reproduction") or _fallback_reproduction(ticket)
    return f"""## 사용자 피드백
{ticket.get('message') or ticket.get('title') or ''}

## 자동 분류
- 유형: `{ticket.get('kind', 'usability')}`
- 우선순위: `{priority}`
- 심각도: `{ticket.get('severity', 'medium')}`
- 분류 신뢰도: `{_classification_confidence(ticket)}`
- 지원 접수 모드: `{_context_value(ticket, 'support_mode', metadata.get('mode') or 'auto')}`

## 화면/실행 컨텍스트
- 현재 URL: `{_context_value(ticket, 'current_url')}`
- Route: `{_context_value(ticket, 'route')}`
- 생성 모델: `{_context_value(ticket, 'selected_model')}`
- 프로바이더: `{_context_value(ticket, 'selected_provider')}`
- 생성 모드: `{_context_value(ticket, 'generation_mode')}`
- 스타일: `{_context_value(ticket, 'selected_style')}`
- 상세도: `{_context_value(ticket, 'detail_level')}`
- 뷰포트: `{viewport.get('width', '?')}x{viewport.get('height', '?')}`
- User-Agent: `{ticket.get('user_agent') or 'unknown'}`

## 재현 정보
{reproduction}

## 기대 동작
{metadata.get('expected') or '사용자가 자연스럽게 기능을 이해하고 불편 없이 사용할 수 있어야 합니다.'}

## 실제 동작
{metadata.get('actual') or ticket.get('message') or ''}

## 첨부 정보
- 스크린샷: {ticket.get('screenshot_url') or '없음'}
- 콘솔 에러:
{_format_bullets(console_errors) or '- 없음'}

## 관련 파일 후보
{_format_bullets(related) or '- 아직 특정하지 못함'}

## 제안 방향
{ticket.get('suggested_fix') or '관련 화면을 확인하고 최소 수정으로 개선합니다.'}

## 작업 에이전트 지시
- 이 이슈 기준으로 새 브랜치를 생성하세요.
- 가능하면 실패 테스트 또는 UI smoke 재현을 먼저 추가하세요.
- 최소 수정으로 구현하세요.
- `npm run lint`, `npx tsc --noEmit`, `npx next build` 또는 관련 `pytest` 결과를 PR 본문에 첨부하세요.
- PR 본문에 `Fixes #<issue-number>`를 포함하세요.

---
_이 이슈는 Insight Engine Support Assistant가 사용자 피드백을 바탕으로 자동 생성했습니다._
""".strip()


def build_issue_payload(ticket: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": ticket.get("title") or "[Feedback] 사용자 피드백",
        "body": build_issue_body(ticket),
        "labels": issue_labels(ticket),
    }


def _format_bullets(items: list[Any]) -> str:
    return "\n".join(f"- `{item}`" if isinstance(item, str) and ("/" in item or item.endswith(".tsx") or item.endswith(".py")) else f"- {item}" for item in items if item)


def create_github_issue(ticket_id: str, store: FeedbackStore | None = None) -> dict[str, Any]:
    store = store or get_feedback_store()
    ticket = store.get_ticket(ticket_id)
    repo = _repo_from_env()
    payload = build_issue_payload(ticket)
    issue = _github_request("POST", f"/repos/{repo}/issues", payload)
    updated = store.update_ticket(ticket_id, {
        "status": "issue_created",
        "github_issue_url": issue.get("html_url", ""),
        "github_issue_number": issue.get("number"),
        "labels": payload["labels"],
    })
    return {"ticket": updated, "issue": issue}


def _safe_branch_slug(ticket: dict[str, Any]) -> str:
    raw = ticket.get("slug") or ticket.get("title") or ticket.get("id") or "feedback"
    slug = re.sub(r"[^0-9A-Za-z_-]+", "-", raw).strip("-").lower()
    return (slug[:48] or "feedback")


def _get_default_branch(repo: str) -> str:
    data = _github_request("GET", f"/repos/{repo}")
    return data.get("default_branch") or "main"


def _get_ref_sha(repo: str, branch: str) -> str:
    ref = _github_request("GET", f"/repos/{repo}/git/ref/heads/{urllib.parse.quote(branch, safe='/')}")
    return ref.get("object", {}).get("sha") or ""


def _create_branch(repo: str, branch: str, sha: str) -> None:
    try:
        _github_request("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    except GitHubHandoffError as exc:
        if "Reference already exists" not in str(exc):
            raise


def _put_file(repo: str, branch: str, path: str, content: str, message: str) -> dict[str, Any]:
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    return _github_request("PUT", f"/repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}", payload)


def create_draft_pr(ticket_id: str, store: FeedbackStore | None = None) -> dict[str, Any]:
    """Create a docs-only draft PR for a ticket.

    This does not edit application code. It adds a feedback spec markdown file so
    a worker agent can continue from an auditable branch/PR.
    """
    store = store or get_feedback_store()
    ticket = store.get_ticket(ticket_id)
    repo = _repo_from_env()
    default_branch = _get_default_branch(repo)
    base_sha = _get_ref_sha(repo, default_branch)
    if not base_sha:
        raise GitHubHandoffError("기본 브랜치 SHA를 확인하지 못했어.")

    branch = f"support/{ticket_id}-{_safe_branch_slug(ticket)}"
    _create_branch(repo, branch, base_sha)
    spec_path = f"docs/feedback/{ticket_id}.md"
    issue_number = ticket.get("github_issue_number")
    body = build_issue_body(ticket)
    spec = f"# Support Feedback Spec: {ticket.get('title')}\n\n{body}\n"
    _put_file(repo, branch, spec_path, spec, f"docs: add feedback spec for {ticket_id}")

    pr_body = (
        "## Summary\n"
        "- Adds a docs-only feedback spec generated by the in-app Support Assistant.\n"
        "- No application code is changed in this handoff PR.\n\n"
        "## Worker Agent Next Steps\n"
        "- Claim the linked issue or this draft PR.\n"
        "- Add failing test/smoke reproduction if possible.\n"
        "- Implement the smallest safe fix.\n"
        "- Update this PR with validation output.\n"
    )
    if issue_number:
        pr_body += f"\nRefs #{issue_number}\n"

    pr = _github_request("POST", f"/repos/{repo}/pulls", {
        "title": f"draft: support feedback {ticket_id}",
        "head": branch,
        "base": default_branch,
        "body": pr_body,
        "draft": True,
    })
    updated = store.update_ticket(ticket_id, {
        "status": "draft_pr_created",
        "github_pr_url": pr.get("html_url", ""),
        "github_pr_number": pr.get("number"),
    })
    return {"ticket": updated, "pull_request": pr, "branch": branch, "spec_path": spec_path}
