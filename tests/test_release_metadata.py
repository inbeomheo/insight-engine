"""Release metadata exposed for production diagnostics."""
import json
from pathlib import Path

from app import create_app
from utils.release_metadata import release_metadata


ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_uses_safe_env_values():
    metadata = release_metadata({
        'APP_VERSION': 'v2.0',
        'APP_RELEASE': '2026.06.27+abc123',
        'GIT_SHA': 'abc123def456',
        'BUILD_TIME': '2026-06-27T08:00:00Z',
    })

    assert metadata == {
        'version': 'v2.0',
        'release': '2026.06.27+abc123',
        'gitSha': 'abc123def456',
        'buildTime': '2026-06-27T08:00:00Z',
    }


def test_release_metadata_rejects_control_characters_and_spaces():
    metadata = release_metadata({
        'APP_VERSION': 'bad version with spaces',
        'APP_RELEASE': 'bad\nrelease',
        'GIT_SHA': '',
        'BUILD_TIME': 'unknown',
    })

    assert metadata['version'] == 'v2.0'
    assert metadata['release'] == 'unknown'
    assert metadata['gitSha'] == 'unknown'
    assert metadata['buildTime'] == 'unknown'


def test_health_response_includes_release_metadata(monkeypatch):
    monkeypatch.setenv('APP_VERSION', 'v2.0')
    monkeypatch.setenv('APP_RELEASE', 'local-test-release')
    monkeypatch.setenv('GIT_SHA', 'local-test-sha')
    monkeypatch.setenv('BUILD_TIME', '2026-06-27T08:00:00Z')
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health')
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['release'] == {
        'version': 'v2.0',
        'release': 'local-test-release',
        'gitSha': 'local-test-sha',
        'buildTime': '2026-06-27T08:00:00Z',
    }


def test_dockerfile_defines_oci_release_labels():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    assert 'ARG APP_VERSION=v2.0' in dockerfile
    assert 'ARG APP_RELEASE=local' in dockerfile
    assert 'org.opencontainers.image.revision=$GIT_SHA' in dockerfile
    assert 'org.opencontainers.image.created=$BUILD_TIME' in dockerfile


def test_dockerfile_avoids_recursive_app_chown_after_copy():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    assert 'COPY --chown=999:999 . .' in dockerfile
    assert (
        'COPY --chown=999:999 --from=frontend-builder '
        '/app/frontend/.next ./frontend/.next'
    ) in dockerfile
    assert (
        'COPY --chown=999:999 --from=frontend-builder '
        '/app/frontend/node_modules ./frontend/node_modules'
    ) in dockerfile
    assert 'chown -R appuser:appuser /app\n' not in dockerfile


def test_compose_passes_release_build_args_without_clobbering_sentry_release():
    compose = (ROOT / 'docker-compose.deploy.yml').read_text(encoding='utf-8')

    assert 'APP_VERSION: ${APP_VERSION:-v2.0}' in compose
    assert 'APP_RELEASE: ${APP_RELEASE:-local}' in compose
    assert 'GIT_SHA: ${GIT_SHA:-local}' in compose
    assert 'BUILD_TIME: ${BUILD_TIME:-unknown}' in compose
    assert 'SENTRY_RELEASE: ${SENTRY_RELEASE:-local}' not in compose


def test_ci_docker_build_passes_github_sha_as_release():
    ci = (ROOT / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')

    assert "BUILD_TIME=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" in ci
    assert 'APP_RELEASE=${{ github.sha }}' in ci
    assert 'GIT_SHA=${{ github.sha }}' in ci


def test_release_verification_script_exports_release_metadata_before_gates():
    script = (ROOT / 'scripts' / 'verify_release.sh').read_text(encoding='utf-8')
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:release'] == 'bash scripts/verify_release.sh'
    assert 'export APP_RELEASE="${APP_RELEASE:-$GIT_SHA}"' in script
    assert '"$PY" scripts/check_production_readiness.py' in script
    assert 'docker compose -f docker-compose.deploy.yml config --quiet' in script


def test_package_version_remains_documented_source_version():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['version'] == '1.0.0'
