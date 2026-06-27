"""Rate limiter environment parsing matches production readiness semantics."""

import os
import subprocess
import sys
from pathlib import Path

from tests.test_production_readiness_check import _run_readiness_check, _safe_minimum_env


ROOT = Path(__file__).resolve().parents[1]


def _limiter_enabled_for(value: str) -> bool:
    env = os.environ.copy()
    env['RATE_LIMIT_ENABLED'] = value
    env['REDIS_URL'] = 'memory://'
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'from extensions import limiter; print("1" if limiter.enabled else "0")',
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip() == '1'


def test_rate_limiter_accepts_common_truthy_values():
    for value in ('true', 'TRUE', '1', 'yes', 'on', '', 'unexpected'):
        assert _limiter_enabled_for(value) is True


def test_rate_limiter_disables_common_falsey_values():
    for value in ('false', '0', 'no', 'off'):
        assert _limiter_enabled_for(value) is False


def test_production_readiness_and_runtime_rate_limit_parsing_align():
    result = _run_readiness_check(_safe_minimum_env(RATE_LIMIT_ENABLED='1'))

    assert result.returncode == 0
    assert _limiter_enabled_for('1') is True
