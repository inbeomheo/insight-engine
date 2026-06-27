"""Python dependency vulnerability audit contract."""
import json
import subprocess
from datetime import date
from pathlib import Path

from scripts import audit_python_dependencies


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'requirements.txt'
CI_REQUIREMENTS = ROOT / 'requirements-ci.txt'
IGNORE_FILE = ROOT / 'security' / 'pip-audit-ignore.json'


def test_python_audit_requirements_are_separate_from_runtime_requirements():
    runtime = REQUIREMENTS.read_text(encoding='utf-8')
    ci = CI_REQUIREMENTS.read_text(encoding='utf-8')

    assert 'pip-audit' not in runtime
    assert 'pip-audit==2.10.1' in ci


def test_python_audit_policy_has_expiring_chromadb_exception():
    payload = json.loads(IGNORE_FILE.read_text(encoding='utf-8'))
    ignored = payload['ignored_vulnerabilities']

    assert audit_python_dependencies.validate_ignored_vulnerabilities(today=date(2026, 6, 27)) == []
    chromadb_exception = next(item for item in ignored if item['id'] == 'CVE-2026-45829')
    assert chromadb_exception['package'] == 'chromadb'
    assert chromadb_exception['expires'] == '2026-07-27'
    assert 'no fixed ChromaDB release' in chromadb_exception['reason']


def test_python_audit_command_uses_requirements_and_tracked_ignores():
    command = audit_python_dependencies._audit_command('python3')

    assert command[:5] == ['python3', '-m', 'pip_audit', '-r', str(REQUIREMENTS)]
    assert '--progress-spinner' in command
    assert '--ignore-vuln' in command
    assert 'CVE-2026-45829' in command


def test_python_audit_does_not_install_tooling_by_default(monkeypatch, capsys):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1)

    monkeypatch.delenv('PIP_AUDIT_AUTO_INSTALL', raising=False)
    monkeypatch.setattr(audit_python_dependencies.subprocess, 'run', fake_run)

    assert audit_python_dependencies._ensure_pip_audit('python3') is False
    assert all('install' not in call for call in calls)
    assert 'pip-audit is not installed' in capsys.readouterr().err


def test_python_audit_auto_install_requires_explicit_opt_in(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ['python3', '-m', 'pip_audit']:
            return subprocess.CompletedProcess(args, 1 if len(calls) == 1 else 0)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setenv('PIP_AUDIT_AUTO_INSTALL', '1')
    monkeypatch.setattr(audit_python_dependencies.subprocess, 'run', fake_run)

    assert audit_python_dependencies._ensure_pip_audit('python3') is True
    assert any(call[:4] == ['python3', '-m', 'pip', 'install'] for call in calls)


def test_vulnerable_fixed_versions_are_enforced_in_requirements():
    requirements = REQUIREMENTS.read_text(encoding='utf-8')

    assert 'flask==3.1.3' in requirements
    assert 'python-dotenv==1.2.2' in requirements
    assert 'markdown==3.8.1' in requirements
    assert 'flask==3.0.0' not in requirements
    assert 'python-dotenv==1.0.1' not in requirements
    assert 'markdown==3.5.1' not in requirements


def test_package_json_exposes_python_dependency_audit_gate():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:python-audit'].endswith('scripts/audit_python_dependencies.py\'')
    assert 'npm run verify:python-audit' in package_json['scripts']['verify:audit']
