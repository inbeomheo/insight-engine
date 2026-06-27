"""Validate GitHub Actions production workflow wiring."""
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'
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


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get('steps') or [])


def _step_by_name(job: dict[str, Any], name: str) -> dict[str, Any] | None:
    for step in _steps(job):
        if step.get('name') == name:
            return step
    return None


def _step_names(job: dict[str, Any]) -> list[str]:
    return [step.get('name', '') for step in _steps(job)]


def validate_workflow(path: Path = WORKFLOW) -> list[str]:
    errors: list[str] = []
    try:
        workflow_text = path.read_text(encoding='utf-8')
        workflow = yaml.safe_load(workflow_text) or {}
    except yaml.YAMLError as exc:
        return [f'{path} is not valid YAML: {exc.__class__.__name__}: {exc}']

    jobs = workflow.get('jobs') or {}
    for job_name in ('backend', 'frontend', 'e2e-smoke', 'production-gates', 'docker-build', 'publish-image', 'deploy'):
        if job_name not in jobs:
            errors.append(f'job {job_name} is required')

    permissions = workflow.get('permissions') or {}
    if permissions != {'contents': 'read'}:
        errors.append('workflow GitHub token permissions must be limited to contents: read')

    frontend = jobs.get('frontend') or {}
    setup_node = _step_by_name(frontend, 'Set up Node.js') or {}
    setup_node_with = setup_node.get('with') or {}
    if setup_node_with.get('cache-dependency-path') != 'frontend/package-lock.json':
        errors.append('frontend setup-node must cache using frontend/package-lock.json')

    for job_name, job in jobs.items():
        for step in _steps(job):
            if 'cache-dependency-path' in step:
                errors.append(f'{job_name}/{step.get("name", "<unnamed>")} has cache-dependency-path outside with')
            uses = step.get('uses')
            if uses:
                if not PINNED_ACTION_REF.fullmatch(str(uses)):
                    errors.append(f'{job_name}/{step.get("name", uses)} must pin action uses to a 40-character commit SHA')
                    continue
                action_name = str(uses).split('@', 1)[0]
                expected_pin = EXPECTED_ACTION_PINS.get(action_name)
                if expected_pin and uses != expected_pin:
                    errors.append(f'{job_name}/{step.get("name", uses)} must use pinned action {expected_pin}')

    for action_ref, version_comment in EXPECTED_ACTION_VERSION_COMMENTS.items():
        expected_line = f'{action_ref} # {version_comment}'
        if expected_line not in workflow_text:
            errors.append(f'workflow action pin {action_ref} must include version comment #{version_comment}')

    production_gates = jobs.get('production-gates') or {}
    if 'Install production gate Python dependencies' not in _step_names(production_gates):
        errors.append('production-gates must install Python dependencies used by validation scripts')
    if 'Validate Kubernetes deployment manifest' not in _step_names(production_gates):
        errors.append('production-gates must validate the Kubernetes manifest')
    python_audit_dependencies = _step_by_name(production_gates, 'Install Python audit dependencies')
    if not python_audit_dependencies:
        errors.append('production-gates must install Python audit dependencies from requirements-ci.txt')
    elif python_audit_dependencies.get('run') != 'python -m pip install -r requirements-ci.txt':
        errors.append('production-gates Python audit dependencies must install requirements-ci.txt')
    python_audit = _step_by_name(production_gates, 'Audit Python dependencies')
    if not python_audit:
        errors.append('production-gates must audit Python dependencies')
    elif python_audit.get('run') != 'npm run verify:python-audit':
        errors.append('production-gates Python dependency audit must run npm run verify:python-audit')
    if 'Validate GitHub Actions workflow contract' not in _step_names(production_gates):
        errors.append('production-gates must validate the GitHub Actions workflow contract')
    if 'Validate maintenance automation contract' not in _step_names(production_gates):
        errors.append('production-gates must validate maintenance automation')

    docker_build = jobs.get('docker-build') or {}
    build_step = _step_by_name(docker_build, 'Build production image')
    if not build_step:
        errors.append('docker-build must build the production image')
    else:
        build_with = build_step.get('with') or {}
        if build_with.get('push') is not False:
            errors.append('docker-build production image build must not push')
        if build_with.get('tags') != 'insight-engine:ci':
            errors.append('docker-build production image must be tagged insight-engine:ci')
    image_hygiene = _step_by_name(docker_build, 'Verify production image hygiene')
    if not image_hygiene:
        errors.append('docker-build must verify production image hygiene after build')
    else:
        env = image_hygiene.get('env') or {}
        if env.get('IMAGE_REF') != 'insight-engine:ci':
            errors.append('production image hygiene step must check insight-engine:ci')
        if image_hygiene.get('run') != 'npm run verify:image-hygiene':
            errors.append('production image hygiene step must run npm run verify:image-hygiene')

    publish_image = jobs.get('publish-image') or {}
    publish_step = _step_by_name(publish_image, 'Build and push production image')
    if not publish_step:
        errors.append('publish-image must build and push the production image')
    else:
        publish_with = publish_step.get('with') or {}
        if publish_with.get('push') is not True:
            errors.append('publish-image build step must push the production image')
        if publish_with.get('provenance') != 'mode=max':
            errors.append('publish-image build step must publish max provenance attestations')
        if publish_with.get('sbom') is not True:
            errors.append('publish-image build step must publish an SBOM attestation')
        tags = str(publish_with.get('tags') or '')
        if '${{ github.sha }}' not in tags:
            errors.append('publish-image build step must publish an immutable github.sha tag')

    deploy = jobs.get('deploy') or {}
    if deploy.get('needs') != 'publish-image':
        errors.append('deploy job must wait for publish-image')
    if deploy.get('environment') != 'production':
        errors.append('deploy job must target the production environment')
    if int(deploy.get('timeout-minutes') or 0) < 20:
        errors.append('deploy job timeout must allow post-deploy readiness retries')
    deploy_concurrency = deploy.get('concurrency') or {}
    if deploy_concurrency.get('group') != 'insight-engine-production':
        errors.append('deploy job must serialize production deployments with a stable concurrency group')
    if deploy_concurrency.get('cancel-in-progress') is not False:
        errors.append('deploy job must not cancel an in-progress production deployment')

    railway_deploy = _step_by_name(deploy, 'Deploy to Railway')
    if not railway_deploy:
        errors.append('deploy job must include the Railway deployment step')
    else:
        if railway_deploy.get('uses') != EXPECTED_ACTION_PINS['bervProject/railway-deploy']:
            errors.append('Railway deployment action must be pinned to the reviewed commit')
        railway_env = railway_deploy.get('env') or {}
        railway_with = railway_deploy.get('with') or {}
        if 'RAILWAY_TOKEN' not in railway_env:
            errors.append('Railway deployment action must receive RAILWAY_TOKEN via env')
        if 'railway_token' in railway_with:
            errors.append('Railway deployment action does not support a railway_token input')

    required_config = _step_by_name(deploy, 'Verify required production monitor configuration')
    if not required_config:
        errors.append('deploy job must fail fast when production monitor secrets are missing')
    else:
        env = required_config.get('env') or {}
        if 'INSIGHT_BASE_URL' not in env:
            errors.append('production monitor config step must require INSIGHT_BASE_URL')
        if 'ALERT_WEBHOOK_URL' not in env:
            errors.append('production monitor config step must require ALERT_WEBHOOK_URL')

    post_deploy = _step_by_name(deploy, 'Verify deployed production readiness')
    if not post_deploy:
        errors.append('deploy job must verify public readiness after Railway deploy')
    else:
        env = post_deploy.get('env') or {}
        run = post_deploy.get('run') or ''
        for key in ('INSIGHT_BASE_URL', 'ALERT_WEBHOOK_URL', 'INSIGHT_EXPECTED_RELEASE', 'INSIGHT_EXPECTED_GIT_SHA'):
            if key not in env:
                errors.append(f'post-deploy readiness step must set {key}')
        for token in (
            'scripts/monitor_readiness.py',
            '--require-public-host',
            '--require-https',
            '--tls-min-days 21',
            '--require-release-metadata',
            '--expected-release "$INSIGHT_EXPECTED_RELEASE"',
            '--expected-git-sha "$INSIGHT_EXPECTED_GIT_SHA"',
            '--require-webhook',
        ):
            if token not in run:
                errors.append(f'post-deploy readiness step must include {token}')

    return errors


def main() -> int:
    errors = validate_workflow()
    if errors:
        print('GitHub Actions workflow validation failed', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1

    print('GitHub Actions workflow validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
