"""Executable production readiness checks."""
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_readiness_check(env):
    process_env = os.environ.copy()
    process_env.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'check_production_readiness.py')],
        cwd=ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_readiness_check_passes_with_safe_minimum_production_env():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
    })

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_reports_missing_production_guards_together():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CORS_ORIGINS' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'REDIS_URL' in output


def test_readiness_check_reports_all_required_vars_when_environment_is_empty():
    result = _run_readiness_check({
        'FLASK_ENV': '',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'FLASK_ENV' in output
    assert 'CORS_ORIGINS' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'REDIS_URL' in output


def test_package_json_exposes_verify_production_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:production'] == (
        'python scripts/check_production_readiness.py'
    )
