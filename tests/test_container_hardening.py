"""Docker Compose runtime hardening contract."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / 'docker-compose.deploy.yml'
DOCKERFILE = ROOT / 'Dockerfile'
RUNTIME_SERVICES = {'backend', 'frontend', 'edge', 'chatmock', 'redis'}
CAP_DROP_ALL_SERVICES = {'backend', 'frontend', 'chatmock'}
READ_ONLY_ROOT_SERVICES = {'backend', 'frontend', 'edge', 'redis'}


def _compose_services() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding='utf-8'))['services']


def test_deploy_compose_applies_basic_container_hardening():
    services = _compose_services()

    for service_name in RUNTIME_SERVICES:
        service = services[service_name]
        assert service['init'] is True
        assert service['security_opt'] == ['no-new-privileges:true']
        assert service['pids_limit'] == 512
        assert service['logging'] == {
            'driver': 'json-file',
            'options': {
                'max-size': '${DOCKER_LOG_MAX_SIZE:-10m}',
                'max-file': '${DOCKER_LOG_MAX_FILE:-5}',
            },
        }

    for service_name in CAP_DROP_ALL_SERVICES:
        assert services[service_name]['cap_drop'] == ['ALL']
    assert 'cap_drop' not in services['edge']
    assert 'cap_drop' not in services['redis']


def test_deploy_compose_does_not_require_chatmock_for_production_stack():
    services = _compose_services()

    assert 'chatmock' not in services['backend']['depends_on']
    assert services['chatmock']['profiles'] == ['chatmock']


def test_deploy_compose_sets_backend_read_only_root_filesystem():
    services = _compose_services()
    backend = services['backend']

    assert backend['read_only'] is True
    assert backend['environment']['PYTHONDONTWRITEBYTECODE'] == '1'
    assert backend['environment']['XDG_CACHE_HOME'] == '/app/cache/xdg'
    assert backend['environment']['APP_CACHE_DIR'] == '/app/cache'
    assert backend['environment']['AI_CACHE_DB'] == '/app/cache/ai_cache.db'
    assert backend['environment']['AGENT_DB_PATH'] == '/app/data/agent_state.db'
    assert backend['environment']['CHROMA_DB_PATH'] == '/app/data/chroma_db'
    assert backend['environment']['CONTENT_BACKUP_DIR'] == '/app/backups/content-library'
    assert backend['environment']['FEEDBACK_DATA_DIR'] == '/app/data/feedback'
    assert backend['environment']['FEEDBACK_STORE_DIR'] == '/app/data/feedback'
    assert backend['environment']['FINETUNE_OUTPUT_DIR'] == '/app/data/finetune'
    assert backend['environment']['GRAPH_STORE_PATH'] == '/app/data/graph_store'
    assert backend['environment']['JOB_STORE_DIR'] == '/app/data/jobs'
    assert backend['environment']['PREFERENCE_DATA_PATH'] == '/app/data/preferences.jsonl'
    assert backend['environment']['SHARE_PAGE_DIR'] == '/app/data/shared_pages'
    assert backend['environment']['USER_MEMORY_PATH'] == '/app/data/user_memory'
    assert backend['environment']['SCHEDULER_HEARTBEAT_FILE'] == '/tmp/insight-engine-scheduler.heartbeat'
    assert backend['tmpfs'] == [
        '/tmp:rw,noexec,nosuid,nodev,size=128m',
        '/app/.gunicorn:rw,noexec,nosuid,nodev,size=1m,mode=1777',
    ]
    assert backend['volumes'] == [
        'insight_app_data:/app/data',
        '${APP_DATA_BACKUP_VOLUME:-insight_app_backups}:/app/backups',
        '${APP_DATA_BACKUP_REPLICA_VOLUME:-insight_app_backup_replica}:/app/backup-replica',
        'insight_app_cache:/app/cache',
        'insight_app_logs:/app/logs',
    ]


def test_deploy_compose_sets_read_only_root_filesystem_where_supported():
    services = _compose_services()

    for service_name in READ_ONLY_ROOT_SERVICES:
        assert services[service_name]['read_only'] is True

    assert 'read_only' not in services['chatmock']
    assert services['frontend']['environment']['NEXT_TELEMETRY_DISABLED'] == '1'
    assert services['frontend']['environment']['XDG_CACHE_HOME'] == '/tmp/xdg-cache'
    assert services['frontend']['environment']['TMPDIR'] == '/tmp'
    assert services['frontend']['tmpfs'] == [
        '/tmp:rw,noexec,nosuid,nodev,size=64m',
        '/app/frontend/.next/cache:rw,noexec,nosuid,nodev,size=128m',
        '/app/frontend/.next/diagnostics:rw,noexec,nosuid,nodev,size=8m',
    ]
    assert services['redis']['tmpfs'] == [
        '/tmp:rw,noexec,nosuid,nodev,size=32m',
    ]
    assert services['edge']['volumes'] == [
        './Caddyfile.deploy:/etc/caddy/Caddyfile:ro',
        'insight_caddy_data:/data',
        'insight_caddy_config:/config',
    ]


def test_deploy_compose_sets_graceful_stop_windows():
    services = _compose_services()

    assert services['backend']['stop_grace_period'] == '60s'
    for service_name in RUNTIME_SERVICES - {'backend'}:
        assert services[service_name]['stop_grace_period'] == '30s'


def test_dockerfile_uses_fixed_non_root_runtime_uid():
    dockerfile = DOCKERFILE.read_text(encoding='utf-8')

    assert '--uid 999' in dockerfile
    assert '--gid 999' in dockerfile
    assert 'USER 999:999' in dockerfile


def test_dockerfile_reuses_builder_node_runtime_without_nodesource_script():
    dockerfile = DOCKERFILE.read_text(encoding='utf-8')

    assert 'COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node' in dockerfile
    assert 'deb.nodesource.com' not in dockerfile
    assert 'setup_20.x' not in dockerfile
    assert '| bash' not in dockerfile
    assert 'apt-get install -y nodejs' not in dockerfile


def test_dockerfile_defaults_to_production_gunicorn_entrypoint():
    dockerfile = DOCKERFILE.read_text(encoding='utf-8')

    assert 'FLASK_ENV=production' in dockerfile
    assert 'FLASK_DEBUG=0' in dockerfile
    assert 'APP_DATA_DIR=/app/data' in dockerfile
    assert 'AGENT_DB_PATH=/app/data/agent_state.db' in dockerfile
    assert 'CHROMA_DB_PATH=/app/data/chroma_db' in dockerfile
    assert 'FEEDBACK_DATA_DIR=/app/data/feedback' in dockerfile
    assert 'FEEDBACK_STORE_DIR=/app/data/feedback' in dockerfile
    assert 'FINETUNE_OUTPUT_DIR=/app/data/finetune' in dockerfile
    assert 'GRAPH_STORE_PATH=/app/data/graph_store' in dockerfile
    assert 'JOB_STORE_DIR=/app/data/jobs' in dockerfile
    assert 'PREFERENCE_DATA_PATH=/app/data/preferences.jsonl' in dockerfile
    assert 'SHARE_PAGE_DIR=/app/data/shared_pages' in dockerfile
    assert 'USER_MEMORY_PATH=/app/data/user_memory' in dockerfile
    assert 'APP_CACHE_DIR=/app/cache' in dockerfile
    assert 'AI_CACHE_DB=/app/cache/ai_cache.db' in dockerfile
    assert 'SCHEDULER_HEARTBEAT_FILE=/tmp/insight-engine-scheduler.heartbeat' in dockerfile
    assert 'CMD ["gunicorn"' in dockerfile
    assert '"app:app"' in dockerfile
    assert '"app:create_app()"' not in dockerfile
    assert 'CMD ["python", "app.py"]' not in dockerfile
