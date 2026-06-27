"""Tracked-file secret scan guardrails."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check_no_secrets.py'


def _load_secret_scan_module():
    spec = importlib.util.spec_from_file_location('check_no_secrets', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


secret_scan = _load_secret_scan_module()


def test_secret_scan_detects_likely_real_openai_key(tmp_path):
    leaked = tmp_path / 'leaked.py'
    token = 'sk-' + 'rVaLueZ93qP7mN2tQwXy6AbCdEf'
    leaked.write_text(f"OPENAI_API_KEY='{token}'\n", encoding='utf-8')

    findings = secret_scan.scan_file(leaked, tmp_path)

    assert len(findings) == 1
    assert findings[0].kind == 'openai_api_key'
    assert 'realValue' not in findings[0].preview


def test_secret_scan_allows_documented_placeholders(tmp_path):
    example = tmp_path / '.env.example'
    example.write_text(
        '\n'.join([
            'OPENAI_API_KEY=sk-...',
            'ANTHROPIC_API_KEY=sk-ant-...',
            'SUPPORT_TOKEN=sk-proj-testsecret0000000000000000',
            'SLACK_BOT_TOKEN=xoxb-token',
        ]),
        encoding='utf-8',
    )

    assert secret_scan.scan_file(example, tmp_path) == []


def test_secret_scan_skips_generated_test_results(tmp_path):
    generated = tmp_path / 'tests' / 'test-results' / 'results.json'
    generated.parent.mkdir(parents=True)
    generated.write_text('{"OPENAI_API_KEY":"sk-realValue1234567890abcdef"}', encoding='utf-8')

    assert secret_scan.scan_file(generated, tmp_path) == []


def test_secret_scan_cli_reports_json_findings(tmp_path):
    leaked = tmp_path / 'leaked.txt'
    token = 'ghp_' + 'Z9Yx8Wv7Ut6Sr5Qp4On3Ml2Kj1HgF0De'
    leaked.write_text(f'GITHUB_TOKEN={token}\n', encoding='utf-8')

    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--json', str(leaked)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    findings = json.loads(result.stdout)
    assert result.returncode == 1
    assert findings[0]['kind'] == 'github_token'


def test_package_json_exposes_secret_scan_gate():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    verify_release = (ROOT / 'scripts' / 'verify_release.sh').read_text(encoding='utf-8')

    assert package_json['scripts']['verify:secrets'] == 'python3 scripts/check_no_secrets.py'
    assert package_json['scripts']['verify:release'] == 'bash scripts/verify_release.sh'
    assert 'npm run verify:secrets' in verify_release
