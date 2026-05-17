"""Ollama health check helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _default_sanitize(message: str) -> str:
    from utils.responses import sanitize_error_for_client

    return sanitize_error_for_client(message)


def check_ollama_health(
    *,
    base_url: str,
    http_get: Callable[..., Any] | None = None,
    sanitize_error: Callable[[str], str] | None = None,
) -> tuple[dict[str, Any], int]:
    """Check Ollama `/api/tags` and return response payload plus status."""
    if http_get is None:
        import requests as http_requests

        http_get = http_requests.get

    scrub = sanitize_error or _default_sanitize

    try:
        response = http_get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [model.get("name", "") for model in data.get("models", [])]
        return {"ok": True, "models": models, "base_url": base_url}, 200
    except Exception as exc:
        return {
            "ok": False,
            "error": scrub(str(exc)),
            "base_url": base_url,
        }, 503
