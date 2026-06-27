"""Audit Python dependencies with pip-audit and tracked temporary exceptions."""
from __future__ import annotations

from datetime import date, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'requirements.txt'
CI_REQUIREMENTS = ROOT / 'requirements-ci.txt'
IGNORE_FILE = ROOT / 'security' / 'pip-audit-ignore.json'
MIN_REASON_LENGTH = 40


def _load_ignored_vulnerabilities(path: Path = IGNORE_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'{path.relative_to(ROOT)} is not valid JSON: {exc}') from exc
    ignored = payload.get('ignored_vulnerabilities')
    if not isinstance(ignored, list):
        raise ValueError(f'{path.relative_to(ROOT)} must contain ignored_vulnerabilities list')
    return ignored


def validate_ignored_vulnerabilities(today: date | None = None) -> list[str]:
    """Return validation errors for pip-audit temporary ignore policy."""
    today = today or date.today()
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(_load_ignored_vulnerabilities(), start=1):
        if not isinstance(item, dict):
            errors.append(f'ignore entry #{index} must be an object')
            continue
        vuln_id = str(item.get('id') or '').strip()
        package = str(item.get('package') or '').strip()
        reason = str(item.get('reason') or '').strip()
        expires_raw = str(item.get('expires') or '').strip()
        if not vuln_id:
            errors.append(f'ignore entry #{index} must include id')
        if not package:
            errors.append(f'ignore entry #{index} must include package')
        if len(reason) < MIN_REASON_LENGTH:
            errors.append(f'ignore entry {vuln_id or index} must include a specific mitigation reason')
        try:
            expires = datetime.strptime(expires_raw, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f'ignore entry {vuln_id or index} must include expires as YYYY-MM-DD')
            continue
        if expires < today:
            errors.append(f'ignore entry {vuln_id or index} expired on {expires.isoformat()}')
        if vuln_id in seen:
            errors.append(f'ignore entry {vuln_id} is duplicated')
        seen.add(vuln_id)
    return errors


def _pip_audit_installed(python: str) -> bool:
    probe = subprocess.run(
        [python, '-m', 'pip_audit', '--version'],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return probe.returncode == 0


def _ensure_pip_audit(python: str) -> bool:
    if _pip_audit_installed(python):
        return True
    if os.getenv('PIP_AUDIT_AUTO_INSTALL') != '1':
        print(
            'pip-audit is not installed. Install audit tooling with '
            f'"{python} -m pip install -r {CI_REQUIREMENTS.relative_to(ROOT)}", '
            'or set PIP_AUDIT_AUTO_INSTALL=1 in a writable CI/dev environment.',
            file=sys.stderr,
        )
        return False
    subprocess.run(
        [python, '-m', 'pip', 'install', '-r', str(CI_REQUIREMENTS)],
        cwd=ROOT,
        check=True,
    )
    return _pip_audit_installed(python)


def _audit_command(python: str) -> list[str]:
    command = [
        python,
        '-m',
        'pip_audit',
        '-r',
        str(REQUIREMENTS),
        '--progress-spinner',
        'off',
    ]
    for item in _load_ignored_vulnerabilities():
        vuln_id = str(item.get('id') or '').strip()
        if vuln_id:
            command.extend(['--ignore-vuln', vuln_id])
    return command


def run_python_dependency_audit(python: str | None = None) -> int:
    errors = validate_ignored_vulnerabilities()
    if errors:
        print('Python dependency audit exception policy failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    python = python or os.getenv('PYTHON') or sys.executable
    if not _ensure_pip_audit(python):
        return 1
    return subprocess.run(_audit_command(python), cwd=ROOT, check=False).returncode


def main() -> int:
    return run_python_dependency_audit()


if __name__ == '__main__':
    raise SystemExit(main())
