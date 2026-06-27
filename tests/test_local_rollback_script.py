"""Local Docker deployment rollback contract."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLLBACK_SCRIPT = ROOT / 'scripts' / 'rollback_local.sh'
DEPLOY_SCRIPT = ROOT / 'scripts' / 'deploy_local.sh'


def _write_stubs(tmp_path: Path, *, has_rollback_image: bool = True, has_release_labels: bool = True) -> Path:
    log_path = tmp_path / 'commands.log'
    docker_stub = tmp_path / 'docker'
    docker_stub.write_text(
        f"""#!/usr/bin/env bash
printf 'docker %s\\n' "$*" >> "$COMMAND_STUB_LOG"
if [ "$1" = "image" ] && [ "$2" = "inspect" ] && [ "$3" = "--format" ]; then
  {"exit 1" if not has_rollback_image else ""}
  {"case \"$4\" in *version*) printf 'v2.0\\n' ;; *revision*) printf 'abcdef1234567890abcdef1234567890abcdef12\\n' ;; *created*) printf '2026-06-27T08:00:00Z\\n' ;; *) printf '<no value>\\n' ;; esac" if has_release_labels else "printf '<no value>\\n'"}
  exit 0
fi
if [ "$1" = "image" ] && [ "$2" = "inspect" ]; then
  {"exit 0" if has_rollback_image else "exit 1"}
fi
if [ "$1" = "compose" ]; then
  exit 0
fi
exit 0
""",
        encoding='utf-8',
    )
    docker_stub.chmod(0o755)

    npm_stub = tmp_path / 'npm'
    npm_stub.write_text(
        """#!/usr/bin/env bash
printf 'npm %s INSIGHT_EXPECTED_RELEASE=%s INSIGHT_EXPECTED_GIT_SHA=%s\\n' "$*" "${INSIGHT_EXPECTED_RELEASE:-}" "${INSIGHT_EXPECTED_GIT_SHA:-}" >> "$COMMAND_STUB_LOG"
exit 0
""",
        encoding='utf-8',
    )
    npm_stub.chmod(0o755)
    return log_path


def _run_rollback(
    tmp_path: Path,
    *,
    has_rollback_image: bool = True,
    has_release_labels: bool = True,
    env: dict[str, str] | None = None,
):
    log_path = _write_stubs(
        tmp_path,
        has_rollback_image=has_rollback_image,
        has_release_labels=has_release_labels,
    )
    merged_env = os.environ.copy()
    merged_env.update({
        'PATH': f'{tmp_path}{os.pathsep}{merged_env["PATH"]}',
        'COMMAND_STUB_LOG': str(log_path),
    })
    if env:
        merged_env.update(env)

    result = subprocess.run(
        ['bash', str(ROLLBACK_SCRIPT)],
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )
    calls = log_path.read_text(encoding='utf-8').splitlines() if log_path.exists() else []
    return result, calls


def test_package_json_exposes_local_rollback_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['ops:rollback-local'] == 'bash scripts/rollback_local.sh'


def test_deploy_script_preserves_previous_image_and_auto_rolls_back_on_failure():
    deploy_script = DEPLOY_SCRIPT.read_text(encoding='utf-8')

    assert 'ROLLBACK_IMAGE_TAG="${ROLLBACK_IMAGE_TAG:-insight-engine:rollback}"' in deploy_script
    assert 'docker tag "$previous_image_id" "$ROLLBACK_IMAGE_TAG"' in deploy_script
    assert 'trap rollback_on_deploy_error ERR' in deploy_script
    assert 'ROLLBACK_SKIP_CLEANUP=1 bash scripts/rollback_local.sh' in deploy_script
    assert 'trap - ERR' in deploy_script


def test_rollback_script_retags_previous_image_and_recreates_services_without_build(tmp_path):
    result, calls = _run_rollback(tmp_path, env={'ROLLBACK_SKIP_CLEANUP': 'true'})

    assert result.returncode == 0
    assert 'docker image inspect insight-engine:rollback' in calls
    assert any('org.opencontainers.image.revision' in call for call in calls)
    assert 'release=' in result.stdout
    assert 'git_sha=' in result.stdout
    assert 'build_time=' in result.stdout
    assert 'docker tag insight-engine:rollback insight-engine:local' in calls
    assert (
        'docker compose -f docker-compose.deploy.yml up -d --no-build --force-recreate '
        '--wait --wait-timeout 180 --remove-orphans backend frontend'
    ) in calls
    assert (
        'docker compose -f docker-compose.deploy.yml up -d --force-recreate --no-deps '
        '--wait --wait-timeout 60 --remove-orphans edge'
    ) in calls
    monitor_calls = [call for call in calls if call.startswith('npm run ops:monitor ')]
    assert len(monitor_calls) == 1
    assert 'INSIGHT_EXPECTED_RELEASE=abcdef1234567890abcdef1234567890abcdef12' in monitor_calls[0]
    assert 'INSIGHT_EXPECTED_GIT_SHA=abcdef1234567890abcdef1234567890abcdef12' in monitor_calls[0]
    assert 'npm run docker:cleanup' not in calls


def test_rollback_script_runs_cleanup_by_default(tmp_path):
    result, calls = _run_rollback(tmp_path)

    assert result.returncode == 0
    assert any(call.startswith('npm run docker:cleanup ') for call in calls)


def test_rollback_script_fails_when_no_rollback_image_exists(tmp_path):
    result, calls = _run_rollback(tmp_path, has_rollback_image=False)

    assert result.returncode == 2
    assert 'rollback image insight-engine:rollback not found' in result.stderr
    assert not any('--force-recreate' in call for call in calls)


def test_rollback_script_requires_usable_release_metadata(tmp_path):
    result, calls = _run_rollback(tmp_path, has_release_labels=False)

    assert result.returncode == 2
    assert 'has no usable org.opencontainers.image.version label' in result.stderr
    assert not any('--force-recreate' in call for call in calls)
