"""Provider credential validation service tests."""

from services.core.provider_validation_service import validate_provider_credentials


class _FakeResponse:
    def __init__(self, error=None):
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error


class _Clock:
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0)


def _providers():
    return {
        "ollama": {
            "models": [{"id": "ollama_chat/llama3"}],
            "api_base": "http://localhost:11434",
        },
        "gemini": {
            "models": [{"id": "gemini/gemini-test"}],
        },
        "openrouter": {
            "models": [{"id": "openrouter/model"}],
            "api_base": "https://openrouter.ai/api/v1",
        },
        "empty": {"models": []},
    }


def test_validate_provider_rejects_missing_provider_id():
    payload, status = validate_provider_credentials(
        provider_id="",
        api_key="key",
        supported_providers=_providers(),
    )

    assert status == 400
    assert payload == {"valid": False, "error": "provider_id가 필요합니다."}


def test_validate_provider_rejects_unsupported_provider():
    payload, status = validate_provider_credentials(
        provider_id="unknown",
        api_key="key",
        supported_providers=_providers(),
    )

    assert status == 400
    assert payload == {"valid": False, "error": "지원하지 않는 프로바이더: unknown"}


def test_validate_ollama_provider_uses_base_url_and_reports_latency():
    calls = []

    def http_get(url, timeout):
        calls.append((url, timeout))
        return _FakeResponse()

    payload, status = validate_provider_credentials(
        provider_id="ollama",
        api_key="",
        supported_providers=_providers(),
        http_get=http_get,
        clock=_Clock(10.0, 10.123),
    )

    assert status == 200
    assert payload == {
        "valid": True,
        "model_tested": "ollama_chat/llama3",
        "latency_ms": 123,
    }
    assert calls == [("http://localhost:11434/api/tags", 5)]


def test_validate_litellm_provider_passes_api_base_when_configured():
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)

    payload, status = validate_provider_credentials(
        provider_id="openrouter",
        api_key="secret",
        supported_providers=_providers(),
        litellm_completion=completion,
        clock=_Clock(20.0, 20.05),
    )

    assert status == 200
    assert payload == {
        "valid": True,
        "model_tested": "openrouter/model",
        "latency_ms": 50,
    }
    assert calls == [{
        "model": "openrouter/model",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "api_key": "secret",
        "api_base": "https://openrouter.ai/api/v1",
    }]


def test_validate_litellm_provider_sanitizes_failures():
    def completion(**kwargs):
        raise RuntimeError("bad secret")

    payload, status = validate_provider_credentials(
        provider_id="gemini",
        api_key="secret",
        supported_providers=_providers(),
        litellm_completion=completion,
        sanitize_error=lambda message: f"safe:{message}",
    )

    assert status == 200
    assert payload == {
        "valid": False,
        "model_tested": "gemini/gemini-test",
        "error": "safe:bad secret",
    }
