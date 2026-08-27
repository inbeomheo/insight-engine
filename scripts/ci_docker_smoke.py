"""Boot the built full-stack Docker image and verify its public HTTP surface."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import urlopen


DEFAULT_IMAGE = "insight-engine:ci"
DEFAULT_HOST_PORT = 18080
DEFAULT_BACKEND_HOST_PORT = 15001
DEFAULT_FRONTEND_HOST_PORT = 13000
DEFAULT_TIMEOUT_SECONDS = 180


def _run(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def _container_name() -> str:
    run_id = os.getenv("GITHUB_RUN_ID", str(os.getpid()))
    attempt = os.getenv("GITHUB_RUN_ATTEMPT", "local")
    return f"insight-engine-ci-smoke-{run_id}-{attempt}"


def _split_container_name(role: str) -> str:
    return f"{_container_name()}-{role}"


def _split_backend_volume_name() -> str:
    return f"{_container_name()}-backend-persist"


def _fetch(path: str, *, host_port: int) -> tuple[int, bytes]:
    try:
        with urlopen(
            f"http://127.0.0.1:{host_port}{path}",
            timeout=3,
        ) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def _is_running(container_name: str) -> bool:
    result = _run(
        [
            "docker",
            "inspect",
            "--format={{.State.Running}}",
            container_name,
        ],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _wait_for_json(
    path: str,
    *,
    host_port: int,
    container_name: str,
    timeout_seconds: int,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    last_error: str | None = None

    while time.monotonic() < deadline:
        if not _is_running(container_name):
            raise RuntimeError("Docker smoke container exited before becoming ready")
        try:
            status, body = _fetch(path, host_port=host_port)
            last_status = status
            if status == 200:
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ValueError("response is not a JSON object")
                return payload
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as exc:
            last_error = str(exc)
        time.sleep(2)

    detail = f"last HTTP status={last_status}"
    if last_error:
        detail += f", last error={last_error}"
    raise RuntimeError(f"{path} did not become ready within {timeout_seconds}s ({detail})")


def _wait_for_frontend(
    *,
    host_port: int,
    container_name: str,
    timeout_seconds: int,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    while time.monotonic() < deadline:
        if not _is_running(container_name):
            raise RuntimeError("Docker smoke container exited before frontend startup")
        try:
            last_status, _body = _fetch("/", host_port=host_port)
            if last_status == 200:
                return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError(
        "frontend did not become ready through nginx within "
        f"{timeout_seconds}s (last HTTP status={last_status})"
    )


def _print_logs(container_name: str) -> None:
    print("\n--- Docker smoke container logs ---", file=sys.stderr)
    _run(
        ["docker", "logs", container_name],
        check=False,
    )


def _remove_container(container_name: str) -> None:
    _run(
        ["docker", "rm", "--force", container_name],
        check=False,
        capture_output=True,
    )


def _remove_volume(volume_name: str) -> None:
    _run(
        ["docker", "volume", "rm", "--force", volume_name],
        check=False,
        capture_output=True,
    )


def _wait_for_container_http(
    path: str,
    *,
    internal_port: int,
    container_name: str,
    timeout_seconds: int,
) -> None:
    """Probe from inside a split-role container without host networking races."""
    deadline = time.monotonic() + timeout_seconds
    last_error = "endpoint was not probed"
    probe = (
        "import urllib.request; "
        f"r=urllib.request.urlopen('http://127.0.0.1:{internal_port}{path}', timeout=3); "
        "r.read(1); "
        "raise SystemExit(0 if 200 <= r.status < 400 else 1)"
    )
    while time.monotonic() < deadline:
        if not _is_running(container_name):
            raise RuntimeError(
                f"split {container_name} container exited before {path} became ready"
            )
        result = _run(
            ["docker", "exec", container_name, "python", "-c", probe],
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            return
        last_error = (result.stderr or result.stdout or "probe failed").strip()
        time.sleep(2)
    raise RuntimeError(
        f"split {container_name} {path} did not become ready within "
        f"{timeout_seconds}s ({last_error})"
    )


def _assert_content_cache_writable(container_name: str) -> None:
    """Exercise the production cache as the same unprivileged runtime user."""
    probe = (
        "from services.core import content_service as cache; "
        "video_id='ciCache0001'; "
        "payload={'text':'writable'}; "
        "assert cache.CACHE_DIR == '/app/persist/cache/content', cache.CACHE_DIR; "
        "cache._save_cache(video_id, 'transcript', payload); "
        "assert cache._load_cache(video_id, 'transcript') == payload; "
        "assert cache.clear_cache(video_id) == 1"
    )
    result = _run(
        [
            "docker",
            "exec",
            "--user",
            "10001:10001",
            container_name,
            "python",
            "-c",
            probe,
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "cache probe failed").strip()
        raise RuntimeError(f"production content cache is not writable: {detail}")


def _smoke_split_production_roles(
    image: str,
    *,
    backend_host_port: int,
    frontend_host_port: int,
    timeout_seconds: int,
) -> None:
    """Boot the same image as independent production backend/frontend roles."""
    backend_name = _split_container_name("backend")
    frontend_name = _split_container_name("frontend")
    volume_name = _split_backend_volume_name()
    ephemeral_secret = secrets.token_urlsafe(32)
    for name in (backend_name, frontend_name):
        _remove_container(name)
    _remove_volume(volume_name)

    try:
        _run([
            "docker",
            "run",
            "--detach",
            "--name",
            backend_name,
            "--publish",
            f"127.0.0.1:{backend_host_port}:5001",
            "--mount",
            f"type=volume,source={volume_name},target=/app/persist",
            "--env",
            "FLASK_ENV=production",
            "--env",
            "FLASK_DEBUG=0",
            "--env",
            "BACKEND_BIND_HOST=0.0.0.0",
            "--env",
            "RATE_LIMIT_ENABLED=false",
            "--env",
            "SCHEDULER_ENABLED=false",
            "--env",
            "AUTO_BACKUP_ENABLED=false",
            "--env",
            "PLATFORM_VOLUME_BACKUPS_ENABLED=true",
            "--env",
            "CORS_ORIGINS=https://ci.insight-engine.invalid",
            "--env",
            "PUBLIC_ORIGIN=https://ci.insight-engine.invalid",
            "--env",
            f"METRICS_AUTH_TOKEN={ephemeral_secret}",
            "--env",
            f"ENCRYPTION_SECRET={ephemeral_secret}",
            "--env",
            "SUPABASE_URL=https://ci-runtime-smoke.supabase.co",
            "--env",
            f"SUPABASE_PUBLISHABLE_KEY={ephemeral_secret}",
            "--env",
            f"SUPABASE_SECRET_KEY={ephemeral_secret}",
            image,
            "tini",
            "--",
            "python",
            "/app/scripts/run_full_stack.py",
            "backend",
        ], capture_output=True)
        _wait_for_container_http(
            "/health",
            internal_port=5001,
            container_name=backend_name,
            timeout_seconds=timeout_seconds,
        )
        _assert_content_cache_writable(backend_name)

        # Deliberately omit /app/persist here: the frontend role must still drop
        # privileges but must not require or bootstrap backend-owned storage.
        _run([
            "docker",
            "run",
            "--detach",
            "--name",
            frontend_name,
            "--publish",
            f"127.0.0.1:{frontend_host_port}:3000",
            "--env",
            "NODE_ENV=production",
            "--env",
            "FRONTEND_BIND_HOST=0.0.0.0",
            "--env",
            "NEXT_BACKEND_URL=http://127.0.0.1:5001",
            image,
            "tini",
            "--",
            "python",
            "/app/scripts/run_full_stack.py",
            "frontend",
        ], capture_output=True)
        _wait_for_container_http(
            "/",
            internal_port=3000,
            container_name=frontend_name,
            timeout_seconds=timeout_seconds,
        )
        print(
            f"Docker split production roles passed for {image}: backend and frontend"
        )
    except Exception:
        for name in (backend_name, frontend_name):
            _print_logs(name)
        raise
    finally:
        for name in (frontend_name, backend_name):
            _remove_container(name)
        _remove_volume(volume_name)


def main() -> int:
    image = os.getenv("DOCKER_SMOKE_IMAGE", DEFAULT_IMAGE)
    host_port = int(os.getenv("DOCKER_SMOKE_PORT", str(DEFAULT_HOST_PORT)))
    backend_host_port = int(
        os.getenv("DOCKER_SMOKE_BACKEND_PORT", str(DEFAULT_BACKEND_HOST_PORT))
    )
    frontend_host_port = int(
        os.getenv("DOCKER_SMOKE_FRONTEND_PORT", str(DEFAULT_FRONTEND_HOST_PORT))
    )
    timeout_seconds = int(
        os.getenv("DOCKER_SMOKE_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    )
    container_name = _container_name()

    ports = {
        "DOCKER_SMOKE_PORT": host_port,
        "DOCKER_SMOKE_BACKEND_PORT": backend_host_port,
        "DOCKER_SMOKE_FRONTEND_PORT": frontend_host_port,
    }
    for name, port in ports.items():
        if not 1024 <= port <= 65535:
            raise ValueError(f"{name} must be between 1024 and 65535")
    if len(set(ports.values())) != len(ports):
        raise ValueError("Docker smoke host ports must be distinct")
    if not 10 <= timeout_seconds <= 600:
        raise ValueError("DOCKER_SMOKE_TIMEOUT_SECONDS must be between 10 and 600")

    _run(["docker", "image", "inspect", image], capture_output=True)
    _remove_container(container_name)

    try:
        _run([
            "docker",
            "run",
            "--detach",
            "--name",
            container_name,
            "--publish",
            f"127.0.0.1:{host_port}:8080",
            "--env",
            "PORT=8080",
            "--env",
            "FLASK_ENV=testing",
            "--env",
            "FLASK_DEBUG=0",
            "--env",
            "RATE_LIMIT_ENABLED=false",
            "--env",
            "SCHEDULER_ENABLED=false",
            "--env",
            "AUTO_BACKUP_ENABLED=false",
            "--env",
            "SUPABASE_URL=",
            "--env",
            "SUPABASE_PUBLISHABLE_KEY=",
            "--env",
            "SUPABASE_SECRET_KEY=",
            "--env",
            "SUPABASE_ANON_KEY=",
            "--env",
            "SUPABASE_SERVICE_ROLE_KEY=",
            image,
        ], capture_output=True)

        health = _wait_for_json(
            "/health",
            host_port=host_port,
            container_name=container_name,
            timeout_seconds=timeout_seconds,
        )
        if health.get("status") != "healthy":
            raise RuntimeError(f"unexpected /health response: {health!r}")

        ready = _wait_for_json(
            "/ready",
            host_port=host_port,
            container_name=container_name,
            timeout_seconds=timeout_seconds,
        )
        dependencies = ready.get("dependencies")
        supabase_schema = (
            dependencies.get("supabase_schema")
            if isinstance(dependencies, dict)
            else None
        )
        if (
            ready.get("status") != "ready"
            or not isinstance(dependencies, dict)
            or dependencies.get("chatmock") != "skipped"
            or dependencies.get("redis") != "skipped"
            or not isinstance(supabase_schema, dict)
            or supabase_schema.get("ready") is not True
            or supabase_schema.get("reason") != "skipped_outside_production"
        ):
            raise RuntimeError(f"unexpected testing /ready response: {ready!r}")

        _wait_for_frontend(
            host_port=host_port,
            container_name=container_name,
            timeout_seconds=timeout_seconds,
        )
        print(
            f"Docker smoke passed for {image}: /health, /ready, and / via nginx"
        )
        _smoke_split_production_roles(
            image,
            backend_host_port=backend_host_port,
            frontend_host_port=frontend_host_port,
            timeout_seconds=timeout_seconds,
        )
        return 0
    except Exception:
        _print_logs(container_name)
        raise
    finally:
        _remove_container(container_name)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
        print(f"Docker smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
