"""Production maintenance automation contracts."""
import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = ROOT / '.github' / 'dependabot.yml'
DOCKERIGNORE = ROOT / '.dockerignore'
VALIDATOR = ROOT / 'scripts' / 'validate_maintenance_config.py'


def _dependabot():
    return yaml.safe_load(DEPENDABOT.read_text(encoding='utf-8'))


def test_maintenance_config_validator_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'maintenance config validation passed' in result.stdout


def test_dependabot_covers_runtime_dependency_manifests():
    config = _dependabot()
    updates = {
        (update['package-ecosystem'], update['directory'])
        for update in config['updates']
    }

    assert config['version'] == 2
    assert {
        ('github-actions', '/'),
        ('npm', '/'),
        ('npm', '/frontend'),
        ('npm', '/tests/e2e'),
        ('pip', '/'),
        ('docker', '/'),
        ('docker', '/k8s'),
        ('docker-compose', '/'),
    }.issubset(updates)


def test_dependabot_targets_have_matching_manifest_files():
    manifest_map = {
        ('github-actions', '/'): [ROOT / '.github' / 'workflows' / 'ci.yml'],
        ('npm', '/'): [ROOT / 'package.json'],
        ('npm', '/frontend'): [ROOT / 'frontend' / 'package.json'],
        ('npm', '/tests/e2e'): [ROOT / 'tests' / 'e2e' / 'package.json'],
        ('pip', '/'): [ROOT / 'requirements.txt', ROOT / 'requirements-ci.txt'],
        ('docker', '/'): [ROOT / 'Dockerfile'],
        ('docker', '/k8s'): [ROOT / 'k8s' / 'deployment.yaml'],
        ('docker-compose', '/'): [ROOT / 'docker-compose.yml', ROOT / 'docker-compose.deploy.yml'],
    }

    for update in _dependabot()['updates']:
        key = (update['package-ecosystem'], update['directory'])
        assert key in manifest_map
        assert all(path.exists() for path in manifest_map[key])


def test_dependabot_schedule_is_weekly_and_staggered():
    times = []
    for update in _dependabot()['updates']:
        schedule = update['schedule']
        times.append(schedule['time'])
        assert schedule['interval'] == 'weekly'
        assert schedule['day'] == 'monday'
        assert schedule['timezone'] == 'Etc/UTC'
        assert update['open-pull-requests-limit'] >= 3
        assert 'dependencies' in update['labels']

    assert len(times) == len(set(times))


def test_dockerignore_keeps_sensitive_files_out_and_frontend_lockfile_in():
    patterns = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }

    assert '.env' in patterns
    assert '.env.*' in patterns
    assert '!.env.example' in patterns
    assert '.git' in patterns
    assert 'tests/' in patterns
    assert 'test-results/' in patterns
    assert 'tests/test-results/' in patterns
    assert 'tests/e2e/test-results/' in patterns
    assert 'playwright-report/' in patterns
    assert '.playwright-mcp/' in patterns
    assert 'node_modules/' in patterns
    assert '**/node_modules/' in patterns
    assert '/data/' in patterns
    assert '*.jsonl' in patterns
    assert 'publish_queue.json' in patterns
    assert '.agent/' in patterns
    assert '.agents/' in patterns
    assert '.claude/' in patterns
    assert '.cmux/' in patterns
    assert '.understand-anything/' in patterns
    assert '.worktrees/' in patterns
    assert 'downloads/' in patterns
    assert 'skills-lock.json' in patterns
    assert 'data/chroma_db/' not in patterns
    assert '/package-lock.json' in patterns
    assert 'package-lock.json' not in patterns
    assert '**/package-lock.json' not in patterns
    assert 'frontend/package-lock.json' not in patterns


def test_deploy_compose_bounds_docker_json_logs():
    compose = yaml.safe_load((ROOT / 'docker-compose.deploy.yml').read_text(encoding='utf-8'))

    for service_name, service in compose['services'].items():
        assert service['logging']['driver'] == 'json-file', service_name
        assert service['logging']['options']['max-size'] == '${DOCKER_LOG_MAX_SIZE:-10m}'
        assert service['logging']['options']['max-file'] == '${DOCKER_LOG_MAX_FILE:-5}'


def test_package_json_exposes_maintenance_validation_gate():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    verify_release = (ROOT / 'scripts' / 'verify_release.sh').read_text(encoding='utf-8')

    assert package_json['scripts']['verify:maintenance'] == 'python3 scripts/validate_maintenance_config.py'
    assert 'npm run verify:maintenance' in verify_release
