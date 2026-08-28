"""Release artifact and deployment topology regression tests."""
from pathlib import Path
import importlib.util
import json
import subprocess
from types import SimpleNamespace

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
RAILWAY_SELECTOR = ROOT / 'scripts' / 'select_railway_deployment.cjs'
RAILWAY_CONTRACT = ROOT / 'scripts' / 'validate_railway_contract.cjs'


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding='utf-8')


def test_master_is_the_only_production_publish_and_deploy_branch():
    workflow = _read('.github/workflows/ci.yml')
    parsed_workflow = yaml.safe_load(workflow)
    deploy = workflow.split('  deploy:', 1)[1]

    assert "refs/heads/master" in deploy
    assert "refs/heads/main" not in deploy
    assert 'continue-on-error' not in deploy
    assert '@railway/cli@5.45.2' in deploy
    assert parsed_workflow['defaults']['run']['shell'] == 'bash'
    assert 'set -Eeuo pipefail' in deploy
    assert 'RELEASE_IMAGE: ${{ secrets.DOCKER_USERNAME }}/insight-engine:${{ github.sha }}' in deploy
    assert (
        'railway service source connect --image "$RELEASE_IMAGE" '
        '--service "$RAILWAY_SERVICE" --json'
    ) in deploy
    assert 'railway redeploy' not in deploy
    assert '--from-source' not in deploy
    assert deploy.count(
        'railway deployment list --service "$RAILWAY_SERVICE" --limit 20 --json'
    ) == 2
    assert 'scripts/select_railway_deployment.cjs "$before_ids" "$RELEASE_IMAGE"' in deploy
    assert 'deployment_id" != "$before_id' not in deploy
    assert 'FAILED|CRASHED|REMOVED' in deploy
    assert 'Timed out waiting for Railway to deploy exact image $RELEASE_IMAGE' in deploy
    assert 'railway status --json' in deploy
    assert 'railway environment config --json' in deploy
    assert 'validate-environment "$service_id" "$RELEASE_IMAGE"' in deploy
    assert 'validate-settings "$service_id"' in deploy
    assert 'railway variable list --service "$RAILWAY_SERVICE" --json' in deploy
    assert 'select-public-origin' in deploy
    assert '"$public_origin/ready"' in deploy
    assert '"$ready_status" == "200"' in deploy
    assert deploy.index('validate-settings "$service_id"') < deploy.index(
        'service source connect --image "$RELEASE_IMAGE"'
    )
    assert deploy.index('select-public-origin') < deploy.index(
        'service source connect --image "$RELEASE_IMAGE"'
    )
    assert deploy.index('service source connect --image "$RELEASE_IMAGE"') < deploy.index(
        'deadline=$((SECONDS + 1800))'
    )
    assert deploy.index('uses: actions/checkout@v4') < deploy.index(
        'scripts/select_railway_deployment.cjs'
    )

    coverage = workflow.split('- name: 커버리지 업로드', 1)[1].split('  #', 1)[0]
    assert "refs/heads/master" in coverage
    assert 'continue-on-error' not in coverage
    assert '--ignore=tests/e2e' in coverage
    assert '--ignore=tests/web_feature_test.py' in coverage

    docker_build = workflow.split('  docker-build:', 1)[1].split('  deploy:', 1)[0]
    assert 'load: true' in docker_build
    assert 'push: false' in docker_build
    assert 'DOCKER_SMOKE_IMAGE: insight-engine:ci' in docker_build
    assert 'docker push "$DOCKER_REPOSITORY:$IMAGE_SHA"' in docker_build
    assert 'docker push "$DOCKER_REPOSITORY:production"' in docker_build
    assert docker_build.index('python scripts/ci_docker_smoke.py') < docker_build.index(
        'docker push "$DOCKER_REPOSITORY:$IMAGE_SHA"'
    )
    assert 'target: chatmock' in docker_build

    e2e = workflow.split('  e2e-no-auth:', 1)[1].split('  docker-build:', 1)[0]
    assert '--project=no-auth-chromium' not in e2e
    assert 'npx --no-install playwright test' in e2e


def _select_railway_deployment(rows, *, excluded='', image='owner/insight-engine:sha'):
    return subprocess.run(
        ['node', str(RAILWAY_SELECTOR), excluded, image],
        input=json.dumps(rows),
        text=True,
        capture_output=True,
        check=False,
    )


def test_railway_selector_ignores_unrelated_and_preexisting_deployments():
    result = _select_railway_deployment(
        [
            {
                'id': 'manual-new',
                'status': 'SUCCESS',
                'meta': {'image': 'other/project:latest'},
            },
            {
                'id': 'release-new',
                'status': 'BUILDING',
                'meta': {
                    'source': {
                        'image': 'docker.io/owner/insight-engine:sha',
                    },
                },
            },
            {
                'id': 'release-old',
                'status': 'SUCCESS',
                'meta': {'image': 'owner/insight-engine:sha'},
            },
        ],
        excluded='release-old',
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == 'release-new\tBUILDING\n'


def test_railway_selector_returns_a_newline_when_no_exact_image_matches():
    result = _select_railway_deployment([
        {
            'id': 'manual-new',
            'status': 'SUCCESS',
            'meta': {'image': 'other/project:latest'},
        },
    ])

    assert result.returncode == 0, result.stderr
    assert result.stdout == '\t\n'


@pytest.mark.parametrize(
    'meta',
    [
        {'image': 'evil.example/owner/insight-engine:sha'},
        {'note': 'owner/insight-engine:sha'},
        {'note': {'value': 'docker.io/owner/insight-engine:sha'}},
    ],
)
def test_railway_selector_rejects_registry_suffixes_and_non_image_metadata(meta):
    result = _select_railway_deployment([
        {'id': 'unrelated', 'status': 'SUCCESS', 'meta': meta},
    ])

    assert result.returncode == 0, result.stderr
    assert result.stdout == '\t\n'


def test_railway_selector_rejects_an_image_hidden_in_build_metadata():
    result = _select_railway_deployment([
        {
            'id': 'unrelated',
            'status': 'SUCCESS',
            'meta': {
                'buildMetadata': {
                    'image': 'owner/insight-engine:sha',
                },
            },
        },
    ])

    assert result.returncode == 0, result.stderr
    assert result.stdout == '\t\n'


def test_railway_selector_fails_closed_on_invalid_cli_json():
    result = subprocess.run(
        ['node', str(RAILWAY_SELECTOR), '', 'owner/insight-engine:sha'],
        input='{}',
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert 'must be a JSON array' in result.stderr


def _validate_railway_contract(mode, payload, *args):
    return subprocess.run(
        ['node', str(RAILWAY_CONTRACT), mode, *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def test_railway_contract_selects_exactly_one_named_service():
    payload = {
        'services': {
            'edges': [
                {'node': {'id': 'other-id', 'name': 'other'}},
                {'node': {'id': 'service-id', 'name': 'insight-engine'}},
            ],
        },
    }

    result = _validate_railway_contract('select-service', payload, 'insight-engine')

    assert result.returncode == 0, result.stderr
    assert result.stdout == 'service-id\n'


def _railway_environment_config():
    return {
        'services': {
            'service-id': {
                'isCreated': True,
                'isDeleted': False,
                'source': {'image': 'docker.io/owner/insight-engine:sha'},
                'deploy': {
                    'healthcheckPath': '/ready',
                    'healthcheckTimeout': 120,
                    'requiredMountPath': '/app/persist',
                    'drainingSeconds': 630,
                },
                'volumeMounts': {
                    'volume-id': {'mountPath': '/app/persist'},
                },
            },
        },
        'volumes': {
            'volume-id': {
                'isCreated': True,
                'isDeleted': False,
            },
        },
    }


def test_railway_contract_validates_live_image_healthcheck_drain_and_volume():
    result = _validate_railway_contract(
        'validate-environment',
        _railway_environment_config(),
        'service-id',
        'owner/insight-engine:sha',
    )

    assert result.returncode == 0, result.stderr
    assert 'Railway live contract verified' in result.stdout


def test_railway_contract_preflights_settings_before_the_release_image_changes():
    payload = _railway_environment_config()
    payload['services']['service-id']['source']['image'] = 'owner/insight-engine:previous'

    result = _validate_railway_contract(
        'validate-settings',
        payload,
        'service-id',
    )

    assert result.returncode == 0, result.stderr
    assert 'Railway live contract verified' in result.stdout


@pytest.mark.parametrize(
    ('field', 'value', 'message'),
    [
        ('source.image', 'evil.example/owner/insight-engine:sha', 'exact release image'),
        ('deploy.healthcheckPath', '/health', 'healthcheckPath'),
        ('deploy.healthcheckTimeout', 119, 'healthcheckTimeout'),
        ('deploy.requiredMountPath', '/data', 'requiredMountPath'),
        ('deploy.drainingSeconds', 629, 'drainingSeconds'),
        ('volumeMounts.volume-id.mountPath', '/data', 'exactly one volume'),
    ],
)
def test_railway_contract_fails_closed_on_live_setting_drift(field, value, message):
    payload = _railway_environment_config()
    target = payload['services']['service-id']
    parts = field.split('.')
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value

    result = _validate_railway_contract(
        'validate-environment',
        payload,
        'service-id',
        'owner/insight-engine:sha',
    )

    assert result.returncode == 1
    assert message in result.stderr


def test_railway_contract_rejects_a_service_not_marked_created():
    payload = _railway_environment_config()
    payload['services']['service-id']['isCreated'] = False

    result = _validate_railway_contract(
        'validate-environment',
        payload,
        'service-id',
        'owner/insight-engine:sha',
    )

    assert result.returncode == 1
    assert 'active service' in result.stderr


@pytest.mark.parametrize(
    ('mutation', 'message'),
    [
        ('missing', 'missing or inactive'),
        ('not-created', 'missing or inactive'),
        ('deleted', 'missing or inactive'),
    ],
)
def test_railway_contract_rejects_an_inactive_mounted_volume(mutation, message):
    payload = _railway_environment_config()
    if mutation == 'missing':
        payload['volumes'].pop('volume-id')
    elif mutation == 'not-created':
        payload['volumes']['volume-id']['isCreated'] = False
    else:
        payload['volumes']['volume-id']['isDeleted'] = True

    result = _validate_railway_contract(
        'validate-environment',
        payload,
        'service-id',
        'owner/insight-engine:sha',
    )

    assert result.returncode == 1
    assert message in result.stderr


def test_railway_contract_outputs_only_a_valid_https_public_origin():
    result = _validate_railway_contract(
        'select-public-origin',
        {
            'PUBLIC_ORIGIN': 'https://insight.example.com',
            'RAILWAY_DEPLOYMENT_DRAINING_SECONDS': '630',
            'SECRET': 'do-not-print',
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == 'https://insight.example.com\n'
    assert 'do-not-print' not in result.stdout + result.stderr


@pytest.mark.parametrize(
    'origin',
    ['http://insight.example.com', 'https://insight.example.com/path', 'not-a-url'],
)
def test_railway_contract_rejects_an_invalid_public_origin(origin):
    result = _validate_railway_contract(
        'select-public-origin',
        {
            'PUBLIC_ORIGIN': origin,
            'RAILWAY_DEPLOYMENT_DRAINING_SECONDS': '630',
        },
    )

    assert result.returncode == 1
    assert 'PUBLIC_ORIGIN' in result.stderr


def test_railway_contract_rejects_a_short_runtime_drain_window():
    result = _validate_railway_contract(
        'select-public-origin',
        {
            'PUBLIC_ORIGIN': 'https://insight.example.com',
            'RAILWAY_DEPLOYMENT_DRAINING_SECONDS': '629',
        },
    )

    assert result.returncode == 1
    assert 'RAILWAY_DEPLOYMENT_DRAINING_SECONDS' in result.stderr


def test_python_dependency_audit_blocks_every_non_reviewed_finding():
    workflow = _read('.github/workflows/ci.yml')
    audit = workflow.split('- name: Python 의존성 취약점 감사', 1)[1].split(
        '- name: 린트', 1,
    )[0]

    assert 'pip-audit -r requirements.txt' in audit
    assert 'SECURITY.md' in audit
    assert audit.count('--ignore-vuln') == 4
    for advisory in (
        'PYSEC-2026-311',
        'CVE-2026-45830',
        'CVE-2026-45831',
        'CVE-2026-45833',
    ):
        assert f'--ignore-vuln {advisory}' in audit
    assert 'continue-on-error' not in audit


def test_railway_uses_the_full_stack_docker_artifact():
    railway = json.loads(_read('railway.json'))
    dockerfile = _read('Dockerfile')
    dockerignore = _read('.dockerignore')

    assert railway['build'] == {'builder': 'DOCKERFILE', 'dockerfilePath': 'Dockerfile'}
    assert railway['$schema'] == 'https://railway.com/railway.schema.json'
    assert railway['deploy']['drainingSeconds'] == 630
    assert railway['deploy']['healthcheckPath'] == '/ready'
    assert railway['deploy']['requiredMountPath'] == '/app/persist'
    assert 'startCommand' not in railway['deploy']
    assert 'FROM node:22-bookworm-slim AS frontend-builder' in dockerfile
    assert 'FROM node:22-alpine AS frontend-builder' not in dockerfile
    final_stage = dockerfile.split('FROM python:3.11-slim AS final', 1)[1]
    assert 'USER appuser' not in final_stage
    assert 'RAILWAY_RUN_UID=0' in _read('README.md')
    assert '/app/persist' in dockerfile
    assert 'scripts/run_full_stack.py' in dockerfile
    assert 'http://127.0.0.1:${PORT:-8080}/ready' in dockerfile
    assert 'http://127.0.0.1:${PORT:-8080}/health' not in dockerfile
    assert '!frontend/package-lock.json' in dockerignore
    assert '!LICENSE' in dockerignore
    assert '/data_volume_backups/' in dockerignore
    assert '/services/cache/' in dockerignore
    gitignore = _read('.gitignore')
    assert '/data_volume_backups/' in gitignore
    assert '/services/cache/' in gitignore
    assert 'CONTENT_CACHE_DIR=/app/persist/cache/content' in dockerfile
    supervisor = _read('scripts/run_full_stack.py')
    assert "['python', 'scripts/backup_app_data.py', 'daemon']" in supervisor
    assert 'os.setgid(account.pw_gid)' in supervisor
    assert 'os.setuid(account.pw_uid)' in supervisor
    assert supervisor.index('_prepare_and_drop_privileges()') < supervisor.index(
        '_start_services(role)'
    )


def test_chatmock_is_pinned_non_root_and_uses_a_named_credential_volume():
    dockerfile = _read('Dockerfile')
    compose_text = _read('docker-compose.deploy.yml')
    compose = yaml.safe_load(compose_text)
    chatmock = compose['services']['chatmock']
    login = compose['services']['chatmock-login']

    assert dockerfile.count('chatmock==1.40') == 1
    assert chatmock['read_only'] is True
    assert chatmock['cap_drop'] == ['ALL']
    assert chatmock['volumes'] == ['insight_chatmock_credentials:/data']
    assert chatmock['environment']['CHATGPT_LOCAL_HOME'] == '/data/codex'
    assert login['profiles'] == ['chatmock-login']
    assert login['volumes'] == ['insight_chatmock_credentials:/data']
    assert 'CHATMOCK_CODEX_HOME' not in compose_text


def test_compose_health_and_single_volume_backup_contracts():
    standard = yaml.safe_load(_read('docker-compose.yml'))
    deploy = yaml.safe_load(_read('docker-compose.deploy.yml'))

    assert '3000/' in ' '.join(standard['services']['frontend']['healthcheck']['test'])
    assert standard['services']['nginx']['depends_on']['frontend']['condition'] == 'service_healthy'
    assert 'ready' in ' '.join(deploy['services']['backend']['healthcheck']['test'])
    assert deploy['services']['backend']['depends_on']['chatmock']['condition'] == 'service_healthy'
    assert deploy['services']['edge']['depends_on']['frontend']['condition'] == 'service_healthy'

    assert 'app-data-backup' not in deploy['services']
    deploy_backend = deploy['services']['backend']
    assert deploy_backend['volumes'] == ['insight_app_persist:/app/persist']
    assert deploy_backend['environment']['APP_DATA_DIR'] == '/app/persist/data'
    assert deploy_backend['environment']['APP_DATA_BACKUP_DIR'] == '/app/persist/backups'
    assert deploy_backend['environment']['AUTO_BACKUP_ENABLED'] == '${AUTO_BACKUP_ENABLED:-false}'
    assert deploy_backend['environment']['PLATFORM_VOLUME_BACKUPS_ENABLED'] == (
        '${PLATFORM_VOLUME_BACKUPS_ENABLED:?Enable independent platform volume backups and set true}'
    )
    assert deploy_backend['environment']['PUBLIC_ORIGIN'] == (
        '${PUBLIC_ORIGIN:?Set PUBLIC_ORIGIN to the public HTTPS origin}'
    )
    assert deploy_backend['environment']['SUPABASE_SECRET_KEY'] == '${SUPABASE_SECRET_KEY:-}'
    assert deploy_backend['environment']['SUPABASE_SERVICE_ROLE_KEY'] == '${SUPABASE_SERVICE_ROLE_KEY:-}'
    assert deploy_backend['environment']['BACKUP_QUIESCE_TIMEOUT_SECONDS']
    assert deploy_backend['environment']['BACKUP_INITIAL_DELAY_SECONDS'] == (
        '${BACKUP_INITIAL_DELAY_SECONDS:-300}'
    )
    assert deploy_backend['command'][-1] == 'backend'

    standard_backend = standard['services']['backend']
    assert standard_backend['volumes'] == ['app_persist:/app/persist']
    assert standard_backend['command'][-1] == 'backend'
    assert list(name for name in standard['volumes'] if name.startswith('app_')) == ['app_persist']
    assert list(name for name in deploy['volumes'] if name.startswith('insight_app_')) == [
        'insight_app_persist'
    ]


def test_supervisor_initializes_mount_as_root_then_never_spawns_web_as_root():
    dockerfile = _read('Dockerfile')
    supervisor = _read('scripts/run_full_stack.py')

    assert 'chown -R appuser:appuser /app/persist' in dockerfile
    assert 'root-owned mount' in dockerfile
    assert "PERSIST_ROOT = Path('/app/persist')" in supervisor
    assert 'os.chown(path, uid, gid, follow_symlinks=False)' in supervisor
    assert "raise RuntimeError('refusing to start application services as root')" in supervisor
    assert supervisor.index("os.setuid(account.pw_uid)") < supervisor.index(
        'def _spawn('
    )
    assert 'start_new_session=True' in supervisor
    assert "'app:app'" in supervisor
    assert 'app:create_app()' not in supervisor
    assert 'BACKEND_GRACEFUL_TIMEOUT_SECONDS' in supervisor
    assert 'NGINX_DRAIN_TIMEOUT_SECONDS' in supervisor
    assert 'signal.SIGQUIT' in supervisor
    assert 'signal.SIGCONT' in supervisor
    assert 'FRONTEND_WATCHDOG_FAILURE_THRESHOLD' in supervisor
    assert 'FULL_STACK_FRONTEND_READINESS_URL' in supervisor
    prepare = supervisor.split('def _prepare_and_drop_privileges()', 1)[1].split(
        'def _backup_enabled()', 1,
    )[0]
    assert prepare.index("recover_interrupted_restore(PERSIST_ROOT / 'data')") < prepare.index(
        '_initialize_persistent_storage('
    )

    next_config = _read('frontend/next.config.ts')
    assert "key: 'Content-Security-Policy'" in next_config
    assert "frame-ancestors 'none'" in next_config
    assert "key: 'X-Frame-Options', value: 'DENY'" in next_config
    assert "key: 'Strict-Transport-Security'" in next_config


def test_persistent_storage_initialization_does_not_follow_symlinks(tmp_path, monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_storage_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    persist = tmp_path / 'persist'
    external = tmp_path / 'external'
    persist.mkdir()
    external.mkdir()
    external_file = external / 'do-not-follow.txt'
    external_file.write_text('external', encoding='utf-8')
    (persist / 'external-link').symlink_to(external_file)
    calls = []

    def record_chown(path, uid, gid, *, follow_symlinks):
        calls.append((Path(path), uid, gid, follow_symlinks))

    monkeypatch.setattr(module.os, 'chown', record_chown)
    module._initialize_persistent_storage(persist, uid=10001, gid=10001)

    assert calls
    assert all(call[3] is False for call in calls)
    assert not any(call[0] == external_file for call in calls)
    for name in module.PERSIST_SUBDIRECTORIES:
        assert (persist / name).is_dir()


def test_root_bootstrap_drops_uid_and_gid_before_service_start(tmp_path, monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_privilege_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    state = {'euid': 0}
    events = []
    account = SimpleNamespace(
        pw_name='appuser',
        pw_uid=10001,
        pw_gid=10001,
        pw_dir='/app/persist/data/home',
    )
    monkeypatch.setattr(module, 'PERSIST_ROOT', tmp_path.resolve() / 'persist')
    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setattr(module.pwd, 'getpwnam', lambda _name: account)
    monkeypatch.setattr(module.os, 'geteuid', lambda: state['euid'])
    monkeypatch.setattr(
        module,
        '_initialize_persistent_storage',
        lambda *_args, **_kwargs: events.append('initialize'),
    )
    monkeypatch.setattr(
        module.os, 'initgroups', lambda *_args: events.append('initgroups'),
    )
    monkeypatch.setattr(module.os, 'setgid', lambda _gid: events.append('setgid'))

    def drop_uid(_uid):
        events.append('setuid')
        state['euid'] = 10001

    monkeypatch.setattr(module.os, 'setuid', drop_uid)
    monkeypatch.setattr(module.os, 'umask', lambda _mask: events.append('umask'))

    module._prepare_and_drop_privileges()

    assert events == ['initialize', 'initgroups', 'setgid', 'setuid', 'umask']
    assert state['euid'] == 10001


def test_non_root_boot_recovers_restore_before_creating_empty_data(tmp_path, monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_non_root_recovery_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    persist = (tmp_path / 'persist').resolve()
    persist.mkdir()
    target = persist / 'data'
    transaction = persist / '.data.restore-interrupted'
    previous = transaction / 'previous'
    previous.mkdir(parents=True)
    (previous / 'preserved.txt').write_text('preserved', encoding='utf-8')
    marker = transaction / '.insight-engine-restore-transaction-v1.json'
    marker.write_text(
        json.dumps({'target_name': 'data', 'version': 1}),
        encoding='utf-8',
    )

    def missing_runtime_account(_name):
        raise KeyError('local non-root runtime')

    monkeypatch.setattr(module, 'PERSIST_ROOT', persist)
    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setattr(module.pwd, 'getpwnam', missing_runtime_account)
    monkeypatch.setattr(module.os, 'geteuid', lambda: 10001)
    monkeypatch.setattr(module.os, 'umask', lambda _mask: None)

    module._prepare_and_drop_privileges()

    assert (target / 'preserved.txt').read_text(encoding='utf-8') == 'preserved'
    assert not transaction.exists()


def test_production_boot_fails_before_creating_an_unmounted_persist_tree(
    tmp_path, monkeypatch,
):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_mount_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    persist = tmp_path.resolve() / 'persist'
    monkeypatch.setattr(module, 'PERSIST_ROOT', persist)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setattr(module, '_is_exact_mount', lambda _path: False)

    with pytest.raises(RuntimeError, match='exact mounted volume'):
        module._prepare_and_drop_privileges()

    assert not persist.exists()


def test_railway_volume_reference_must_match_the_exact_runtime_mount(
    tmp_path, monkeypatch,
):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_railway_mount_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    persist = tmp_path.resolve() / 'persist'
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('RAILWAY_ENVIRONMENT_ID', 'environment-id')
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH', '/wrong/path')
    monkeypatch.setattr(module, '_is_exact_mount', lambda _path: True)

    with pytest.raises(RuntimeError, match='RAILWAY_VOLUME_MOUNT_PATH'):
        module._require_production_persistent_mount(persist)


def test_readme_makes_railway_backup_the_primary_recovery_boundary():
    readme = _read('README.md')

    assert 'Railway\uC758 \uD574\uB2F9 \uBCFC\uB968\uC5D0 \uB300\uD55C manual/automated backup' in readme
    assert '`AUTO_BACKUP_ENABLED=true`' in readme
    assert '`SIGSTOP`' in readme
    assert '`SIGCONT`' in readme
    assert 'SQLite `PRAGMA quick_check`' in readme


def test_edge_auth_uses_required_secret_and_routes_special_paths_correctly():
    caddy = _read('Caddyfile.deploy')
    compose = _read('docker-compose.deploy.yml')
    railway_nginx = _read('nginx.railway.conf')

    assert '{$CADDY_BASIC_AUTH_USER}' in caddy
    assert '{$CADDY_BASIC_AUTH_HASH}' in caddy
    assert '$2a$' not in caddy
    assert '${CADDY_BASIC_AUTH_USER:?' in compose
    assert '${CADDY_BASIC_AUTH_HASH:?' in compose
    assert '@nextOg path /api/og /api/og/*' in caddy
    assert 'reverse_proxy @nextOg frontend:3000' in caddy
    assert caddy.index('reverse_proxy @nextOg frontend:3000') < caddy.index(
        'reverse_proxy @backend backend:5001'
    )

    og_position = railway_nginx.index('location = /api/og')
    api_position = railway_nginx.index('location /api/')
    assert og_position < api_position
    assert 'location ^~ /share/' in railway_nginx
    assert 'location ^~ /api/shares/' in railway_nginx
    assert 'proxy_pass http://127.0.0.1:3000' in railway_nginx
    assert 'proxy_pass http://127.0.0.1:5001' in railway_nginx
    assert 'map $http_x_forwarded_proto $railway_forwarded_proto' in railway_nginx
    assert 'map $http_x_real_ip $railway_client_ip' in railway_nginx
    assert 'proxy_set_header X-Real-IP $railway_client_ip' in railway_nginx
    assert 'proxy_set_header X-Forwarded-For $railway_client_ip' in railway_nginx
    assert 'proxy_set_header X-Forwarded-Proto $railway_forwarded_proto' in railway_nginx
    assert 'proxy_set_header X-Forwarded-Prefix ""' in railway_nginx
    assert 'proxy_set_header X-Real-IP $remote_addr' not in railway_nginx
    assert 'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for' not in railway_nginx


def test_railway_nginx_logging_is_safe_after_privilege_drop():
    railway_nginx = _read('nginx.railway.conf')

    assert 'access_log off;' in railway_nginx
    assert 'error_log stderr warn;' in railway_nginx
    assert '/dev/stdout' not in railway_nginx
    assert '/dev/stderr' not in railway_nginx


def test_standard_nginx_routes_og_and_public_shares_before_generic_api():
    nginx = _read('nginx.conf')

    assert 'location = /api/og' in nginx
    assert 'location ^~ /share/' in nginx
    assert 'location ^~ /api/shares/' in nginx
    assert nginx.index('location = /api/og') < nginx.index('location /api/')
    assert 'proxy_pass http://frontend:3000' in nginx.split('location = /api/og', 1)[1].split('}', 1)[0]
    assert 'proxy_pass http://backend:5001' in nginx.split('location ^~ /api/shares/', 1)[1].split('}', 1)[0]


def test_supervisor_renders_non_root_nginx_paths_and_signal_handler_is_nonblocking(
    tmp_path, monkeypatch,
):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rendered = tmp_path / 'nginx.conf'
    monkeypatch.setattr(module, 'RENDERED_PATH', rendered)
    monkeypatch.setattr(module, 'NGINX_TEMP_ROOT', tmp_path / 'nginx-runtime')
    monkeypatch.setenv('PORT', '8080')
    config_path = module._render_nginx_config(module._public_port())
    config = config_path.read_text(encoding='utf-8')

    assert 'listen 8080;' in config
    assert '${PORT}' not in config
    assert '${NGINX_TEMP_ROOT}' not in config
    assert f'pid {module.NGINX_TEMP_ROOT}/nginx.pid;' in config
    for temp_dir in ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
        assert f'{module.NGINX_TEMP_ROOT}/{temp_dir}' in config
        assert (module.NGINX_TEMP_ROOT / temp_dir).is_dir()
    assert '/var/cache/nginx' not in config

    module.STOP_REQUESTED.clear()
    module._request_stop()
    assert module.STOP_REQUESTED.is_set()


def test_supervisor_drains_nginx_before_stopping_application_processes(monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_shutdown_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    events = []

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid
            self.running = True

        def poll(self):
            return None if self.running else 0

        def wait(self, timeout):
            events.append(('wait', self.pid))
            self.running = False
            return 0

    backend = FakeProcess(101)
    frontend = FakeProcess(102)
    nginx = FakeProcess(103)
    backup = FakeProcess(104)
    module.PROCESSES[:] = [backend, backup, frontend, nginx]
    module.PROCESS_ROLES.update({
        101: 'backend',
        102: 'frontend',
        103: 'nginx',
        104: 'backup',
    })

    def record_signal(process, signal_number):
        events.append(('signal', process.pid, signal_number))

    monkeypatch.setattr(module, '_signal_process_group', record_signal)
    module._stop_all()

    backup_term = events.index(('signal', 104, module.signal.SIGTERM))
    backup_wait = events.index(('wait', 104))
    backend_resume = events.index(('signal', 101, module.signal.SIGCONT))
    nginx_quit = events.index(('signal', 103, module.signal.SIGQUIT))
    frontend_term = events.index(('signal', 102, module.signal.SIGTERM))
    backend_term = events.index(('signal', 101, module.signal.SIGTERM))
    nginx_wait = events.index(('wait', 103))
    assert backup_term < backup_wait < backend_resume
    assert backend_resume < nginx_quit
    assert nginx_quit < frontend_term
    assert nginx_quit < backend_term
    assert frontend_term < nginx_wait
    assert backend_term < nginx_wait
    assert backend_resume < backend_term


def test_full_stack_shutdown_and_proxy_timeouts_fit_platform_window():
    dockerfile = _read('Dockerfile')
    compose = _read('docker-compose.yml')
    deploy_compose = _read('docker-compose.deploy.yml')
    supervisor = _read('scripts/run_full_stack.py')
    standard_nginx = _read('nginx.conf')
    railway_nginx = _read('nginx.railway.conf')

    assert 'BACKUP_SHUTDOWN_TIMEOUT_SECONDS=10' in dockerfile
    assert 'BACKEND_GRACEFUL_TIMEOUT_SECONDS=600' in dockerfile
    assert 'NGINX_DRAIN_TIMEOUT_SECONDS=605' in dockerfile
    assert 'PROCESS_SHUTDOWN_TIMEOUT_SECONDS=605' in dockerfile
    assert 'stop_grace_period: 630s' in compose
    assert (
        'BACKEND_GRACEFUL_TIMEOUT_SECONDS: ${BACKEND_GRACEFUL_TIMEOUT_SECONDS:-600}'
        in deploy_compose
    )
    assert (
        'NGINX_DRAIN_TIMEOUT_SECONDS: ${NGINX_DRAIN_TIMEOUT_SECONDS:-605}'
        in deploy_compose
    )
    assert (
        'PROCESS_SHUTDOWN_TIMEOUT_SECONDS: ${PROCESS_SHUTDOWN_TIMEOUT_SECONDS:-605}'
        in deploy_compose
    )
    assert 'max(nginx_timeout, application_timeout)' in supervisor
    assert 'PLATFORM_SHUTDOWN_TIMEOUT_SECONDS = 630' in supervisor
    assert 'FORCE_KILL_TIMEOUT_SECONDS = 5' in supervisor
    assert 'proxy_read_timeout 660s;' not in standard_nginx
    assert 'proxy_read_timeout 660s;' not in railway_nginx
    assert 'proxy_read_timeout 600s;' in standard_nginx
    assert 'proxy_read_timeout 600s;' in railway_nginx


def test_supervisor_frontend_probe_is_bounded_and_requires_success(monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_probe_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size):
            assert size == 1
            return b'<'

    calls = []

    def open_request(request, *, timeout):
        calls.append((request.full_url, timeout))
        return Response()

    monkeypatch.setattr(module.urllib.request, 'urlopen', open_request)

    assert module._probe_frontend_ready() is True
    assert calls == [(module.FULL_STACK_FRONTEND_URL, 3)]


def test_supervisor_backend_entrypoint_and_graceful_timeout(monkeypatch):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location('run_full_stack_command_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setenv('BACKEND_GRACEFUL_TIMEOUT_SECONDS', '240')
    command = module._backend_command()

    assert '--graceful-timeout=240' in command
    assert command[-1] == 'app:app'
    assert 'app:create_app()' not in command


@pytest.mark.parametrize(
    ('name', 'value'),
    [
        ('BACKUP_SHUTDOWN_TIMEOUT_SECONDS', '31'),
        ('BACKEND_GRACEFUL_TIMEOUT_SECONDS', '601'),
        ('NGINX_DRAIN_TIMEOUT_SECONDS', '606'),
        ('PROCESS_SHUTDOWN_TIMEOUT_SECONDS', 'invalid'),
    ],
)
def test_supervisor_validates_all_shutdown_timeouts_before_spawning(
    name, value, monkeypatch,
):
    script = ROOT / 'scripts' / 'run_full_stack.py'
    spec = importlib.util.spec_from_file_location(
        f'run_full_stack_timeout_preflight_{name}', script,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    events = []
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        module,
        '_prepare_and_drop_privileges',
        lambda: events.append('prepare'),
    )
    monkeypatch.setattr(
        module,
        '_spawn',
        lambda *_args, **_kwargs: events.append('spawn'),
    )

    with pytest.raises(RuntimeError, match=name):
        module.main(['full-stack'])

    assert events == []
