"""Webhook test response service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def _default_sanitize(message: str) -> str:
    from utils.responses import sanitize_error_for_client

    return sanitize_error_for_client(message)


def _default_webhook_cls():
    from services.platform.webhook_service import WebhookService

    return WebhookService


def run_webhook_test(
    data: Mapping[str, Any],
    *,
    webhook_cls: type | None = None,
    sanitize_error: Callable[[str], str] | None = None,
    log_error: Callable[..., None] | None = None,
) -> tuple[dict[str, Any], int]:
    """Send a webhook test payload and return response payload plus status."""
    url = str(data.get("url", "")).strip()
    if not url:
        return {"success": False, "error": "웹훅 URL이 필요합니다."}, 400

    webhook_type = webhook_cls or _default_webhook_cls()
    scrub = sanitize_error or _default_sanitize

    try:
        result = webhook_type(url=url, enabled=True).test()
    except Exception as exc:
        if log_error:
            log_error(f"Webhook test failed: {exc}", exc_info=True)
        return {
            "success": False,
            "error": "[서버 오류] 웹훅 테스트 중 문제가 발생했습니다.",
        }, 500

    if not result.get("success"):
        result = {
            **result,
            "error": scrub(result.get("error", "웹훅 테스트 실패")),
        }
        if str(result.get("error", "")).startswith("[서버 오류]"):
            result["error"] = "[서버 오류] 웹훅 테스트에 실패했습니다."

    status_code = 200 if result.get("success") else 400
    return result, status_code
