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
    monkeypatch.setattr(runtime.os, "execve", lambda *args: calls.append(args))
    assert runtime.main([mode]) == 0
    binary, command, environment = calls[0]
    assert binary == "/usr/local/bin/CLIProxyAPI"
    assert command[1] == "-config"
    assert command[3:] == expected
    assert key not in " ".join(command)
    assert environment["CLIPROXYAPI_API_KEY"] == key
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
    monkeypatch.setattr(runtime.os, "execve", lambda *args: calls.append(args))
    assert runtime.main(["serve"]) == 0
    assert calls[0][0] == calls[0][1][0] == binary
    assert json.loads(Path(calls[0][1][2]).read_text())["host"] == "0.0.0.0"


def test_runtime_ignores_inherited_management_and_remote_auth_storage(monkeypatch, tmp_path):
    runtime = _load("cliproxyapi_runtime.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", secrets.token_urlsafe(32))
    blocked = ["MANAGEMENT_PASSWORD", "HOME_JWT", "home_jwt", "DEPLOY",
               "PGSTORE_DSN", "pgstore_dsn", "GITSTORE_GIT_URL", "gitstore_git_token",
               "OBJECTSTORE_ENDPOINT", "objectstore_secret_key"]
    for name in blocked:
        monkeypatch.setenv(name, "test-unrelated-setting")
    monkeypatch.setattr(runtime.tempfile, "tempdir", str(tmp_path))
    calls = []
    monkeypatch.setattr(runtime.os, "execve", lambda *args: calls.append(args))
    runtime.main(["serve"])
    assert all(name not in calls[0][2] for name in blocked)
    # 부모 환경과 파일을 바꾸는 대신 자식 실행 환경만 격리한다.
    assert all(runtime.os.environ[name] == "test-unrelated-setting" for name in blocked)


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
            if not request.endswith("/v1/models"):
                raise HTTPError(request, 404, "disabled", {}, None)
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
    assert len(requests) == (4 if unauthorized_status == 401 else 2)


@pytest.mark.parametrize("management_status", [200, 401, 403])
def test_healthcheck_rejects_enabled_management_even_when_password_protected(monkeypatch, management_status):
    runtime = _load("cliproxyapi_runtime.py")
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", secrets.token_urlsafe(32))

    @contextmanager
    def fake_urlopen(request, *, timeout):
        if isinstance(request, str):
            status = 401 if request.endswith("/v1/models") else management_status
            if status != 200:
                raise HTTPError(request, status, "test", {}, None)
        response = io.BytesIO(b'{"data": []}')
        response.status = 200
        yield response

    monkeypatch.setattr(runtime, "urlopen", fake_urlopen)
    with pytest.raises(ValueError, match="관리 기능"):
        runtime.healthcheck()


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
