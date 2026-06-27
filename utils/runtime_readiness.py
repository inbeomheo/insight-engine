"""Runtime readiness checks for production dependencies."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any

from utils.app_data_backup import latest_app_data_backup
from utils.production_readiness import (
    error_tracking_configuration_errors,
    production_readiness_errors,
)


def _component(status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {'status': status, 'message': message}
    payload.update(extra)
    return payload


def _write_probe(directory: str | Path, name: str) -> dict[str, Any]:
    path = Path(directory).resolve()
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=name, dir=path, delete=False) as tmp:
            tmp.write(b'1')
            tmp_path = Path(tmp.name)
        tmp_path.unlink(missing_ok=True)
        return _component('ok', 'writable')
    except Exception as exc:
        return _component('error', f'not writable: {exc.__class__.__name__}')


def _redis_check(env: dict[str, str]) -> dict[str, Any]:
    redis_url = (env.get('PUBLISH_QUEUE_REDIS_URL') or env.get('REDIS_URL') or '').strip()
    if not redis_url:
        if (env.get('FLASK_ENV') or '').strip().lower() == 'production':
            return _component('error', 'redis url is required')
        return _component('skipped', 'redis url is not configured')

    if redis_url.startswith('memory://'):
        if (env.get('FLASK_ENV') or '').strip().lower() == 'production':
            return _component('error', 'memory redis substitute is not allowed in production')
        return _component('skipped', 'in-memory redis substitute configured')

    try:
        import redis

        client = redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=False,
        )
        client.ping()
        return _component('ok', 'redis ping succeeded')
    except Exception as exc:
        return _component('error', f'redis ping failed: {exc.__class__.__name__}')


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _int_env(env: dict[str, str], name: str) -> int | None:
    raw = (env.get(name) or '').strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _backup_max_age_hours(env: dict[str, str]) -> int | None:
    configured = _int_env(env, 'APP_DATA_BACKUP_MAX_AGE_HOURS')
    if configured:
        return configured
    interval = _int_env(env, 'AUTO_BACKUP_INTERVAL_HOURS')
    if interval:
        return interval * 2
    return None


def _backup_freshness_check(directory: str | Path, env: dict[str, str]) -> dict[str, Any]:
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return _component('skipped', 'backup freshness is only enforced in production')

    max_age_hours = _backup_max_age_hours(env)
    if not max_age_hours:
        return _component('error', 'backup max age is not configured')

    try:
        latest = latest_app_data_backup(directory)
    except Exception as exc:
        return _component('error', f'backup archive check failed: {exc.__class__.__name__}')

    if not latest:
        return _component('error', 'no backup archives found')
    if latest['size_bytes'] <= 0:
        return _component('error', 'latest backup archive is empty', archive=latest['archive'])
    if not latest['is_zipfile']:
        return _component('error', 'latest backup archive is not a valid zip', archive=latest['archive'])
    if not latest.get('manifest_present'):
        return _component('error', 'latest backup sidecar manifest is missing', archive=latest['archive'])
    if not latest.get('manifest_valid'):
        return _component(
            'error',
            'latest backup sidecar manifest is invalid',
            archive=latest['archive'],
            manifest_error=latest.get('manifest_error') or 'invalid',
        )

    max_age_seconds = max_age_hours * 3600
    if latest['age_seconds'] > max_age_seconds:
        return _component(
            'error',
            'latest backup archive is stale',
            archive=latest['archive'],
            age_seconds=latest['age_seconds'],
            max_age_seconds=max_age_seconds,
        )

    return _component(
        'ok',
        'latest backup archive is fresh',
        archive=latest['archive'],
        age_seconds=latest['age_seconds'],
        max_age_seconds=max_age_seconds,
        modified_at=latest['modified_at'],
    )


def _error_tracking_check(env: dict[str, str]) -> dict[str, Any]:
    errors = error_tracking_configuration_errors(env)
    if errors:
        return _component('error', '; '.join(errors))

    if (env.get('SENTRY_DSN') or '').strip():
        return _component('ok', 'Sentry DSN configured')

    if _truthy(env.get('ERROR_TRACKING_REQUIRED')):
        return _component('error', 'SENTRY_DSN is required')

    return _component('skipped', 'SENTRY_DSN is not configured')


def _scheduler_check(env: dict[str, str]) -> dict[str, Any]:
    if not _truthy(env.get('SCHEDULER_ENABLED') or 'true'):
        return _component('skipped', 'scheduler is disabled')

    heartbeat_raw = (env.get('SCHEDULER_HEARTBEAT_FILE') or '').strip()
    if not heartbeat_raw:
        if (env.get('FLASK_ENV') or '').strip().lower() == 'production':
            return _component('error', 'scheduler heartbeat file is required')
        return _component('skipped', 'scheduler heartbeat file is not configured')

    max_age = _int_env(env, 'SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS') or 120
    heartbeat = Path(heartbeat_raw)
    try:
        stat = heartbeat.stat()
    except FileNotFoundError:
        return _component('error', 'scheduler heartbeat file is missing')
    except Exception as exc:
        return _component('error', f'scheduler heartbeat check failed: {exc.__class__.__name__}')

    age_seconds = time.time() - stat.st_mtime
    if age_seconds > max_age:
        return _component(
            'error',
            'scheduler heartbeat is stale',
            age_seconds=round(age_seconds, 1),
            max_age_seconds=max_age,
        )
    return _component(
        'ok',
        'scheduler heartbeat is fresh',
        age_seconds=round(age_seconds, 1),
        max_age_seconds=max_age,
    )


def _content_backup_dir(env: dict[str, str]) -> str:
    configured = (env.get('CONTENT_BACKUP_DIR') or '').strip()
    if configured:
        return configured

    backup_dir = (env.get('APP_DATA_BACKUP_DIR') or '').strip()
    if backup_dir:
        return str(Path(backup_dir) / 'content-library')

    return ''


def _runtime_data_probe(env: dict[str, str], app_data_dir: str | Path) -> dict[str, Any]:
    app_data = Path(app_data_dir)
    targets: dict[str, tuple[Path, bool]] = {
        'AGENT_DB_PATH': (app_data / 'agent_state.db', True),
        'CHROMA_DB_PATH': (app_data / 'chroma_db', False),
        'FEEDBACK_DATA_DIR': (app_data / 'feedback', False),
        'FEEDBACK_STORE_DIR': (app_data / 'feedback', False),
        'FINETUNE_OUTPUT_DIR': (app_data / 'finetune', False),
        'GRAPH_STORE_PATH': (app_data / 'graph_store', False),
        'JOB_STORE_DIR': (app_data / 'jobs', False),
        'PREFERENCE_DATA_PATH': (app_data / 'preferences.jsonl', True),
        'SHARE_PAGE_DIR': (app_data / 'shared_pages', False),
        'USER_MEMORY_PATH': (app_data / 'user_memory', False),
    }

    failed_targets: list[str] = []
    for env_name, (default_path, is_file) in targets.items():
        configured = (env.get(env_name) or '').strip()
        target = Path(configured) if configured else default_path
        probe_dir = target.parent if is_file else target
        probe = _write_probe(probe_dir, f'readiness-{env_name.lower()}-')
        if probe['status'] != 'ok':
            failed_targets.append(env_name)

    if failed_targets:
        return _component(
            'error',
            'runtime app data paths are not writable',
            failed_targets=failed_targets,
            target_count=len(targets),
        )
    return _component('ok', 'runtime app data paths are writable', target_count=len(targets))


def runtime_readiness_report(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Return a non-secret runtime readiness report.

    The report is designed for load balancers and deployment smoke checks. It does
    not include raw secret values, URLs, or filesystem paths.
    """
    snapshot = dict(os.environ if env is None else env)
    started = time.perf_counter()

    components: dict[str, dict[str, Any]] = {}

    config_errors = production_readiness_errors(snapshot)
    if (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['production_config'] = (
            _component('error', 'production configuration is incomplete', error_count=len(config_errors))
            if config_errors else
            _component('ok', 'production configuration passed')
        )
    else:
        components['production_config'] = _component('skipped', 'not running in production mode')

    app_data_dir = (snapshot.get('APP_DATA_DIR') or 'data').strip()
    components['app_data'] = _write_probe(app_data_dir, 'readiness-app-data-')
    components['app_data_runtime_paths'] = _runtime_data_probe(snapshot, app_data_dir)

    app_cache_dir = (snapshot.get('APP_CACHE_DIR') or snapshot.get('CACHE_DIR') or '').strip()
    if app_cache_dir:
        components['app_cache'] = _write_probe(app_cache_dir, 'readiness-app-cache-')
    elif (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['app_cache'] = _component('error', 'cache directory is required')
    else:
        components['app_cache'] = _component('skipped', 'cache directory is not configured')

    ai_cache_db = (snapshot.get('AI_CACHE_DB') or '').strip()
    if ai_cache_db:
        components['ai_cache'] = _write_probe(
            Path(ai_cache_db).parent,
            'readiness-ai-cache-',
        )
    elif app_cache_dir:
        components['ai_cache'] = _write_probe(app_cache_dir, 'readiness-ai-cache-')
    elif (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['ai_cache'] = _component('error', 'cache directory is required')
    else:
        components['ai_cache'] = _component('skipped', 'cache directory is not configured')

    backup_dir = (snapshot.get('APP_DATA_BACKUP_DIR') or '').strip()
    if backup_dir:
        components['app_data_backup'] = _write_probe(backup_dir, 'readiness-backup-')
        components['app_data_backup_freshness'] = _backup_freshness_check(backup_dir, snapshot)
    elif (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['app_data_backup'] = _component('error', 'backup directory is required')
        components['app_data_backup_freshness'] = _component('error', 'backup directory is required')
    else:
        components['app_data_backup'] = _component('skipped', 'backup directory is not configured')
        components['app_data_backup_freshness'] = _component('skipped', 'backup directory is not configured')

    content_backup_dir = _content_backup_dir(snapshot)
    if content_backup_dir:
        components['content_backup'] = _write_probe(
            content_backup_dir,
            'readiness-content-backup-',
        )
    elif (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['content_backup'] = _component('error', 'backup directory is required')
    else:
        components['content_backup'] = _component(
            'skipped',
            'backup directory is not configured',
        )

    replica_dir = (snapshot.get('APP_DATA_BACKUP_REPLICA_DIR') or '').strip()
    if replica_dir:
        components['app_data_backup_replica'] = _write_probe(replica_dir, 'readiness-backup-replica-')
        components['app_data_backup_replica_freshness'] = _backup_freshness_check(replica_dir, snapshot)
    elif (snapshot.get('FLASK_ENV') or '').strip().lower() == 'production':
        components['app_data_backup_replica'] = _component('error', 'backup replica directory is required')
        components['app_data_backup_replica_freshness'] = _component(
            'error',
            'backup replica directory is required',
        )
    else:
        components['app_data_backup_replica'] = _component(
            'skipped',
            'backup replica directory is not configured',
        )
        components['app_data_backup_replica_freshness'] = _component(
            'skipped',
            'backup replica directory is not configured',
        )

    components['redis'] = _redis_check(snapshot)
    components['error_tracking'] = _error_tracking_check(snapshot)
    components['scheduler'] = _scheduler_check(snapshot)

    is_ready = all(component['status'] in {'ok', 'skipped'} for component in components.values())
    return {
        'status': 'ready' if is_ready else 'not_ready',
        'components': components,
        'duration_ms': round((time.perf_counter() - started) * 1000, 1),
    }
