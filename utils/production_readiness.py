"""Production readiness validation helpers."""
from pathlib import Path
from urllib.parse import urlparse


LOCAL_CORS_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
PLACEHOLDER_ENCRYPTION_SECRETS = {'your-encryption-secret-key-here', 'change-me'}
DEVELOPMENT_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https: blob:; "
    "font-src 'self' data: https:; "
    "connect-src 'self' https: wss:; "
    "media-src 'self' https: blob:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
PRODUCTION_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: https: blob:; "
    "font-src 'self' data: https:; "
    "connect-src 'self' https: wss:; "
    "media-src 'self' https: blob:; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "upgrade-insecure-requests"
)
UNSAFE_PRODUCTION_CSP_TOKENS = ("'unsafe-inline'", "'unsafe-eval'")
MIN_PRODUCTION_BACKUP_RETENTION = 7


def default_content_security_policy(flask_env: str) -> str:
    """Return the default CSP for the current runtime environment."""
    if (flask_env or '').strip().lower() == 'production':
        return PRODUCTION_CONTENT_SECURITY_POLICY
    return DEVELOPMENT_CONTENT_SECURITY_POLICY


def parse_cors_origins(raw_origins: str) -> list[str]:
    """Return non-empty CORS origins from a comma-separated env value."""
    return [origin.strip() for origin in (raw_origins or '').split(',') if origin.strip()]


def production_security_errors(
    flask_env: str,
    allowed_origins: list[str],
    metrics_token: str,
    encryption_secret: str,
) -> list[str]:
    """Return production-only security configuration errors."""
    if (flask_env or '').strip().lower() != 'production':
        return []

    errors: list[str] = []

    if not allowed_origins:
        errors.append('CORS_ORIGINS must list production HTTPS origins')
    else:
        for origin in allowed_origins:
            if origin in {'*', 'null', 'file://'}:
                errors.append(f'CORS_ORIGINS contains an unsafe origin: {origin}')
                continue

            parsed = urlparse(origin)
            host = (parsed.hostname or '').lower()
            if parsed.scheme != 'https' or not host:
                errors.append(f'CORS_ORIGINS entries must be HTTPS origins: {origin}')
                continue
            if host in LOCAL_CORS_HOSTS or host.endswith('.local'):
                errors.append(f'CORS_ORIGINS contains a local origin: {origin}')

    if not (metrics_token or '').strip():
        errors.append('METRICS_AUTH_TOKEN is required to protect /metrics')

    normalized_secret = (encryption_secret or '').strip()
    if len(normalized_secret) < 32 or normalized_secret in PLACEHOLDER_ENCRYPTION_SECRETS:
        errors.append('ENCRYPTION_SECRET must be a random secret with at least 32 characters')

    return errors


def content_security_policy_errors(flask_env: str, content_security_policy: str) -> list[str]:
    """Return production CSP errors for unsafe script execution sources."""
    if (flask_env or '').strip().lower() != 'production':
        return []

    csp = content_security_policy or default_content_security_policy(flask_env)
    return [
        f'CONTENT_SECURITY_POLICY must not include {token} in production'
        for token in UNSAFE_PRODUCTION_CSP_TOKENS
        if token in csp
    ]


def validate_production_security_config(
    flask_env: str,
    allowed_origins: list[str],
    metrics_token: str,
    encryption_secret: str,
    content_security_policy: str | None = None,
) -> None:
    """Raise when production security configuration is unsafe.

    검증은 ``flask_env``가 'production'일 때만 동작한다. development/testing 등
    그 외 환경에서는 production 기준을 강제하지 않고 항상 통과(no-op)하므로,
    부팅 경로(``create_app``)에서 호출해도 개발/테스트 환경을 막지 않는다.
    """
    errors = production_security_errors(flask_env, allowed_origins, metrics_token, encryption_secret)
    errors.extend(content_security_policy_errors(
        flask_env,
        content_security_policy or default_content_security_policy(flask_env),
    ))
    if errors:
        raise RuntimeError('; '.join(errors))


def backup_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production backup scheduling/retention configuration errors."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    interval_raw = (env.get('AUTO_BACKUP_INTERVAL_HOURS') or '').strip()
    if not interval_raw:
        errors.append('AUTO_BACKUP_INTERVAL_HOURS is required in production')
    else:
        try:
            interval_hours = int(interval_raw)
            if interval_hours < 1:
                errors.append('AUTO_BACKUP_INTERVAL_HOURS must be at least 1')
        except ValueError:
            errors.append('AUTO_BACKUP_INTERVAL_HOURS must be an integer number of hours')

    max_backups_raw = (env.get('MAX_BACKUPS') or '30').strip()
    try:
        max_backups = int(max_backups_raw)
        if max_backups < MIN_PRODUCTION_BACKUP_RETENTION:
            errors.append(f'MAX_BACKUPS must be at least {MIN_PRODUCTION_BACKUP_RETENTION} in production')
    except ValueError:
        errors.append('MAX_BACKUPS must be an integer')

    backup_dir_raw = (env.get('APP_DATA_BACKUP_DIR') or '').strip()
    if not backup_dir_raw:
        errors.append('APP_DATA_BACKUP_DIR is required for production app_data volume backups')
    else:
        app_data_dir = Path((env.get('APP_DATA_DIR') or 'data').strip()).resolve()
        backup_dir = Path(backup_dir_raw).resolve()
        try:
            backup_dir.relative_to(app_data_dir)
            errors.append('APP_DATA_BACKUP_DIR must be outside APP_DATA_DIR')
        except ValueError:
            pass

    return errors


def production_readiness_errors(env: dict[str, str]) -> list[str]:
    """Return offline deployment readiness errors for environment variables."""
    flask_env = (env.get('FLASK_ENV') or '').strip().lower()
    errors: list[str] = []

    if flask_env != 'production':
        errors.append('FLASK_ENV must be production')

    security_env = env.get('FLASK_ENV', '') if flask_env == 'production' else 'production'
    errors.extend(production_security_errors(
        security_env,
        parse_cors_origins(env.get('CORS_ORIGINS', '')),
        env.get('METRICS_AUTH_TOKEN', ''),
        env.get('ENCRYPTION_SECRET', ''),
    ))
    errors.extend(content_security_policy_errors(
        security_env,
        env.get('CONTENT_SECURITY_POLICY') or default_content_security_policy(security_env),
    ))

    if not (env.get('REDIS_URL') or '').strip():
        errors.append('REDIS_URL is required for shared production rate limits')

    backup_env = dict(env)
    backup_env['FLASK_ENV'] = security_env
    errors.extend(backup_configuration_errors(backup_env))

    return errors
