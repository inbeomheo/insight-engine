"""Root verification npm script invariants."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _scripts():
    return json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['scripts']


def test_root_verify_scripts_cover_backend_frontend_and_e2e_gates():
    scripts = _scripts()

    assert 'verify:backend' in scripts
    assert 'verify:frontend' in scripts
    assert 'verify:e2e' in scripts
    assert 'verify:all' in scripts

    assert 'pytest tests --ignore=tests/e2e' in scripts['verify:backend']
    assert 'flake8' in scripts['verify:backend']
    assert 'npm run lint' in scripts['verify:frontend']
    assert 'npm test' in scripts['verify:frontend']
    assert 'npx tsc --noEmit' in scripts['verify:frontend']
    assert 'npm run build' in scripts['verify:frontend']
    assert 'scripts/run_e2e_smoke.py' in scripts['verify:e2e']
    assert 'verify:backend' in scripts['verify:all']
    assert 'verify:frontend' in scripts['verify:all']
    assert 'verify:e2e' in scripts['verify:all']


def test_e2e_webserver_uses_cross_platform_python_wrapper():
    config = (ROOT / 'tests' / 'e2e' / 'playwright.config.ts').read_text(
        encoding='utf-8'
    )
    runner = (ROOT / 'scripts' / 'run_python.cjs').read_text(encoding='utf-8')
    smoke_runner = (ROOT / 'scripts' / 'run_e2e_smoke.py').read_text(encoding='utf-8')

    assert "'node scripts/run_python.cjs app.py'" in config
    assert "resolve(root, '.venv', 'Scripts', 'python.exe')" in runner
    assert "'python3.11'" in runner
    assert "commandAvailable('uv')" in runner
    assert "sys.version_info >= (3, 11)" in runner
    assert "node node_modules/next/dist/bin/next dev" in config
    assert "const backendUrl = 'http://127.0.0.1:5001'" in config
    assert 'NEXT_BACKEND_URL: backendUrl' in config
    assert "PLAYWRIGHT_MANAGED_SERVERS === '1'" in config
    assert "FLASK_ENV: 'testing'" in config
    assert "'FLASK_ENV': 'testing'" in smoke_runner
