"""Ollama health check service tests."""

from services.integrations.ollama_health_service import check_ollama_health


class _FakeResponse:
    def __init__(self, payload=None, error=None):
        self._payload = payload or {}
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._payload


def test_check_ollama_health_returns_model_names_on_success():
    calls = []

    def http_get(url, timeout):
        calls.append((url, timeout))
        return _FakeResponse({"models": [{"name": "llama3"}, {"name": "mistral"}]})

    payload, status = check_ollama_health(
        base_url="http://localhost:11434",
        http_get=http_get,
    )

    assert status == 200
    assert payload == {
        "ok": True,
        "models": ["llama3", "mistral"],
        "base_url": "http://localhost:11434",
    }
    assert calls == [("http://localhost:11434/api/tags", 5)]


def test_check_ollama_health_sanitizes_failure_message():
    def http_get(url, timeout):
        return _FakeResponse(error=RuntimeError("connection refused: secret"))

    payload, status = check_ollama_health(
        base_url="http://ollama:11434",
        http_get=http_get,
        sanitize_error=lambda message: f"safe:{message}",
    )

    assert status == 503
    assert payload == {
        "ok": False,
        "error": "safe:connection refused: secret",
        "base_url": "http://ollama:11434",
    }
