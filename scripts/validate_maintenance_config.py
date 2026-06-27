"""Validate dependency update automation and Docker build context hygiene."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = ROOT / '.github' / 'dependabot.yml'
DOCKERIGNORE = ROOT / '.dockerignore'
DEPLOY_COMPOSE = ROOT / 'docker-compose.deploy.yml'

REQUIRED_DEPENDABOT_UPDATES = {
    ('github-actions', '/'),
    ('npm', '/'),
    ('npm', '/frontend'),
    ('npm', '/tests/e2e'),
    ('pip', '/'),
    ('docker', '/'),
    ('docker', '/k8s'),
    ('docker-compose', '/'),
}
DEPENDABOT_MANIFEST_GLOBS = {
    ('github-actions', '/'): ['.github/workflows/*.yml', '.github/workflows/*.yaml'],
    ('npm', '/'): ['package.json'],
    ('npm', '/frontend'): ['frontend/package.json'],
    ('npm', '/tests/e2e'): ['tests/e2e/package.json'],
    ('pip', '/'): ['requirements.txt', 'requirements-ci.txt'],
    ('docker', '/'): ['Dockerfile'],
    ('docker', '/k8s'): ['k8s/*.yml', 'k8s/*.yaml'],
    ('docker-compose', '/'): ['docker-compose.yml', 'docker-compose.yaml', 'docker-compose.*.yml', 'docker-compose.*.yaml'],
}
REQUIRED_DOCKERIGNORE_PATTERNS = {
    '.git',
    '.env',
    '.env.*',
    '!.env.example',
    '__pycache__',
    '.venv',
    'node_modules/',
    '**/node_modules/',
    'tests/',
    'test-results/',
    'tests/test-results/',
    'tests/e2e/test-results/',
    'playwright-report/',
    '.playwright-mcp/',
    'cache/',
    'logs/',
    '/data/',
    '*.sqlite',
    '*.sqlite3',
    '*.db',
    '*.jsonl',
    'publish_queue.json',
    '.agent/',
    '.agents/',
    '.claude/',
    '.cmux/',
    '.understand-anything/',
    '.worktrees/',
    'downloads/',
    'skills-lock.json',
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def validate_dependabot(path: Path = DEPENDABOT) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f'{path.relative_to(ROOT)} is required']

    try:
        config = _load_yaml(path)
    except yaml.YAMLError as exc:
        return [f'{path.relative_to(ROOT)} is not valid YAML: {exc.__class__.__name__}: {exc}']

    if config.get('version') != 2:
        errors.append('dependabot.yml must use version: 2')

    updates = config.get('updates')
    if not isinstance(updates, list):
        return errors + ['dependabot.yml updates must be a list']

    configured = set()
    seen_times = set()
    for index, update in enumerate(updates):
        if not isinstance(update, dict):
            errors.append(f'dependabot update #{index + 1} must be a mapping')
            continue
        ecosystem = update.get('package-ecosystem')
        directory = update.get('directory')
        configured.add((ecosystem, directory))

        schedule = update.get('schedule') or {}
        if schedule.get('interval') != 'weekly':
            errors.append(f'dependabot {ecosystem}:{directory} must run weekly')
        if schedule.get('timezone') != 'Etc/UTC':
            errors.append(f'dependabot {ecosystem}:{directory} must use Etc/UTC timezone')
        time = schedule.get('time')
        if time in seen_times:
            errors.append(f'dependabot schedule time {time} must be unique to avoid update bursts')
        seen_times.add(time)

        if int(update.get('open-pull-requests-limit') or 0) < 3:
            errors.append(f'dependabot {ecosystem}:{directory} must allow at least 3 open PRs')
        labels = set(update.get('labels') or [])
        if 'dependencies' not in labels:
            errors.append(f'dependabot {ecosystem}:{directory} must label dependency PRs')

    missing = REQUIRED_DEPENDABOT_UPDATES - configured
    for ecosystem, directory in sorted(missing):
        errors.append(f'dependabot must update {ecosystem} manifests in {directory}')

    for update in updates:
        if not isinstance(update, dict):
            continue
        key = (update.get('package-ecosystem'), update.get('directory'))
        manifest_globs = DEPENDABOT_MANIFEST_GLOBS.get(key)
        if not manifest_globs:
            errors.append(f'dependabot {key[0]}:{key[1]} is not an approved production dependency update target')
            continue
        if not any(list(ROOT.glob(pattern)) for pattern in manifest_globs):
            errors.append(f'dependabot {key[0]}:{key[1]} does not match any expected manifest files')

    return errors


def validate_dockerignore(path: Path = DOCKERIGNORE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f'{path.relative_to(ROOT)} is required']

    patterns = {
        line.strip()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }
    missing = REQUIRED_DOCKERIGNORE_PATTERNS - patterns
    for pattern in sorted(missing):
        errors.append(f'.dockerignore must include {pattern}')

    if 'package-lock.json' in patterns:
        errors.append('.dockerignore must not ignore every package-lock.json; use /package-lock.json for the root lockfile')
    if '/package-lock.json' not in patterns:
        errors.append('.dockerignore must explicitly scope root package-lock ignore as /package-lock.json')
    if 'frontend/package-lock.json' in patterns or '**/package-lock.json' in patterns:
        errors.append('.dockerignore must keep frontend/package-lock.json in the build context for npm ci')

    return errors


def validate_deploy_compose_logging(path: Path = DEPLOY_COMPOSE) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f'{path.relative_to(ROOT)} is required']

    try:
        compose = _load_yaml(path)
    except yaml.YAMLError as exc:
        return [f'{path.relative_to(ROOT)} is not valid YAML: {exc.__class__.__name__}: {exc}']

    services = compose.get('services')
    if not isinstance(services, dict):
        return ['docker-compose.deploy.yml must define services']

    for name, service in sorted(services.items()):
        if not isinstance(service, dict):
            errors.append(f'docker-compose.deploy.yml service {name} must be a mapping')
            continue
        logging = service.get('logging') or {}
        options = logging.get('options') if isinstance(logging, dict) else {}
        if logging.get('driver') != 'json-file':
            errors.append(f'docker-compose.deploy.yml service {name} must use bounded json-file logging')
            continue
        if not (isinstance(options, dict) and options.get('max-size') and options.get('max-file')):
            errors.append(f'docker-compose.deploy.yml service {name} must set logging max-size and max-file')

    return errors


def validate_maintenance_config() -> list[str]:
    return validate_dependabot() + validate_dockerignore() + validate_deploy_compose_logging()


def main() -> int:
    errors = validate_maintenance_config()
    if errors:
        print('maintenance config validation failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print('maintenance config validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
