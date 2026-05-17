"""Deployment/CI configuration invariants."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_docker_build_keeps_dev_dependencies_until_build():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    npm_ci = dockerfile.index('RUN npm ci')
    npm_build = dockerfile.index('RUN npm run build')
    npm_prune = dockerfile.index('RUN npm prune --omit=dev')

    assert npm_ci < npm_build < npm_prune
    assert 'RUN npm ci --omit=dev' not in dockerfile


def test_compose_frontend_start_command_is_relative_to_workdir():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text(encoding='utf-8'))
    frontend = compose['services']['frontend']

    assert frontend['working_dir'] == '/app/frontend'
    assert frontend['command'] == [
        'node',
        'node_modules/.bin/next',
        'start',
        '--port',
        '3000',
    ]


def test_ci_installs_test_dependencies_and_gates_docker_on_e2e_smoke():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    jobs = workflow['jobs']

    backend_runs = '\n'.join(step.get('run', '') for step in jobs['backend-test']['steps'])
    e2e_runs = '\n'.join(step.get('run', '') for step in jobs['e2e-smoke']['steps'])

    assert 'requirements-dev.txt' in backend_runs
    assert 'main-page/ci-smoke.spec.ts' in e2e_runs
    assert jobs['docker-build']['needs'] == ['backend-test', 'frontend-test', 'e2e-smoke']


def test_ci_opts_javascript_actions_into_node24_runtime():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))

    assert workflow['env']['FORCE_JAVASCRIPT_ACTIONS_TO_NODE24'] == 'true'


def test_ci_uses_node24_action_major_versions():
    workflow_text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')

    assert 'actions/checkout@v5' in workflow_text
    assert 'actions/setup-node@v5' in workflow_text
    assert 'actions/setup-python@v6' in workflow_text
    assert 'actions/checkout@v4' not in workflow_text
    assert 'actions/setup-node@v4' not in workflow_text
    assert 'actions/setup-python@v5' not in workflow_text


def test_dockerignore_keeps_frontend_lockfile_for_npm_ci():
    dockerignore = (ROOT / '.dockerignore').read_text(encoding='utf-8').splitlines()

    assert 'package-lock.json' not in dockerignore or '!frontend/package-lock.json' in dockerignore


def test_compose_nginx_bind_mount_source_exists():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text(encoding='utf-8'))
    nginx = compose['services']['nginx']
    bind_sources = [volume.split(':', 1)[0] for volume in nginx['volumes'] if volume.startswith('./')]

    for source in bind_sources:
        assert (ROOT / source).exists(), f'missing compose bind source: {source}'


def test_ci_docker_build_runs_for_pull_requests_without_push():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    docker_job = workflow['jobs']['docker-build']
    build_step = next(
        step for step in docker_job['steps']
        if step.get('uses') == 'docker/build-push-action@v5'
    )

    assert "github.event_name == 'pull_request'" in docker_job.get('if', '')
    assert build_step['with']['push'] == "${{ github.event_name != 'pull_request' }}"
    assert build_step['with']['tags'] == "${{ steps.docker-meta.outputs.tags }}"


def test_ci_docker_build_uses_secret_free_pull_request_tags():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    docker_steps = workflow['jobs']['docker-build']['steps']
    tag_step = next(step for step in docker_steps if step.get('id') == 'docker-meta')

    assert "github.event_name" in tag_step['run']
    assert 'insight-engine:pr-' in tag_step['run']
    assert 'DOCKER_USERNAME' in tag_step['env']


def test_ci_triggers_include_repository_default_branch():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))

    assert 'master' in workflow[True]['push']['branches']
    assert 'master' in workflow[True]['pull_request']['branches']


def test_ci_dependency_files_include_imported_test_runtime_modules():
    requirements = (ROOT / 'requirements.txt').read_text(encoding='utf-8').lower()
    dev_requirements = (ROOT / 'requirements-dev.txt').read_text(encoding='utf-8').lower()

    assert 'flask-cors' in requirements
    assert 'duckduckgo-search' in requirements
    assert 'claude-code-sdk' in dev_requirements
    assert 'playwright' in dev_requirements
