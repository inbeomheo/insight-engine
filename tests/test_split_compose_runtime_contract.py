"""Split Compose role startup and shutdown contract regression tests."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"{path.stem}_split_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("compose_name", ["docker-compose.yml", "docker-compose.deploy.yml"])
def test_split_app_services_use_absolute_supervisor_and_long_stop_grace(compose_name):
    compose = yaml.safe_load((ROOT / compose_name).read_text(encoding="utf-8"))

    for role in ("backend", "frontend"):
        service = compose["services"][role]
        assert service["command"] == [
            "tini",
            "--",
            "python",
            "/app/scripts/run_full_stack.py",
            role,
        ]
        assert service["stop_grace_period"] == "630s"


def test_public_proxies_keep_connections_during_the_long_application_drain():
    standard = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    deploy = yaml.safe_load(
        (ROOT / "docker-compose.deploy.yml").read_text(encoding="utf-8")
    )

    nginx = standard["services"]["nginx"]
    assert nginx["stop_signal"] == "SIGQUIT"
    assert nginx["stop_grace_period"] == "630s"
    assert deploy["services"]["edge"]["stop_grace_period"] == "630s"


def test_frontend_role_drops_privileges_without_touching_persistent_storage(
    tmp_path, monkeypatch,
):
    module = _load_script("run_full_stack.py")
    state = {"euid": 0}
    events: list[str] = []
    account = SimpleNamespace(
        pw_name="appuser",
        pw_uid=10001,
        pw_gid=10001,
        pw_dir="/app/persist/data/home",
    )
    persist = tmp_path / "persist"
    module.RUNTIME_ROLE = "frontend"
    monkeypatch.setattr(module, "PERSIST_ROOT", persist)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setattr(module.pwd, "getpwnam", lambda _name: account)
    monkeypatch.setattr(module.os, "geteuid", lambda: state["euid"])
    monkeypatch.setattr(
        module,
        "_require_production_persistent_mount",
        lambda *_args: pytest.fail("frontend must not validate backend storage"),
    )
    monkeypatch.setattr(
        module,
        "recover_interrupted_restore",
        lambda *_args: pytest.fail("frontend must not recover backend storage"),
    )
    monkeypatch.setattr(
        module,
        "_initialize_persistent_storage",
        lambda *_args, **_kwargs: pytest.fail("frontend must not initialize backend storage"),
    )
    monkeypatch.setattr(module.os, "initgroups", lambda *_args: events.append("initgroups"))
    monkeypatch.setattr(module.os, "setgid", lambda _gid: events.append("setgid"))

    def drop_uid(_uid):
        events.append("setuid")
        state["euid"] = account.pw_uid

    monkeypatch.setattr(module.os, "setuid", drop_uid)
    monkeypatch.setattr(module.os, "umask", lambda _mask: events.append("umask"))

    module._prepare_and_drop_privileges()

    assert events == ["initgroups", "setgid", "setuid", "umask"]
    assert state["euid"] == account.pw_uid
    assert not persist.exists()


@pytest.mark.parametrize("role", ["backend", "full-stack"])
def test_backend_owning_roles_keep_production_mount_validation(role, monkeypatch):
    module = _load_script("run_full_stack.py")
    checked: list[Path] = []
    recovered: list[Path] = []
    module.RUNTIME_ROLE = role
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setattr(module.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(module.pwd, "getpwnam", lambda _name: None)
    monkeypatch.setattr(
        module,
        "_require_production_persistent_mount",
        lambda path: checked.append(path),
    )
    monkeypatch.setattr(
        module,
        "recover_interrupted_restore",
        lambda path: recovered.append(path),
    )
    monkeypatch.setattr(Path, "mkdir", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.os, "access", lambda *_args: True)
    monkeypatch.setattr(module.os, "umask", lambda _mask: None)

    module._prepare_and_drop_privileges()

    assert checked == [module.PERSIST_ROOT]
    assert recovered == [module.PERSIST_ROOT / "data"]


def test_ci_smoke_runs_both_split_production_roles(monkeypatch):
    module = _load_script("ci_docker_smoke.py")
    commands: list[list[str]] = []
    probes: list[tuple[str, int, str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv("GITHUB_RUN_ID", "321")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "4")
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda _length: "ephemeral-test-value")
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(
        module,
        "_wait_for_container_http",
        lambda path, **kwargs: probes.append(
            (path, kwargs["internal_port"], kwargs["container_name"])
        ),
    )

    module._smoke_split_production_roles(
        "insight-engine:ci",
        backend_host_port=15001,
        frontend_host_port=13000,
        timeout_seconds=180,
    )

    runs = [command for command in commands if command[:2] == ["docker", "run"]]
    assert len(runs) == 2
    backend, frontend = runs
    assert "FLASK_ENV=production" in backend
    assert "type=volume,source=insight-engine-ci-smoke-321-4-backend-persist,target=/app/persist" in backend
    assert backend[-5:] == [
        "tini", "--", "python", "/app/scripts/run_full_stack.py", "backend",
    ]
    assert "--mount" not in frontend
    assert frontend[-5:] == [
        "tini", "--", "python", "/app/scripts/run_full_stack.py", "frontend",
    ]
    assert probes == [
        ("/health", 5001, "insight-engine-ci-smoke-321-4-backend"),
        ("/", 3000, "insight-engine-ci-smoke-321-4-frontend"),
    ]
