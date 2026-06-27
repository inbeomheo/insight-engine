"""GitHub Actions workflow production deployment contract."""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'
VALIDATOR = ROOT / 'scripts' / 'validate_ci_workflow.py'
PINNED_ACTION_REF = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$')
EXPECTED_ACTION_PINS = {
    'actions/checkout': 'actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5',
    'actions/setup-python': 'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
    'actions/setup-node': 'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020',
    'docker/setup-buildx-action': 'docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f',
    'docker/build-push-action': 'docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8',
    'docker/login-action': 'docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9',
    'bervProject/railway-deploy': 'bervProject/railway-deploy@4a1cfdb24551aee5c891e0bc716e8de963c4fbe6',
}
EXPECTED_ACTION_VERSION_COMMENTS = {
    'actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5': 'v4',
    'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065': 'v5',
    'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020': 'v4',
    'docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f': 'v3',
    'docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8': 'v6',
    'docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9': 'v3',
    'bervProject/railway-deploy@4a1cfdb24551aee5c891e0bc716e8de963c4fbe6': '0.2.0-beta',
}


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))


def _steps(job_name):
    return _workflow()['jobs'][job_name]['steps']


def _step(job_name, name):
    for step in _steps(job_name):
        if step.get('name') == name:
            return step
    raise AssertionError(f'{job_name} step not found: {name}')


def test_ci_workflow_is_valid_yaml_and_validator_passes():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'GitHub Actions workflow validation passed' in result.stdout


def test_frontend_node_cache_path_is_under_setup_node_with():
    setup_node = _step('frontend', 'Set up Node.js')

    assert setup_node['with']['cache'] == 'npm'
    assert setup_node['with']['cache-dependency-path'] == 'frontend/package-lock.json'
    assert all('cache-dependency-path' not in step for step in _steps('frontend'))


def test_production_gates_install_python_dependencies_for_yaml_validators():
    step_names = [step.get('name') for step in _steps('production-gates')]

    assert 'Install production gate Python dependencies' in step_names
    assert _step('production-gates', 'Install Python audit dependencies')['run'] == 'python -m pip install -r requirements-ci.txt'
    assert _step('production-gates', 'Audit Python dependencies')['run'] == 'npm run verify:python-audit'
    assert 'Validate Kubernetes deployment manifest' in step_names
    assert 'Validate GitHub Actions workflow contract' in step_names
    assert 'Validate maintenance automation contract' in step_names


def test_workflow_uses_minimal_github_token_permissions():
    workflow = _workflow()

    assert workflow['permissions'] == {'contents': 'read'}


def test_workflow_actions_are_pinned_to_reviewed_commit_shas():
    for job_name, job in _workflow()['jobs'].items():
        for step in job['steps']:
            uses = step.get('uses')
            if not uses:
                continue

            assert PINNED_ACTION_REF.fullmatch(uses), f'{job_name}: {uses}'
            action_name = uses.split('@', 1)[0]
            assert uses == EXPECTED_ACTION_PINS[action_name]


def test_workflow_action_pins_include_version_comments_for_dependabot_updates():
    workflow_text = WORKFLOW.read_text(encoding='utf-8')

    for action_ref, version_comment in EXPECTED_ACTION_VERSION_COMMENTS.items():
        assert f'{action_ref} # {version_comment}' in workflow_text


def test_publish_image_produces_supply_chain_attestations():
    build_step = _step('publish-image', 'Build and push production image')
    build_with = build_step['with']

    assert build_with['push'] is True
    assert build_with['provenance'] == 'mode=max'
    assert build_with['sbom'] is True
    assert '${{ github.sha }}' in build_with['tags']


def test_docker_build_verifies_built_image_hygiene():
    build_step = _step('docker-build', 'Build production image')
    hygiene_step = _step('docker-build', 'Verify production image hygiene')

    assert build_step['with']['push'] is False
    assert build_step['with']['tags'] == 'insight-engine:ci'
    assert hygiene_step['env']['IMAGE_REF'] == 'insight-engine:ci'
    assert hygiene_step['run'] == 'npm run verify:image-hygiene'


def test_deploy_job_verifies_public_readiness_after_railway_deploy():
    workflow = _workflow()
    deploy = workflow['jobs']['deploy']
    monitor_config = _step('deploy', 'Verify required production monitor configuration')
    readiness = _step('deploy', 'Verify deployed production readiness')

    assert deploy['needs'] == 'publish-image'
    assert deploy['environment'] == 'production'
    assert deploy['timeout-minutes'] >= 20
    assert deploy['concurrency'] == {
        'group': 'insight-engine-production',
        'cancel-in-progress': False,
    }
    railway = _step('deploy', 'Deploy to Railway')
    assert railway['env']['RAILWAY_TOKEN'] == '${{ secrets.RAILWAY_TOKEN }}'
    assert 'railway_token' not in railway['with']
    assert 'INSIGHT_BASE_URL' in monitor_config['env']
    assert 'ALERT_WEBHOOK_URL' in monitor_config['env']
    assert readiness['env']['INSIGHT_EXPECTED_RELEASE'] == '${{ github.sha }}'
    assert readiness['env']['INSIGHT_EXPECTED_GIT_SHA'] == '${{ github.sha }}'

    run = readiness['run']
    assert 'scripts/monitor_readiness.py' in run
    assert '--require-public-host' in run
    assert '--require-https' in run
    assert '--tls-min-days 21' in run
    assert '--require-release-metadata' in run
    assert '--expected-release "$INSIGHT_EXPECTED_RELEASE"' in run
    assert '--expected-git-sha "$INSIGHT_EXPECTED_GIT_SHA"' in run
    assert '--require-webhook' in run


def test_package_json_exposes_ci_workflow_validation_gate():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    verify_release = (ROOT / 'scripts' / 'verify_release.sh').read_text(encoding='utf-8')

    assert package_json['scripts']['verify:ci'] == 'python3 scripts/validate_ci_workflow.py'
    assert package_json['scripts']['verify:image-hygiene'] == 'bash scripts/verify_docker_image_hygiene.sh'
    assert 'npm run verify:ci' in verify_release
