"""Production readiness validation helpers."""
from pathlib import Path
import re
from urllib.parse import urlparse


# Address deny-list values, not a network bind target.
LOCAL_CORS_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}  # nosec
PLACEHOLDER_ENCRYPTION_SECRETS = {'your-encryption-secret-key-here', 'change-me'}
PLACEHOLDER_SUPABASE_URLS = {'https://your-project.supabase.co'}
PLACEHOLDER_SUPABASE_PUBLIC_KEYS = {
    'your-publishable-key',
    'your-anon-key',
    'change-me',
}
PLACEHOLDER_SUPABASE_SECRET_KEYS = {
    'your-secret-key',
    'your-service-role-key',
    'change-me',
}
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
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SUPABASE_SCHEMA_VERSION = 9
SUPABASE_SCHEMA_VERSION_RPC = 'insight_engine_schema_version'


def _declared_supabase_schema_version(sql: str) -> int | None:
    """Return the constant version exposed by the non-mutating readiness RPC."""
    match = re.search(
        rf'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.'
        rf'{re.escape(SUPABASE_SCHEMA_VERSION_RPC)}\s*\(\s*\)'
        r'[\s\S]*?AS\s+\$\$\s*SELECT\s+([0-9]+)\s*;\s*\$\$\s*;',
        sql,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def supabase_schema_contract_errors(project_root: Path | None = None) -> list[str]:
    """Return errors when bundled SQL cannot prove the required schema version.

    This is deliberately an offline, read-only artifact check. The live database
    version is verified separately by ``/ready`` through the anon-key RPC.
    """
    root = (project_root or PROJECT_ROOT).resolve()
    migrations_dir = root / 'supabase' / 'migrations'
    schema_path = root / 'supabase' / 'schema.sql'
    errors: list[str] = []

    migration_files: list[tuple[int, Path]] = []
    if migrations_dir.is_dir():
        for path in migrations_dir.glob('*.sql'):
            version_match = re.match(r'^(\d+)_', path.name)
            if version_match:
                migration_files.append((int(version_match.group(1)), path))

    if not migration_files:
        errors.append('Supabase migrations are missing from the deployment artifact')
        required_migrations: list[Path] = []
    else:
        latest_version = max(version for version, _path in migration_files)
        if latest_version != REQUIRED_SUPABASE_SCHEMA_VERSION:
            errors.append(
                'REQUIRED_SUPABASE_SCHEMA_VERSION must match the latest bundled '
                f'migration version ({latest_version})'
            )
        required_migrations = [
            path
            for version, path in migration_files
            if version == REQUIRED_SUPABASE_SCHEMA_VERSION
        ]
        if not required_migrations:
            errors.append(
                f'Supabase migration {REQUIRED_SUPABASE_SCHEMA_VERSION:03d} is missing '
                'from the deployment artifact'
            )

    contract_paths = [schema_path, *required_migrations]
    for path in contract_paths:
        if not path.is_file():
            errors.append(f'Supabase schema contract file is missing: {path.relative_to(root)}')
            continue
        declared_version = _declared_supabase_schema_version(
            path.read_text(encoding='utf-8')
        )
        if declared_version != REQUIRED_SUPABASE_SCHEMA_VERSION:
            errors.append(
                f'{path.relative_to(root)} must expose '
                f'{SUPABASE_SCHEMA_VERSION_RPC}() = '
                f'{REQUIRED_SUPABASE_SCHEMA_VERSION}'
            )

    return errors


def default_content_security_policy(flask_env: str) -> str:
    """Return the default CSP for the current runtime environment."""
    if (flask_env or '').strip().lower() == 'production':
        return PRODUCTION_CONTENT_SECURITY_POLICY
    return DEVELOPMENT_CONTENT_SECURITY_POLICY


def parse_cors_origins(raw_origins: str) -> list[str]:
    """Return non-empty CORS origins from a comma-separated env value."""
    return [origin.strip() for origin in (raw_origins or '').split(',') if origin.strip()]


def supabase_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return required production Supabase authentication config errors."""
    errors: list[str] = []
    supabase_url = (env.get('SUPABASE_URL') or '').strip()
    supabase_public_key = (
        env.get('SUPABASE_PUBLISHABLE_KEY')
        or env.get('SUPABASE_ANON_KEY')
        or ''
    ).strip()
    supabase_secret_key = (
        env.get('SUPABASE_SECRET_KEY')
        or env.get('SUPABASE_SERVICE_ROLE_KEY')
        or ''
    ).strip()

    if not supabase_url:
        errors.append('SUPABASE_URL is required for production authentication')
    elif supabase_url in PLACEHOLDER_SUPABASE_URLS:
        errors.append('SUPABASE_URL must not use the example placeholder')
    else:
        parsed = urlparse(supabase_url)
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme != 'https' or not host:
            errors.append('SUPABASE_URL must be a valid HTTPS URL')
        elif host in LOCAL_CORS_HOSTS or host.endswith('.local'):
            errors.append('SUPABASE_URL must not use a local address in production')

    if not supabase_public_key:
        errors.append(
            'SUPABASE_PUBLISHABLE_KEY or legacy SUPABASE_ANON_KEY is required '
            'for production authentication'
        )
    elif supabase_public_key in PLACEHOLDER_SUPABASE_PUBLIC_KEYS:
        errors.append(
            'Supabase publishable/anon key must not use the example placeholder'
        )

    if not supabase_secret_key:
        errors.append(
            'SUPABASE_SECRET_KEY or legacy SUPABASE_SERVICE_ROLE_KEY is required '
            'for production admin and background operations'
        )
    elif supabase_secret_key in PLACEHOLDER_SUPABASE_SECRET_KEYS:
        errors.append(
            'Supabase secret/service_role key must not use the example placeholder'
        )

    return errors


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


def public_origin_errors(flask_env: str, public_origin: str) -> list[str]:
    """Return errors for the canonical externally visible production origin."""
    if (flask_env or '').strip().lower() != 'production':
        return []

    origin = (public_origin or '').strip()
    if not origin:
        return ['PUBLIC_ORIGIN is required in production']

    parsed = urlparse(origin)
    host = (parsed.hostname or '').lower().rstrip('.')
    try:
        parsed.port
    except ValueError:
        return ['PUBLIC_ORIGIN must be a valid HTTPS origin']
    if parsed.scheme != 'https' or not host:
        return ['PUBLIC_ORIGIN must be a valid HTTPS origin']
    if parsed.username or parsed.password:
        return ['PUBLIC_ORIGIN must not contain user information']
    if parsed.path not in {'', '/'} or parsed.params or parsed.query or parsed.fragment:
        return ['PUBLIC_ORIGIN must not contain a path, query, or fragment']
    if host in LOCAL_CORS_HOSTS or host.endswith('.local'):
        return ['PUBLIC_ORIGIN must not use a local address in production']
    return []


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
    public_origin: str = '',
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
    errors.extend(public_origin_errors(flask_env, public_origin))
    if errors:
        raise RuntimeError('; '.join(errors))


def backup_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production backup scheduling/retention configuration errors."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    portable_enabled = (env.get('AUTO_BACKUP_ENABLED') or '').strip().lower()
    platform_enabled = (
        env.get('PLATFORM_VOLUME_BACKUPS_ENABLED') or ''
    ).strip().lower()

    if platform_enabled not in {'true', 'false'}:
        errors.append('PLATFORM_VOLUME_BACKUPS_ENABLED must be explicitly true or false')
    elif platform_enabled != 'true':
        errors.append(
            'PLATFORM_VOLUME_BACKUPS_ENABLED must be true in production to '
            'provide an independent recovery boundary'
        )

    if portable_enabled not in {'true', 'false'}:
        errors.append('AUTO_BACKUP_ENABLED must be explicitly true or false')
        return errors
    if portable_enabled == 'false':
        return errors

    interval_raw = (env.get('AUTO_BACKUP_INTERVAL_HOURS') or '').strip()
    if not interval_raw:
        errors.append('AUTO_BACKUP_INTERVAL_HOURS is required in production')
    else:
        try:
            interval_hours = int(interval_raw)
            if interval_hours < 1:
                errors.append('AUTO_BACKUP_INTERVAL_HOURS must be at least 1')
            elif interval_hours > 720:
                errors.append('AUTO_BACKUP_INTERVAL_HOURS must be at most 720')
        except ValueError:
            errors.append('AUTO_BACKUP_INTERVAL_HOURS must be an integer number of hours')

    max_backups_raw = (env.get('MAX_BACKUPS') or '30').strip()
    try:
        max_backups = int(max_backups_raw)
        if max_backups < MIN_PRODUCTION_BACKUP_RETENTION:
            errors.append(f'MAX_BACKUPS must be at least {MIN_PRODUCTION_BACKUP_RETENTION} in production')
        elif max_backups > 10_000:
            errors.append('MAX_BACKUPS must be at most 10000 in production')
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


def production_readiness_errors(
    env: dict[str, str],
    *,
    project_root: Path | None = None,
) -> list[str]:
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
    errors.extend(public_origin_errors(security_env, env.get('PUBLIC_ORIGIN', '')))
    errors.extend(supabase_configuration_errors(env))
    errors.extend(supabase_schema_contract_errors(project_root))

    if not (env.get('REDIS_URL') or '').strip():
        errors.append('REDIS_URL is required for shared production rate limits')

    backup_env = dict(env)
    backup_env['FLASK_ENV'] = security_env
    errors.extend(backup_configuration_errors(backup_env))

    return errors
