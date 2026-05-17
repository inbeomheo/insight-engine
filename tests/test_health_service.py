"""Health endpoint service tests."""

from services.ops.health_service import build_health_payload, detect_runtime_environment


def test_detect_runtime_environment_uses_development_when_flask_env_is_development():
    assert detect_runtime_environment("development", debug=False) == "development"


def test_detect_runtime_environment_uses_development_when_debug_is_enabled():
    assert detect_runtime_environment("production", debug=True) == "development"


def test_detect_runtime_environment_defaults_to_production():
    assert detect_runtime_environment(None, debug=False) == "production"


def test_build_health_payload_includes_counters_and_memory():
    payload = build_health_payload(
        environment="production",
        request_count=12,
        error_count=3,
        error_rate=0.25,
        memory_usage_mb=128.5,
    )

    assert payload == {
        "status": "healthy",
        "environment": "production",
        "api_version": "v2.0",
        "request_count": 12,
        "error_count": 3,
        "error_rate": 0.25,
        "memory_usage_mb": 128.5,
    }
