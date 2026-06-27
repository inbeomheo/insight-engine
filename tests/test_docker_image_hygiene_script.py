"""Docker image hygiene script contract."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'verify_docker_image_hygiene.sh'


def _run_hygiene(tmp_path: Path, *, revision: str = 'abcdef1234567890abcdef1234567890abcdef12', env=None):
    log_path = tmp_path / 'docker.log'
    docker_stub = tmp_path / 'docker'
    docker_stub.write_text(
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$DOCKER_STUB_LOG"
if [ "$1" = "image" ] && [ "$2" = "inspect" ] && [ "$3" = "--format" ]; then
  case "$4" in
    *version*) printf 'v2.0\\n' ;;
    *revision*) printf '{revision}\\n' ;;
    *created*) printf '2026-06-27T08:00:00Z\\n' ;;
    *) printf '<no value>\\n' ;;
  esac
  exit 0
fi
if [ "$1" = "image" ] && [ "$2" = "inspect" ]; then
  exit 0
fi
if [ "$1" = "run" ]; then
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
        ['bash', str(SCRIPT), 'insight-engine:test'],
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )
    calls = log_path.read_text(encoding='utf-8').splitlines() if log_path.exists() else []
    return result, calls


def test_image_hygiene_checks_oci_labels_and_runs_artifact_scan(tmp_path):
    result, calls = _run_hygiene(tmp_path)

    assert result.returncode == 0
    assert 'docker image hygiene passed: insight-engine:test' in result.stdout
    assert any('org.opencontainers.image.version' in call for call in calls)
    assert any('org.opencontainers.image.revision' in call for call in calls)
    assert any('org.opencontainers.image.created' in call for call in calls)
    assert any(call.startswith('run --rm --entrypoint sh insight-engine:test') for call in calls)


def test_image_hygiene_rejects_unexpected_revision_label(tmp_path):
    result, calls = _run_hygiene(
        tmp_path,
        revision='different-sha',
        env={'EXPECTED_GIT_SHA': 'abcdef1234567890abcdef1234567890abcdef12'},
    )

    assert result.returncode == 1
    assert 'does not match expected git SHA' in result.stderr
    assert not any(call.startswith('run --rm --entrypoint sh') for call in calls)
