"""Runtime readiness endpoint and dependency checks."""
import os
from pathlib import Path
import time
from unittest.mock import patch

from app import create_app
from utils.app_data_backup import backup_manifest_path, create_app_data_backup
from utils.runtime_readiness import runtime_readiness_report


SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'
SAFE_GIT_SHA = 'abcdef1234567890abcdef1234567890abcdef12'


def _production_env(tmp_path):
    return {
        'FLASK_ENV': 'production',
        'AUTH_MODE': 'edge',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'BASIC_AUTH_USER': 'ci-admin',
        'BASIC_AUTH_HASH': '$2a$14$cihashplaceholdercihashplaceholdercihashplaceholdercihashp',
        'SECRET_KEY': SAFE_SECRET_KEY,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'PUBLISH_QUEUE_BACKEND': 'redis',
        'PUBLISH_QUEUE_REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'APP_DATA_BACKUP_MAX_AGE_HOURS': '12',
        'MAX_BACKUPS': '30',
        'APP_DATA_DIR': str(tmp_path / 'app_data'),
        'AGENT_DB_PATH': str(tmp_path / 'app_data' / 'agent_state.db'),
        'CHROMA_DB_PATH': str(tmp_path / 'app_data' / 'chroma_db'),
        'FEEDBACK_DATA_DIR': str(tmp_path / 'app_data' / 'feedback'),
        'FEEDBACK_STORE_DIR': str(tmp_path / 'app_data' / 'feedback'),
        'FINETUNE_OUTPUT_DIR': str(tmp_path / 'app_data' / 'finetune'),
        'GRAPH_STORE_PATH': str(tmp_path / 'app_data' / 'graph_store'),
        'JOB_STORE_DIR': str(tmp_path / 'app_data' / 'jobs'),
        'PREFERENCE_DATA_PATH': str(tmp_path / 'app_data' / 'preferences.jsonl'),
        'SHARE_PAGE_DIR': str(tmp_path / 'app_data' / 'shared_pages'),
        'USER_MEMORY_PATH': str(tmp_path / 'app_data' / 'user_memory'),
        'APP_CACHE_DIR': str(tmp_path / 'app_cache'),
        'AI_CACHE_DB': str(tmp_path / 'app_cache' / 'ai_cache.db'),
        'APP_DATA_BACKUP_DIR': str(tmp_path / 'backups'),
        'CONTENT_BACKUP_DIR': str(tmp_path / 'backups' / 'content-library'),
        'APP_DATA_BACKUP_REPLICA_DIR': str(tmp_path / 'backup_replica'),
        'SCHEDULER_HEARTBEAT_FILE': str(tmp_path / 'scheduler.heartbeat'),
        'ZAI_API_KEY': 'test-zai-key',
        'APP_VERSION': 'v2.0',
        'APP_RELEASE': SAFE_GIT_SHA,
        'GIT_SHA': SAFE_GIT_SHA,
        'BUILD_TIME': '2026-06-27T08:00:00Z',
    }


def _write_scheduler_heartbeat(env, age_seconds=0):
    heartbeat = Path(env['SCHEDULER_HEARTBEAT_FILE'])
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text('2026-06-27T08:00:00Z', encoding='utf-8')
    if age_seconds:
        modified = time.time() - age_seconds
        os.utime(heartbeat, (modified, modified))


def _create_recent_backups(env):
    source = env['APP_DATA_DIR']
    create_app_data_backup(
        source,
        env['APP_DATA_BACKUP_DIR'],
        replica_dir=env['APP_DATA_BACKUP_REPLICA_DIR'],
    )
    _write_scheduler_heartbeat(env)


def test_runtime_readiness_passes_with_writable_paths_and_redis(tmp_path):
    env = _production_env(tmp_path)
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'ready'
    assert report['components']['production_config']['status'] == 'ok'
    assert report['components']['app_data']['status'] == 'ok'
    assert report['components']['app_data_runtime_paths']['status'] == 'ok'
    assert report['components']['app_data_runtime_paths']['target_count'] == 10
    assert report['components']['app_cache']['status'] == 'ok'
    assert report['components']['ai_cache']['status'] == 'ok'
    assert report['components']['app_data_backup']['status'] == 'ok'
    assert report['components']['app_data_backup_freshness']['status'] == 'ok'
    assert report['components']['content_backup']['status'] == 'ok'
    assert report['components']['app_data_backup_replica']['status'] == 'ok'
    assert report['components']['app_data_backup_replica_freshness']['status'] == 'ok'
    assert report['components']['redis']['status'] == 'ok'
    assert report['components']['error_tracking']['status'] == 'skipped'


def test_runtime_readiness_fails_when_production_config_is_incomplete(tmp_path):
    env = _production_env(tmp_path)
    env['BASIC_AUTH_HASH'] = 'plaintext'
    (tmp_path / 'app_data').mkdir()
    _create_recent_backups(env)

    report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['production_config']['status'] == 'error'
    assert report['components']['production_config']['error_count'] >= 1


def test_runtime_readiness_fails_when_runtime_data_subpath_is_not_writable(tmp_path):
    env = _production_env(tmp_path)
    app_data = Path(env['APP_DATA_DIR'])
    app_data.mkdir()
    blocked_graph_store = app_data / 'graph_store'
    blocked_graph_store.write_text('not-a-directory', encoding='utf-8')
    env['GRAPH_STORE_PATH'] = str(blocked_graph_store)
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['production_config']['status'] == 'ok'
    assert report['components']['app_data_runtime_paths']['status'] == 'error'
    assert report['components']['app_data_runtime_paths']['failed_targets'] == ['GRAPH_STORE_PATH']


def test_runtime_readiness_fails_when_redis_ping_fails(tmp_path):
    env = _production_env(tmp_path)
    env['REDIS_URL'] = 'redis://redis.example.invalid:6379/0'
    env['PUBLISH_QUEUE_REDIS_URL'] = 'redis://redis.example.invalid:6379/0'
    (tmp_path / 'app_data').mkdir()
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.side_effect = TimeoutError('timeout')
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['redis']['status'] == 'error'
    assert 'TimeoutError' in report['components']['redis']['message']


def test_runtime_readiness_fails_when_app_cache_dir_missing_in_production(tmp_path):
    env = _production_env(tmp_path)
    env['APP_CACHE_DIR'] = ''
    (tmp_path / 'app_data').mkdir()
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['production_config']['status'] == 'error'
    assert report['components']['app_cache']['status'] == 'error'
    assert 'cache directory' in report['components']['app_cache']['message']


def test_runtime_readiness_fails_when_backup_replica_is_missing(tmp_path):
    env = _production_env(tmp_path)
    env['APP_DATA_BACKUP_REPLICA_DIR'] = ''
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    create_app_data_backup(env['APP_DATA_DIR'], env['APP_DATA_BACKUP_DIR'])
    _write_scheduler_heartbeat(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['app_data_backup_replica']['status'] == 'error'


def test_runtime_readiness_fails_when_required_error_tracking_is_missing(tmp_path):
    env = _production_env(tmp_path)
    env['ERROR_TRACKING_REQUIRED'] = 'true'
    (tmp_path / 'app_data').mkdir()
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['error_tracking']['status'] == 'error'
    assert 'SENTRY_DSN' in report['components']['error_tracking']['message']


def test_runtime_readiness_fails_when_production_uses_memory_redis(tmp_path):
    env = _production_env(tmp_path)
    env['REDIS_URL'] = 'memory://'
    env['PUBLISH_QUEUE_REDIS_URL'] = 'memory://'
    (tmp_path / 'app_data').mkdir()
    _create_recent_backups(env)

    report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['production_config']['status'] == 'error'
    assert report['components']['redis']['status'] == 'error'
    assert 'memory redis' in report['components']['redis']['message']


def test_runtime_readiness_fails_when_backup_archive_is_missing(tmp_path):
    env = _production_env(tmp_path)
    (tmp_path / 'app_data').mkdir()
    _write_scheduler_heartbeat(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['app_data_backup_freshness']['status'] == 'error'
    assert 'no backup archives' in report['components']['app_data_backup_freshness']['message']


def test_runtime_readiness_fails_when_backup_archive_is_stale(tmp_path):
    env = _production_env(tmp_path)
    env['APP_DATA_BACKUP_MAX_AGE_HOURS'] = '1'
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    payload = create_app_data_backup(
        env['APP_DATA_DIR'],
        env['APP_DATA_BACKUP_DIR'],
        replica_dir=env['APP_DATA_BACKUP_REPLICA_DIR'],
    )
    stale_time = time.time() - 3 * 3600
    os.utime(payload['archive_path'], (stale_time, stale_time))
    os.utime(payload['replica']['replica_path'], (stale_time, stale_time))
    _write_scheduler_heartbeat(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['app_data_backup_freshness']['status'] == 'error'
    assert report['components']['app_data_backup_replica_freshness']['status'] == 'error'
    assert 'stale' in report['components']['app_data_backup_freshness']['message']


def test_runtime_readiness_fails_when_latest_backup_manifest_is_missing(tmp_path):
    env = _production_env(tmp_path)
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    payload = create_app_data_backup(
        env['APP_DATA_DIR'],
        env['APP_DATA_BACKUP_DIR'],
        replica_dir=env['APP_DATA_BACKUP_REPLICA_DIR'],
    )
    backup_manifest_path(payload['archive_path']).unlink()
    _write_scheduler_heartbeat(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['app_data_backup_freshness']['status'] == 'error'
    assert 'sidecar manifest' in report['components']['app_data_backup_freshness']['message']


def test_runtime_readiness_checks_scheduler_heartbeat_when_enabled(tmp_path):
    env = _production_env(tmp_path)
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    _create_recent_backups(env)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'ready'
    assert report['components']['scheduler']['status'] == 'ok'
    assert report['components']['scheduler']['max_age_seconds'] == 120


def test_runtime_readiness_fails_when_scheduler_heartbeat_is_missing(tmp_path):
    env = _production_env(tmp_path)
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    _create_recent_backups(env)
    Path(env['SCHEDULER_HEARTBEAT_FILE']).unlink()

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['scheduler']['status'] == 'error'
    assert 'missing' in report['components']['scheduler']['message']


def test_runtime_readiness_fails_when_scheduler_heartbeat_is_stale(tmp_path):
    env = _production_env(tmp_path)
    env['SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS'] = '60'
    (tmp_path / 'app_data').mkdir()
    (tmp_path / 'app_data' / 'state.json').write_text('{}', encoding='utf-8')
    _create_recent_backups(env)
    _write_scheduler_heartbeat(env, age_seconds=90)

    with patch('redis.from_url') as from_url:
        from_url.return_value.ping.return_value = True
        report = runtime_readiness_report(env)

    assert report['status'] == 'not_ready'
    assert report['components']['scheduler']['status'] == 'error'
    assert 'stale' in report['components']['scheduler']['message']
    assert report['components']['scheduler']['max_age_seconds'] == 60


def test_ready_endpoint_returns_200_when_ready():
    app = create_app({'TESTING': True})
    client = app.test_client()

    with patch('routes.utility.operations.runtime_readiness_report', return_value={
        'status': 'ready',
        'components': {},
        'duration_ms': 0.1,
    }):
        resp = client.get('/ready')

    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ready'


def test_ready_endpoint_returns_503_when_not_ready():
    app = create_app({'TESTING': True})
    client = app.test_client()

    with patch('routes.utility.operations.runtime_readiness_report', return_value={
        'status': 'not_ready',
        'components': {'redis': {'status': 'error', 'message': 'redis ping failed'}},
        'duration_ms': 0.1,
    }):
        resp = client.get('/ready')

    assert resp.status_code == 503
    assert resp.get_json()['status'] == 'not_ready'


def test_public_production_ready_omits_component_diagnostics(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    app = create_app({'TESTING': True})
    client = app.test_client()

    with patch('routes.utility.operations.runtime_readiness_report', return_value={
        'status': 'ready',
        'components': {'redis': {'status': 'ok', 'message': 'redis ping succeeded'}},
        'duration_ms': 0.1,
    }):
        resp = client.get('/ready')

    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload == {'status': 'ready'}
    assert resp.headers['Cache-Control'] == 'no-store'


def test_production_ready_includes_diagnostics_with_metrics_token(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    app = create_app({'TESTING': True})
    client = app.test_client()

    with patch('routes.utility.operations.runtime_readiness_report', return_value={
        'status': 'ready',
        'components': {'redis': {'status': 'ok', 'message': 'redis ping succeeded'}},
        'duration_ms': 0.1,
    }):
        resp = client.get('/ready', headers={'Authorization': f'Bearer {SAFE_METRICS_AUTH_TOKEN}'})

    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload['status'] == 'ready'
    assert payload['components']['redis']['status'] == 'ok'
    assert payload['duration_ms'] == 0.1
