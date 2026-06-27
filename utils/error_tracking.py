"""Optional error tracking integration with privacy-safe defaults."""
from __future__ import annotations

import logging
import os
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from utils.release_metadata import release_metadata


REDACTED = '[Filtered]'
SENSITIVE_KEY_PARTS = (
    'authorization',
    'cookie',
    'csrf',
    'passwd',
    'password',
    'secret',
    'session',
    'token',
    'api_key',
    'apikey',
    'access_key',
)
BODY_KEYS = {'body', 'data', 'raw_body'}
ERROR_TRACKING_ENV_KEYS = {
    'APP_RELEASE',
    'APP_VERSION',
    'BUILD_SHA',
    'BUILD_TIME',
    'ERROR_TRACKING_REQUIRED',
    'GIT_SHA',
    'SENTRY_DSN',
    'SENTRY_ENABLED_IN_TESTS',
    'SENTRY_ENVIRONMENT',
    'SENTRY_PROFILES_SAMPLE_RATE',
    'SENTRY_RELEASE',
    'SENTRY_TRACES_SAMPLE_RATE',
}

logger = logging.getLogger(__name__)


def _truthy(value: Any) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).replace('-', '_').lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_query_string(query: str) -> str:
    if not query:
        return query

    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return query
    return urlencode([
        (key, REDACTED if _sensitive_key(key) else value)
        for key, value in pairs
    ])


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.query:
        return value
    return urlunsplit(parsed._replace(query=_redact_query_string(parsed.query)))


def _sanitize_value(value: Any, parent_key: str | None = None) -> Any:
    if parent_key and _sensitive_key(parent_key):
        return REDACTED

    if parent_key in BODY_KEYS and isinstance(value, str):
        return REDACTED

    if parent_key == 'query_string' and isinstance(value, str):
        return _redact_query_string(value)

    if parent_key == 'url' and isinstance(value, str):
        return _redact_url(value)

    if isinstance(value, dict):
        return {
            key: _sanitize_value(child, str(key))
            for key, child in value.items()
        }

    if isinstance(value, list):
        return [_sanitize_value(child, parent_key) for child in value]

    if isinstance(value, tuple):
        return tuple(_sanitize_value(child, parent_key) for child in value)

    return value


def sanitize_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Redact secrets and request bodies before an error event leaves the app."""
    return _sanitize_value(event)


def _sample_rate(env: dict[str, str], key: str, default: float) -> float:
    raw = (env.get(key) or '').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning('Invalid %s value; using %.2f', key, default)
        return default
    if value < 0 or value > 1:
        logger.warning('Out-of-range %s value; using %.2f', key, default)
        return default
    return value


def _snapshot_env(app: Any, env: dict[str, str] | None) -> dict[str, str]:
    if env is not None:
        return {key: str(value) for key, value in env.items()}

    snapshot = dict(os.environ)
    app_config = getattr(app, 'config', {})
    for key in ERROR_TRACKING_ENV_KEYS:
        value = app_config.get(key)
        if value is not None:
            snapshot[key] = str(value)
    return snapshot


def _load_sentry_modules():
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    return sentry_sdk, FlaskIntegration


def init_error_tracking(
    app: Any,
    env: dict[str, str] | None = None,
    module_loader: Callable[[], tuple[Any, Any]] = _load_sentry_modules,
) -> dict[str, Any]:
    """Initialize Sentry when configured and return a non-secret status payload."""
    snapshot = _snapshot_env(app, env)
    required = _truthy(snapshot.get('ERROR_TRACKING_REQUIRED'))
    dsn = (snapshot.get('SENTRY_DSN') or '').strip()
    app_is_testing = bool(getattr(app, 'testing', False) or getattr(app, 'config', {}).get('TESTING'))

    if app_is_testing and not _truthy(snapshot.get('SENTRY_ENABLED_IN_TESTS')):
        status = {
            'status': 'skipped',
            'enabled': False,
            'provider': 'sentry',
            'message': 'disabled in tests',
        }
        app.config['ERROR_TRACKING_STATUS'] = status
        return status

    if not dsn:
        status = {
            'status': 'error' if required else 'disabled',
            'enabled': False,
            'provider': 'sentry',
            'message': 'SENTRY_DSN is not configured',
        }
        app.config['ERROR_TRACKING_STATUS'] = status
        if required:
            raise RuntimeError('SENTRY_DSN is required when ERROR_TRACKING_REQUIRED=true')
        return status

    try:
        sentry_sdk, FlaskIntegration = module_loader()
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            environment=(
                snapshot.get('SENTRY_ENVIRONMENT')
                or snapshot.get('FLASK_ENV')
                or 'development'
            ),
            release=snapshot.get('SENTRY_RELEASE') or release_metadata(snapshot)['release'],
            traces_sample_rate=_sample_rate(snapshot, 'SENTRY_TRACES_SAMPLE_RATE', 0.0),
            profiles_sample_rate=_sample_rate(snapshot, 'SENTRY_PROFILES_SAMPLE_RATE', 0.0),
            send_default_pii=False,
            before_send=sanitize_event,
        )
    except Exception as exc:
        status = {
            'status': 'error',
            'enabled': False,
            'provider': 'sentry',
            'message': f'Sentry initialization failed: {exc.__class__.__name__}',
        }
        app.config['ERROR_TRACKING_STATUS'] = status
        app.logger.exception('Sentry error tracking initialization failed')
        if required:
            raise RuntimeError('Sentry error tracking initialization failed') from exc
        return status

    status = {
        'status': 'ok',
        'enabled': True,
        'provider': 'sentry',
        'message': 'Sentry error tracking enabled',
    }
    app.config['ERROR_TRACKING_STATUS'] = status
    app.logger.info('Sentry error tracking enabled')
    return status
