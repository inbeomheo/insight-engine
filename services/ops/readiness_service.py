"""Readiness probe dependency checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
from typing import Any


@dataclass(frozen=True)
class ReadinessReport:
    """Computed readiness state and per-dependency check results."""

    ready: bool
    checks: dict[str, str]


def _env_get(environ: Mapping[str, str], name: str, default: str = "") -> str:
    value = environ.get(name, default)
    return "" if value is None else str(value)


def _is_truthy(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def build_readiness_report(
    *,
    environ: Mapping[str, str] | None = None,
    redis_from_url: Callable[..., Any] | None = None,
    is_supabase_enabled: Callable[[], bool] | None = None,
    is_scheduler_running: Callable[[], bool] | None = None,
    path_is_dir: Callable[[str], bool] | None = None,
    path_is_writable: Callable[[str], bool] | None = None,
) -> ReadinessReport:
    """Check runtime dependencies for the `/ready` probe."""
    env = os.environ if environ is None else environ
    checks: dict[str, str] = {}
    ready = True

    redis_url = _env_get(env, "REDIS_URL").strip()
    if redis_url:
        try:
            if redis_from_url is None:
                import redis as _redis

                redis_from_url = _redis.from_url
            client = redis_from_url(
                redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"fail: {type(exc).__name__}"
            ready = False
    else:
        checks["redis"] = "skipped (REDIS_URL unset)"

    try:
        if is_supabase_enabled is None:
            from services.data.supabase_service import is_supabase_enabled as _is_supabase_enabled

            is_supabase_enabled = _is_supabase_enabled
        checks["supabase"] = "ok" if is_supabase_enabled() else "disabled"
    except Exception as exc:
        checks["supabase"] = f"fail: {type(exc).__name__}"

    if _is_truthy(_env_get(env, "RAG_ENABLED", "false")):
        chroma_path = _env_get(env, "CHROMA_DB_PATH", "./data/chroma_db")
        is_dir = path_is_dir or os.path.isdir
        is_writable = path_is_writable or (lambda path: os.access(path, os.W_OK))
        if is_dir(chroma_path) and is_writable(chroma_path):
            checks["chroma_db"] = "ok"
        else:
            checks["chroma_db"] = f"fail: path not writable ({chroma_path})"
            ready = False
    else:
        checks["chroma_db"] = "disabled"

    if _is_truthy(_env_get(env, "RUN_SCHEDULER")):
        try:
            if is_scheduler_running is None:
                from services.data.scheduler_worker import is_scheduler_running as _is_scheduler_running

                is_scheduler_running = _is_scheduler_running
            checks["scheduler"] = "running" if is_scheduler_running() else "stopped"
            if checks["scheduler"] == "stopped":
                ready = False
        except (ImportError, AttributeError):
            checks["scheduler"] = "unknown"

    return ReadinessReport(ready=ready, checks=checks)
