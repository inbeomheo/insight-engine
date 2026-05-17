"""Provider credential validation helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import time
from typing import Any


def _default_sanitize(message: str) -> str:
    from utils.responses import sanitize_error_for_client

    return sanitize_error_for_client(message)


def validate_provider_credentials(
    *,
    provider_id: str,
    api_key: str,
    supported_providers: Mapping[str, Mapping[str, Any]],
    http_get: Callable[..., Any] | None = None,
    litellm_completion: Callable[..., Any] | None = None,
    clock: Callable[[], float] | None = None,
    sanitize_error: Callable[[str], str] | None = None,
) -> tuple[dict[str, Any], int]:
    """Validate provider credentials and return response payload plus status."""
    if not provider_id:
        return {"valid": False, "error": "provider_id가 필요합니다."}, 400

    if provider_id not in supported_providers:
        return {"valid": False, "error": f"지원하지 않는 프로바이더: {provider_id}"}, 400

    provider = supported_providers[provider_id]
    models = provider.get("models", [])
    if not models:
        return {"valid": False, "error": "사용 가능한 모델이 없습니다."}, 400

    test_model = models[0]["id"]
    now = clock or time.time
    scrub = sanitize_error or _default_sanitize

    if provider_id == "ollama":
        return _validate_ollama_provider(
            api_key=api_key,
            provider=provider,
            test_model=test_model,
            http_get=http_get,
            clock=now,
            sanitize_error=scrub,
        )

    if not api_key:
        return {"valid": False, "error": "API 키가 필요합니다."}, 400

    return _validate_litellm_provider(
        api_key=api_key,
        provider=provider,
        test_model=test_model,
        litellm_completion=litellm_completion,
        clock=now,
        sanitize_error=scrub,
    )


def _validate_ollama_provider(
    *,
    api_key: str,
    provider: Mapping[str, Any],
    test_model: str,
    http_get: Callable[..., Any] | None,
    clock: Callable[[], float],
    sanitize_error: Callable[[str], str],
) -> tuple[dict[str, Any], int]:
    if http_get is None:
        import requests as http_requests

        http_get = http_requests.get

    base_url = api_key or provider.get("api_base", "http://localhost:11434")
    try:
        started_at = clock()
        response = http_get(f"{base_url}/api/tags", timeout=5)
        latency_ms = round((clock() - started_at) * 1000)
        response.raise_for_status()
        return {"valid": True, "model_tested": test_model, "latency_ms": latency_ms}, 200
    except Exception as exc:
        return {
            "valid": False,
            "model_tested": test_model,
            "error": sanitize_error(str(exc)),
        }, 200


def _validate_litellm_provider(
    *,
    api_key: str,
    provider: Mapping[str, Any],
    test_model: str,
    litellm_completion: Callable[..., Any] | None,
    clock: Callable[[], float],
    sanitize_error: Callable[[str], str],
) -> tuple[dict[str, Any], int]:
    if litellm_completion is None:
        import litellm

        litellm_completion = litellm.completion

    kwargs = {
        "model": test_model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "api_key": api_key,
    }
    if provider.get("api_base"):
        kwargs["api_base"] = provider["api_base"]

    try:
        started_at = clock()
        litellm_completion(**kwargs)
        latency_ms = round((clock() - started_at) * 1000)
        return {"valid": True, "model_tested": test_model, "latency_ms": latency_ms}, 200
    except Exception as exc:
        return {
            "valid": False,
            "model_tested": test_model,
            "error": sanitize_error(str(exc)),
        }, 200
