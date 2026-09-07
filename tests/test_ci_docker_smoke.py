"""Regression tests for the CI full-stack Docker smoke runner."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci_docker_smoke.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ci_docker_smoke_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ready_payload() -> dict[str, object]:
    return {
        "status": "ready",
        "dependencies": {
            "chatmock": "skipped",
            "redis": "skipped",
            "supabase_schema": {
                "ready": True,
                "reason": "skipped_outside_production",
            },
        },
    }


def test_wait_for_json_retries_connection_reset(monkeypatch):
    module = _load_module()
    attempts = iter([
        ConnectionResetError("connection reset during nginx startup"),
        (200, b'{"status":"healthy"}'),
    ])

    def fake_fetch(*_args, **_kwargs):
        result = next(attempts)
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(module, "_is_running", lambda _name: True)
    monkeypatch.setattr(module, "_fetch", fake_fetch)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    assert module._wait_for_json(
        "/health",
        host_port=18080,
        container_name="smoke-container",
        timeout_seconds=10,
    ) == {"status": "healthy"}


def test_wait_for_frontend_retries_connection_reset(monkeypatch):
    module = _load_module()
    attempts = iter([
        ConnectionResetError("connection reset during nginx startup"),
        (200, b"ready"),
    ])

    def fake_fetch(*_args, **_kwargs):
        result = next(attempts)
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(module, "_is_running", lambda _name: True)
    monkeypatch.setattr(module, "_fetch", fake_fetch)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    module._wait_for_frontend(
        host_port=18080,
        container_name="smoke-container",
        timeout_seconds=10,
    )


def test_main_loads_and_runs_full_stack_image_with_auth_disabled(monkeypatch):
    module = _load_module()
    commands: list[list[str]] = []
    requested_paths: list[str] = []
    frontend_checks: list[int] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="true\n", stderr="")

    def fake_wait_for_json(path, **_kwargs):
        requested_paths.append(path)
        return {"status": "healthy"} if path == "/health" else _ready_payload()

    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_wait_for_json", fake_wait_for_json)
    monkeypatch.setattr(
        module,
        "_wait_for_frontend",
        lambda **kwargs: frontend_checks.append(kwargs["host_port"]),
    )

    assert module.main() == 0
    assert commands[0] == ["docker", "image", "inspect", "insight-engine:ci"]

    docker_run = next(command for command in commands if command[:2] == ["docker", "run"])
    assert "insight-engine-ci-smoke-123-2" in docker_run
    assert "127.0.0.1:18080:8080" in docker_run
    for environment in (
        "FLASK_ENV=testing",
        "RATE_LIMIT_ENABLED=false",
        "SCHEDULER_ENABLED=false",
        "SUPABASE_URL=",
        "SUPABASE_PUBLISHABLE_KEY=",
        "SUPABASE_SECRET_KEY=",
        "SUPABASE_ANON_KEY=",
        "SUPABASE_SERVICE_ROLE_KEY=",
    ):
        assert environment in docker_run

    assert requested_paths == ["/health", "/ready"]
    assert frontend_checks == [18080]
    assert commands[-1][:3] == ["docker", "rm", "--force"]


def test_main_logs_and_removes_container_when_testing_ready_contract_fails(
    monkeypatch,
):
    module = _load_module()
    commands: list[list[str]] = []
    logs: list[str] = []
    responses = iter([
        {"status": "healthy"},
        {
            "status": "ready",
            "dependencies": {
                "chatmock": "skipped",
                "redis": "skipped",
                "supabase_schema": {"ready": False},
            },
        },
    ])

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="true\n", stderr="")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_wait_for_json", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(module, "_print_logs", logs.append)

    with pytest.raises(RuntimeError, match="unexpected testing /ready response"):
        module.main()

    assert logs == [module._container_name()]
    assert commands[-1][:3] == ["docker", "rm", "--force"]


def test_production_cache_probe_runs_as_the_application_uid(monkeypatch):
    module = _load_module()
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module, "_run", fake_run)

    module._assert_content_cache_writable("backend-container")

    assert commands == [[
        "docker",
        "exec",
        "--user",
        "10001:10001",
        "backend-container",
        "python",
        "-c",
        commands[0][-1],
    ]]
    assert "/app/persist/cache/content" in commands[0][-1]
    assert "_save_cache" in commands[0][-1]
    assert "_load_cache" in commands[0][-1]
    assert "clear_cache" in commands[0][-1]


def test_production_cache_probe_surfaces_write_failures(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "_run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="permission denied",
        ),
    )

    with pytest.raises(RuntimeError, match="permission denied"):
        module._assert_content_cache_writable("backend-container")
