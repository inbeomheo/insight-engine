"""CLIProxyAPI 설정의 비밀 보호와 CI 실행 검증 계약."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import io
import json
from pathlib import Path
import secrets
import stat
import subprocess
from urllib.error import HTTPError

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load(filename):
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("key", ["", " ", "dummy", "your-api-key-1", "unsafe\nheader"])
def test_runtime_rejects_missing_or_unsafe_key_before_creating_config(monkeypatch, key):
    runtime = _load("cliproxyapi_runtime.py")
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", key)
    monkeypatch.setattr(runtime.tempfile, "mkdtemp", lambda **_kwargs: pytest.fail("설정 파일 생성 금지"))
    with pytest.raises(ValueError):
        runtime.create_config()


def test_runtime_config_is_private_new_and_disables_management(monkeypatch, tmp_path):
    runtime = _load("cliproxyapi_runtime.py")
    key = secrets.token_urlsafe(32) + '\\"'
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", key)
    monkeypatch.setenv("CLIPROXYAPI_AUTH_DIR", str(tmp_path / "auth"))
    monkeypatch.setattr(runtime.tempfile, "tempdir", str(tmp_path))
    first = runtime.create_config()
    second = runtime.create_config()
    assert first != second
    assert first.read_bytes() == second.read_bytes()
    assert stat.S_IMODE(first.stat().st_mode) == 0o600
    assert stat.S_IMODE(first.parent.stat().st_mode) == 0o700
    config = json.loads(first.read_text())
    assert config["api-keys"] == [key]
    assert config["port"] == 8317
    assert config["host"] == "127.0.0.1"
    assert config["remote-management"] == {
        "allow-remote": False, "secret-key": "",
        "disable-control-panel": True, "disable-auto-update-panel": True,
    }
    assert config["ws-auth"] is True
    assert config["plugins"]["enabled"] is False
    assert not (tmp_path / "auth").exists()


def test_config_refuses_overwriting_an_existing_file(monkeypatch, tmp_path):
    runtime = _load("cliproxyapi_runtime.py")
    original = b"existing configuration"
    path = tmp_path / "config.yaml"
    path.write_bytes(original)
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", secrets.token_urlsafe(32))
    monkeypatch.setattr(runtime.tempfile, "mkdtemp", lambda **_kwargs: str(tmp_path))
    with pytest.raises(FileExistsError):
        runtime.create_config()
    assert path.read_bytes() == original


@pytest.mark.parametrize("mode,expected", [("serve", []), ("login", ["-codex-login", "-no-browser"])])
def test_exec_never_passes_key_in_argv(monkeypatch, tmp_path, mode, expected):
    runtime = _load("cliproxyapi_runtime.py")
    monkeypatch.chdir(tmp_path)
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", key)
    monkeypatch.setattr(runtime.tempfile, "tempdir", str(tmp_path))
    calls = []
    monkeypatch.setattr(runtime.os, "execv", lambda *args: calls.append(args))
    assert runtime.main([mode]) == 0
    binary, command = calls[0]
    assert binary == "/usr/local/bin/CLIProxyAPI"
    assert command[1] == "-config"
    assert command[3:] == expected
    assert key not in " ".join(command)
    assert Path.cwd() == Path(command[2]).parent.resolve()


def test_local_binary_and_explicit_container_bind_can_be_configured(monkeypatch, tmp_path):
    runtime = _load("cliproxyapi_runtime.py")
    monkeypatch.chdir(tmp_path)
    binary = str(tmp_path / "CLIProxyAPI")
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("CLIPROXYAPI_BINARY", binary)
    monkeypatch.setenv("CLIPROXYAPI_BIND_HOST", "0.0.0.0")
    monkeypatch.setattr(runtime.tempfile, "tempdir", str(tmp_path))
    calls = []
    monkeypatch.setattr(runtime.os, "execv", lambda *args: calls.append(args))
    assert runtime.main(["serve"]) == 0
    assert calls[0][0] == calls[0][1][0] == binary
    assert json.loads(Path(calls[0][1][2]).read_text())["host"] == "0.0.0.0"


@pytest.mark.parametrize("unauthorized_status", [200, 401, 403, 500])
def test_healthcheck_requires_authenticated_models_and_rejects_anonymous(monkeypatch, unauthorized_status):
    runtime = _load("cliproxyapi_runtime.py")
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", key)
    requests = []

    @contextmanager
    def fake_urlopen(request, *, timeout):
        requests.append(request)
        assert timeout == 3
        if isinstance(request, str):
            if unauthorized_status != 200:
                raise HTTPError(request, unauthorized_status, "denied", {}, None)
        else:
            assert request.headers["Authorization"] == f"Bearer {key}"
        response = io.BytesIO(b'{"data": []}')
        response.status = 200
        yield response

    monkeypatch.setattr(runtime, "urlopen", fake_urlopen)
    if unauthorized_status == 401:
        runtime.healthcheck()
    else:
        with pytest.raises(ValueError):
            runtime.healthcheck()
    assert len(requests) == 2


def test_docker_smoke_uses_ephemeral_env_key_and_no_existing_volume(monkeypatch):
    smoke = _load("cliproxyapi_docker_smoke.py")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        stdout = "-codex-login -no-browser -config" if "-help" in command else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(smoke, "_run", fake_run)
    assert smoke.main() == 0
    run, options = calls[0]
    key = options["env"]["CLIPROXYAPI_API_KEY"]
    assert key and key not in " ".join(run)
    assert run[run.index("--env") + 1] == "CLIPROXYAPI_API_KEY"
    assert run[run.index("--network") + 1] == "none"
    assert "--volume" not in run and "--mount" not in run
    assert "--read-only" in run
    assert any("healthcheck" in command for command, _ in calls)
    assert calls[-1][0] == ["docker", "rm", "--force", run[run.index("--name") + 1]]


def test_docker_smoke_redacts_key_from_failure_logs(monkeypatch, capsys):
    smoke = _load("cliproxyapi_docker_smoke.py")
    key = secrets.token_urlsafe(32)
    monkeypatch.setattr(smoke.secrets, "token_urlsafe", lambda _size: key)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "-help" in command:
            return subprocess.CompletedProcess(command, 0, stdout="missing options", stderr="")
        stdout = f"example secret {key}" if "logs" in command else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(smoke, "_run", fake_run)
    assert smoke.main() == 1
    assert key not in capsys.readouterr().err
    assert calls[-1][:3] == ["docker", "rm", "--force"]
