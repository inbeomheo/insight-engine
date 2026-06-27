"""Docker deploy cleanup script behavior."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'docker_cleanup_after_deploy.sh'


def _run_cleanup(tmp_path: Path, env: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess, list[str]]:
    log_path = tmp_path / 'docker.log'
    docker_stub = tmp_path / 'docker'
    docker_stub.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$DOCKER_STUB_LOG"
if [ "$1" = "container" ] && [ "$2" = "inspect" ]; then
  exit 0
fi
if [ "$1" = "inspect" ]; then
  printf 'sha256:running-image\\n'
  exit 0
fi
exit 0
""",
        encoding='utf-8',
    )
    docker_stub.chmod(0o755)

    merged_env = os.environ.copy()
    merged_env.update({
        'PATH': f'{tmp_path}{os.pathsep}{merged_env["PATH"]}',
        'DOCKER_STUB_LOG': str(log_path),
    })
    if env:
        merged_env.update(env)

    result = subprocess.run(
        ['bash', str(SCRIPT)],
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )
    lines = log_path.read_text(encoding='utf-8').splitlines()
    return result, lines


def test_cleanup_prunes_only_stale_build_cache_by_default(tmp_path):
    result, docker_calls = _run_cleanup(tmp_path)

    assert result.returncode == 0
    assert 'builder prune -f --filter until=168h' in docker_calls


def test_cleanup_honors_custom_build_cache_prune_window(tmp_path):
    result, docker_calls = _run_cleanup(tmp_path, {'BUILD_CACHE_PRUNE_UNTIL': '72h'})

    assert result.returncode == 0
    assert 'builder prune -f --filter until=72h' in docker_calls


def test_cleanup_can_prune_all_build_cache_for_disk_pressure(tmp_path):
    result, docker_calls = _run_cleanup(tmp_path, {'PRUNE_BUILD_CACHE': 'all'})

    assert result.returncode == 0
    assert 'builder prune -f' in docker_calls
    assert not any(call.startswith('builder prune -f --filter') for call in docker_calls)


def test_cleanup_can_skip_build_cache_prune(tmp_path):
    result, docker_calls = _run_cleanup(tmp_path, {'PRUNE_BUILD_CACHE': '0'})

    assert result.returncode == 0
    assert not any(call.startswith('builder prune') for call in docker_calls)


def test_cleanup_rejects_unsupported_build_cache_policy(tmp_path):
    result, docker_calls = _run_cleanup(tmp_path, {'PRUNE_BUILD_CACHE': 'weekly'})

    assert result.returncode == 2
    assert 'unsupported PRUNE_BUILD_CACHE value' in result.stderr
    assert not any(call.startswith('builder prune') for call in docker_calls)
