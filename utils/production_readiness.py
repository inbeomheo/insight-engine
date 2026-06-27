"""Production readiness validation helpers."""
from datetime import datetime
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlparse


LOCAL_CORS_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
PLACEHOLDER_ENCRYPTION_SECRETS = {'your-encryption-secret-key-here', 'change-me'}
PLACEHOLDER_APP_SECRETS = {
    'change-me',
    'dev-secret',
    'development-secret',
    'secret',
    'your-secret-key',
    'your-flask-secret-key',
}
PLACEHOLDER_METRICS_TOKENS = {'change-me', 'metrics-token', 'your-metrics-auth-token'}
PLACEHOLDER_SUPPORT_HANDOFF_SECRETS = {'change-me', 'support-handoff-secret', 'your-support-handoff-secret'}
PLACEHOLDER_BASIC_AUTH_VALUES = {'', 'admin', 'password', 'change-me', 'your-basic-auth-hash'}
PLACEHOLDER_RELEASE_METADATA_VALUES = {'', 'local', 'unknown', 'dev', 'development', 'test', 'none', 'null'}
PLACEHOLDER_PAYMENT_SECRETS = {
    'change-me',
    'your-stripe-secret-key',
    'your-stripe-webhook-secret',
    'your-paddle-api-key',
    'your-paddle-webhook-secret',
    'your-coinbase-commerce-api-key',
    'your-coinbase-webhook-secret',
}
PLACEHOLDER_BOT_SECRETS = {
    'change-me',
    'your-slack-bot-token',
    'your-slack-signing-secret',
    'your-discord-bot-token',
    'your-discord-public-key',
    'your-telegram-bot-token',
    'your-telegram-webhook-secret',
}
PLACEHOLDER_AUTOMATION_WEBHOOK_SECRETS = {
    'change-me',
    'your-automation-webhook-secret',
    'your-webhook-secret',
}
MIN_PRODUCTION_SECRET_LENGTH = 32
MIN_PRODUCTION_SECRET_DISTINCT_CHARS = 8
RELEASE_METADATA_PATTERN = re.compile(r'^[A-Za-z0-9._:/@+-]{1,160}$')
GIT_SHA_PATTERN = re.compile(r'^[0-9a-fA-F]{7,64}$')
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
DEFAULT_PRODUCTION_GENERATION_MODEL = 'zhipuai/GLM-4.5-Air'
DEBUG_ENV_KEYS = ('FLASK_DEBUG', 'DEBUG', 'APP_DEBUG')
MODEL_PROVIDER_ENV_KEYS = {
    'openai': ('OPENAI_API_KEY',),
    'anthropic': ('ANTHROPIC_API_KEY',),
    'gemini': ('GEMINI_API_KEY',),
    'deepseek': ('DEEPSEEK_API_KEY',),
    'zhipuai': ('ZAI_API_KEY', 'ZHIPUAI_API_KEY'),
    'openrouter': ('OPENROUTER_API_KEY',),
    'ollama': ('OLLAMA_BASE_URL',),
}


def _path_within_or_equal(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def default_content_security_policy(flask_env: str) -> str:
    """Return the default CSP for the current runtime environment."""
    if (flask_env or '').strip().lower() == 'production':
        return PRODUCTION_CONTENT_SECURITY_POLICY
    return DEVELOPMENT_CONTENT_SECURITY_POLICY


def parse_cors_origins(raw_origins: str) -> list[str]:
    """Return non-empty CORS origins from a comma-separated env value."""
    return [origin.strip() for origin in (raw_origins or '').split(',') if origin.strip()]


def _is_weak_production_secret(value: str, placeholders: set[str]) -> bool:
    normalized = (value or '').strip()
    return (
        len(normalized) < MIN_PRODUCTION_SECRET_LENGTH
        or normalized.lower() in placeholders
        or len(set(normalized)) < MIN_PRODUCTION_SECRET_DISTINCT_CHARS
    )


def _duplicate_secret_errors(secret_values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for key, value in secret_values.items():
        normalized = (value or '').strip()
        if not normalized:
            continue
        previous_key = seen.get(normalized)
        if previous_key:
            errors.append(f'{key} must not reuse {previous_key}')
            continue
        seen[normalized] = key
    return errors


def production_security_errors(
    flask_env: str,
    allowed_origins: list[str],
    metrics_token: str,
    app_secret: str,
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

            url_error = _public_https_url_error(
                'CORS_ORIGINS',
                origin,
                require_origin=True,
            )
            if url_error:
                errors.append(f'{url_error}: {origin}')

    normalized_metrics_token = (metrics_token or '').strip()
    if _is_weak_production_secret(normalized_metrics_token, PLACEHOLDER_METRICS_TOKENS):
        errors.append('METRICS_AUTH_TOKEN must be a random token with at least 32 characters')

    normalized_app_secret = (app_secret or '').strip()
    if _is_weak_production_secret(normalized_app_secret, PLACEHOLDER_APP_SECRETS):
        errors.append('SECRET_KEY must be a random secret with at least 32 characters')

    normalized_secret = (encryption_secret or '').strip()
    if _is_weak_production_secret(normalized_secret, PLACEHOLDER_ENCRYPTION_SECRETS):
        errors.append('ENCRYPTION_SECRET must be a random secret with at least 32 characters')

    errors.extend(_duplicate_secret_errors({
        'METRICS_AUTH_TOKEN': normalized_metrics_token,
        'SECRET_KEY': normalized_app_secret,
        'ENCRYPTION_SECRET': normalized_secret,
    }))

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


def debug_configuration_errors(flask_env: str, env: dict[str, str]) -> list[str]:
    """Return production errors for debug flags that expose internals."""
    if (flask_env or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    for key in DEBUG_ENV_KEYS:
        if _truthy(env.get(key)):
            errors.append(f'{key} must be disabled in production')
    return errors


def _valid_utc_build_time(value: str) -> bool:
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except ValueError:
        return False


def release_metadata_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for missing or placeholder release metadata."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    app_version = (env.get('APP_VERSION') or '').strip()
    app_release = (env.get('APP_RELEASE') or '').strip()
    git_sha = (env.get('GIT_SHA') or '').strip()
    build_time = (env.get('BUILD_TIME') or '').strip()

    if not app_version or not RELEASE_METADATA_PATTERN.fullmatch(app_version):
        errors.append('APP_VERSION is required and must be safe release metadata')
    if (
        not app_release
        or app_release.lower() in PLACEHOLDER_RELEASE_METADATA_VALUES
        or not RELEASE_METADATA_PATTERN.fullmatch(app_release)
    ):
        errors.append('APP_RELEASE must identify the deployed release and must not be local/unknown')
    if not git_sha or not GIT_SHA_PATTERN.fullmatch(git_sha):
        errors.append('GIT_SHA must be the deployed git commit SHA')
    if not build_time or not _valid_utc_build_time(build_time):
        errors.append('BUILD_TIME must be UTC in YYYY-MM-DDTHH:MM:SSZ format')

    return errors


def trusted_host_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for unsafe trusted host overrides."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    for raw_host in (env.get('TRUSTED_HOSTS') or '').split(','):
        value = raw_host.strip()
        if not value:
            continue
        if value in {'*', 'null', 'file://'}:
            errors.append(f'TRUSTED_HOSTS contains an unsafe host: {value}')
            continue

        parsed = urlparse(value if '://' in value else f'//{value}')
        host = (parsed.hostname or '').lower()
        if not host:
            errors.append(f'TRUSTED_HOSTS entries must be hostnames: {value}')
            continue
        if parsed.username or parsed.password:
            errors.append(f'TRUSTED_HOSTS must not include credentials: {value}')
        if parsed.path not in {'', '/'} or parsed.params or parsed.query or parsed.fragment:
            errors.append(f'TRUSTED_HOSTS entries must not include a path, query, or fragment: {value}')
        if host in LOCAL_CORS_HOSTS or host.endswith('.local'):
            errors.append(f'TRUSTED_HOSTS contains a local host: {value}')
            continue
        if _non_public_ip_literal(host):
            errors.append(f'TRUSTED_HOSTS contains a private or reserved IP host: {value}')

    return errors


def validate_production_security_config(
    flask_env: str,
    allowed_origins: list[str],
    metrics_token: str,
    app_secret: str,
    encryption_secret: str,
    content_security_policy: str | None = None,
    debug_env: dict[str, str] | None = None,
) -> None:
    """Raise when production security configuration is unsafe.

    검증은 ``flask_env``가 'production'일 때만 동작한다. development/testing 등
    그 외 환경에서는 production 기준을 강제하지 않고 항상 통과(no-op)하므로,
    부팅 경로(``create_app``)에서 호출해도 개발/테스트 환경을 막지 않는다.
    """
    errors = production_security_errors(flask_env, allowed_origins, metrics_token, app_secret, encryption_secret)
    errors.extend(content_security_policy_errors(
        flask_env,
        content_security_policy or default_content_security_policy(flask_env),
    ))
    errors.extend(debug_configuration_errors(flask_env, debug_env or {}))
    if errors:
        raise RuntimeError('; '.join(errors))


def backup_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production backup scheduling/retention configuration errors."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    interval_raw = (env.get('AUTO_BACKUP_INTERVAL_HOURS') or '').strip()
    interval_hours: int | None = None
    if not interval_raw:
        errors.append('AUTO_BACKUP_INTERVAL_HOURS is required in production')
    else:
        try:
            interval_hours = int(interval_raw)
            if interval_hours < 1:
                errors.append('AUTO_BACKUP_INTERVAL_HOURS must be at least 1')
        except ValueError:
            errors.append('AUTO_BACKUP_INTERVAL_HOURS must be an integer number of hours')

    max_age_raw = (env.get('APP_DATA_BACKUP_MAX_AGE_HOURS') or '').strip()
    if max_age_raw:
        try:
            max_age_hours = int(max_age_raw)
            if max_age_hours < 1:
                errors.append('APP_DATA_BACKUP_MAX_AGE_HOURS must be at least 1')
            if interval_hours is not None and max_age_hours < interval_hours:
                errors.append('APP_DATA_BACKUP_MAX_AGE_HOURS must be at least AUTO_BACKUP_INTERVAL_HOURS')
        except ValueError:
            errors.append('APP_DATA_BACKUP_MAX_AGE_HOURS must be an integer number of hours')

    max_backups_raw = (env.get('MAX_BACKUPS') or '30').strip()
    try:
        max_backups = int(max_backups_raw)
        if max_backups < MIN_PRODUCTION_BACKUP_RETENTION:
            errors.append(f'MAX_BACKUPS must be at least {MIN_PRODUCTION_BACKUP_RETENTION} in production')
    except ValueError:
        errors.append('MAX_BACKUPS must be an integer')

    app_data_dir_raw = (env.get('APP_DATA_DIR') or '').strip()
    if not app_data_dir_raw:
        errors.append('APP_DATA_DIR is required in production')
    app_data_dir = Path((app_data_dir_raw or 'data')).resolve()

    app_data_path_defaults = {
        'AGENT_DB_PATH': app_data_dir / 'agent_state.db',
        'CHROMA_DB_PATH': app_data_dir / 'chroma_db',
        'FEEDBACK_DATA_DIR': app_data_dir / 'feedback',
        'FEEDBACK_STORE_DIR': app_data_dir / 'feedback',
        'FINETUNE_OUTPUT_DIR': app_data_dir / 'finetune',
        'GRAPH_STORE_PATH': app_data_dir / 'graph_store',
        'JOB_STORE_DIR': app_data_dir / 'jobs',
        'PREFERENCE_DATA_PATH': app_data_dir / 'preferences.jsonl',
        'SHARE_PAGE_DIR': app_data_dir / 'shared_pages',
        'USER_MEMORY_PATH': app_data_dir / 'user_memory',
    }
    for env_name, default_path in app_data_path_defaults.items():
        raw_path = (env.get(env_name) or '').strip()
        path = Path(raw_path).resolve() if raw_path else default_path.resolve()
        if not _path_within_or_equal(path, app_data_dir):
            errors.append(f'{env_name} must be inside APP_DATA_DIR')

    app_cache_dir_raw = (env.get('APP_CACHE_DIR') or '').strip()
    app_cache_dir: Path | None = None
    if not app_cache_dir_raw:
        errors.append('APP_CACHE_DIR is required in production')
    else:
        app_cache_dir = Path(app_cache_dir_raw).resolve()
        if _path_within_or_equal(app_cache_dir, app_data_dir):
            errors.append('APP_CACHE_DIR must be outside APP_DATA_DIR')

    ai_cache_db_raw = (env.get('AI_CACHE_DB') or '').strip()
    if app_cache_dir is not None:
        ai_cache_db = (
            Path(ai_cache_db_raw).resolve()
            if ai_cache_db_raw
            else app_cache_dir / 'ai_cache.db'
        )
        if not _path_within_or_equal(ai_cache_db.parent, app_cache_dir):
            errors.append('AI_CACHE_DB must be inside APP_CACHE_DIR')

    for env_name in ('AI_CACHE_TTL_DAYS', 'AI_CACHE_MAX_SIZE_MB'):
        raw_value = (env.get(env_name) or '').strip()
        if not raw_value:
            continue
        try:
            value = int(raw_value)
        except ValueError:
            errors.append(f'{env_name} must be an integer')
            continue
        if value < 1:
            errors.append(f'{env_name} must be at least 1')

    backup_dir_raw = (env.get('APP_DATA_BACKUP_DIR') or '').strip()
    backup_dir: Path | None = None
    if not backup_dir_raw:
        errors.append('APP_DATA_BACKUP_DIR is required for production app_data volume backups')
    else:
        backup_dir = Path(backup_dir_raw).resolve()
        if _path_within_or_equal(backup_dir, app_data_dir):
            errors.append('APP_DATA_BACKUP_DIR must be outside APP_DATA_DIR')

    content_backup_dir_raw = (env.get('CONTENT_BACKUP_DIR') or '').strip()
    if content_backup_dir_raw:
        content_backup_dir = Path(content_backup_dir_raw).resolve()
    elif backup_dir is not None:
        content_backup_dir = backup_dir / 'content-library'
    else:
        content_backup_dir = None

    if content_backup_dir is not None and _path_within_or_equal(content_backup_dir, app_data_dir):
        errors.append('CONTENT_BACKUP_DIR must be outside APP_DATA_DIR')

    content_max_raw = (env.get('CONTENT_BACKUP_MAX_BACKUPS') or '').strip()
    if content_max_raw:
        try:
            content_max = int(content_max_raw)
        except ValueError:
            errors.append('CONTENT_BACKUP_MAX_BACKUPS must be an integer')
        else:
            if content_max < 1:
                errors.append('CONTENT_BACKUP_MAX_BACKUPS must be at least 1')

    replica_dir_raw = (env.get('APP_DATA_BACKUP_REPLICA_DIR') or '').strip()
    if not replica_dir_raw:
        errors.append('APP_DATA_BACKUP_REPLICA_DIR is required for production backup replication')
    else:
        replica_dir = Path(replica_dir_raw).resolve()
        if _path_within_or_equal(replica_dir, app_data_dir):
            errors.append('APP_DATA_BACKUP_REPLICA_DIR must be outside APP_DATA_DIR')
        if backup_dir is not None:
            if (
                _path_within_or_equal(replica_dir, backup_dir)
                or _path_within_or_equal(backup_dir, replica_dir)
            ):
                errors.append('APP_DATA_BACKUP_REPLICA_DIR must be separate from APP_DATA_BACKUP_DIR')

    replica_max_raw = (env.get('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS') or max_backups_raw).strip()
    try:
        replica_max_backups = int(replica_max_raw)
        if replica_max_backups < MIN_PRODUCTION_BACKUP_RETENTION:
            errors.append(
                f'APP_DATA_BACKUP_REPLICA_MAX_BACKUPS must be at least '
                f'{MIN_PRODUCTION_BACKUP_RETENTION} in production'
            )
    except ValueError:
        errors.append('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS must be an integer')

    return errors


def scheduler_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production scheduler heartbeat configuration errors."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    if _truthy(env.get('SCHEDULER_ENABLED') or 'true'):
        heartbeat_file = (env.get('SCHEDULER_HEARTBEAT_FILE') or '').strip()
        if not heartbeat_file:
            return ['SCHEDULER_HEARTBEAT_FILE is required when SCHEDULER_ENABLED is true']

    max_age_raw = (env.get('SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS') or '').strip()
    if max_age_raw:
        try:
            max_age = int(max_age_raw)
            if max_age < 30:
                return ['SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS must be at least 30']
        except ValueError:
            return ['SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS must be an integer']

    return []


def edge_basic_auth_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for the public edge Basic Auth configuration."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    user = (env.get('BASIC_AUTH_USER') or '').strip()
    password_hash = (env.get('BASIC_AUTH_HASH') or '').strip()

    if not user or user in PLACEHOLDER_BASIC_AUTH_VALUES:
        errors.append('BASIC_AUTH_USER is required for the production edge')
    if not password_hash or password_hash in PLACEHOLDER_BASIC_AUTH_VALUES:
        errors.append('BASIC_AUTH_HASH is required for the production edge')
    elif not (password_hash.startswith('$2') or password_hash.startswith('$scrypt$')):
        errors.append('BASIC_AUTH_HASH must be generated with caddy hash-password')

    return errors


def auth_mode_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for the app authentication mode."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    auth_mode = (env.get('AUTH_MODE') or '').strip().lower()
    if auth_mode not in {'edge', 'supabase'}:
        return ['AUTH_MODE must be either edge or supabase in production']

    if auth_mode == 'supabase':
        if not (env.get('SUPABASE_URL') or '').strip():
            errors.append('SUPABASE_URL is required when AUTH_MODE=supabase')
        if not (env.get('SUPABASE_ANON_KEY') or '').strip():
            errors.append('SUPABASE_ANON_KEY is required when AUTH_MODE=supabase')

    return errors


def publish_queue_backend_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for non-distributed publish queue storage."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    backend = (env.get('PUBLISH_QUEUE_BACKEND') or 'file').strip().lower()
    if backend != 'redis':
        return ['PUBLISH_QUEUE_BACKEND must be redis in production']

    redis_url = ((env.get('PUBLISH_QUEUE_REDIS_URL') or env.get('REDIS_URL') or '').strip())
    if not redis_url:
        return ['REDIS_URL or PUBLISH_QUEUE_REDIS_URL is required for redis publish queue']

    parsed = urlparse(redis_url)
    if parsed.scheme not in {'redis', 'rediss'} or not parsed.netloc:
        return ['REDIS_URL or PUBLISH_QUEUE_REDIS_URL must be an absolute redis:// or rediss:// URL']

    return []


def rate_limit_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for non-distributed rate limit storage."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    if (env.get('RATE_LIMIT_ENABLED') or 'true').strip().lower() in {'0', 'false', 'no', 'off'}:
        errors.append('RATE_LIMIT_ENABLED must not be false in production')

    redis_url = (env.get('REDIS_URL') or '').strip()
    if not redis_url:
        errors.append('REDIS_URL is required for shared production rate limits')
        return errors

    parsed = urlparse(redis_url)
    if parsed.scheme not in {'redis', 'rediss'} or not parsed.netloc:
        errors.append('REDIS_URL must be an absolute redis:// or rediss:// URL for production rate limits')

    return errors


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def error_tracking_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return errors for production error tracking configuration."""
    errors: list[str] = []

    if _truthy(env.get('ERROR_TRACKING_REQUIRED')) and not (env.get('SENTRY_DSN') or '').strip():
        errors.append('SENTRY_DSN is required when ERROR_TRACKING_REQUIRED=true')

    for key in ('SENTRY_TRACES_SAMPLE_RATE', 'SENTRY_PROFILES_SAMPLE_RATE'):
        raw = (env.get(key) or '').strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f'{key} must be a number between 0 and 1')
            continue
        if value < 0 or value > 1:
            errors.append(f'{key} must be between 0 and 1')

    return errors


def monitor_alert_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for readiness monitor alert configuration."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    webhook_url = (env.get('ALERT_WEBHOOK_URL') or env.get('MONITOR_WEBHOOK_URL') or '').strip()
    required = _truthy(env.get('ALERT_WEBHOOK_REQUIRED')) or _truthy(env.get('MONITOR_WEBHOOK_REQUIRED'))

    if required and not webhook_url:
        errors.append('ALERT_WEBHOOK_URL or MONITOR_WEBHOOK_URL is required when ALERT_WEBHOOK_REQUIRED=true')

    if webhook_url:
        parsed = urlparse(webhook_url)
        if parsed.scheme != 'https' or not parsed.netloc:
            errors.append('ALERT_WEBHOOK_URL or MONITOR_WEBHOOK_URL must be an absolute HTTPS URL in production')

    return errors


def _non_public_ip_literal(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        return False
    return not address.is_global


def _public_https_url_error(key: str, value: str, *, require_origin: bool = False) -> str | None:
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not parsed.netloc:
        return f'{key} must be an absolute HTTPS URL in production'
    if parsed.username or parsed.password:
        return f'{key} must not include credentials in production'
    if host in LOCAL_CORS_HOSTS or host.endswith('.local'):
        return f'{key} must not point at a local host in production'
    if _non_public_ip_literal(host):
        return f'{key} must not point at a private or reserved IP in production'
    if require_origin and (parsed.path or parsed.params or parsed.query or parsed.fragment):
        return f'{key} entries must be origins without path, query, or fragment'
    return None


def public_app_url_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for configured public app base URLs."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    for key in ('INSIGHT_BASE_URL', 'APP_BASE_URL'):
        value = (env.get(key) or '').strip()
        if not value:
            continue
        url_error = _public_https_url_error(key, value)
        if url_error:
            errors.append(url_error)
    public_origin = (env.get('PUBLIC_ORIGIN') or '').strip()
    if public_origin:
        url_error = _public_https_url_error('PUBLIC_ORIGIN', public_origin, require_origin=True)
        if url_error:
            errors.append(url_error)
    return errors


def outbound_webhook_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for outbound webhook URLs."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    webhook_url = (env.get('WEBHOOK_URL') or '').strip()
    if _truthy(env.get('WEBHOOK_ENABLED')) and not webhook_url:
        errors.append('WEBHOOK_URL is required when WEBHOOK_ENABLED=true in production')

    for key in ('WEBHOOK_URL', 'SLACK_WEBHOOK_URL', 'DISCORD_WEBHOOK_URL'):
        value = (env.get(key) or '').strip()
        if not value:
            continue
        url_error = _public_https_url_error(key, value)
        if url_error:
            errors.append(url_error)
    return errors


def payment_provider_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for partially configured payment providers."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []

    stripe_secret = (env.get('STRIPE_SECRET_KEY') or '').strip()
    stripe_webhook_secret = (env.get('STRIPE_WEBHOOK_SECRET') or '').strip()
    if stripe_secret or stripe_webhook_secret:
        if not stripe_secret:
            errors.append('STRIPE_SECRET_KEY is required when Stripe payments are configured')
        elif stripe_secret.startswith('sk_test_') or stripe_secret.lower() in PLACEHOLDER_PAYMENT_SECRETS:
            errors.append('STRIPE_SECRET_KEY must be a live Stripe secret key in production')
        if _is_weak_production_secret(stripe_webhook_secret, PLACEHOLDER_PAYMENT_SECRETS):
            errors.append('STRIPE_WEBHOOK_SECRET must be a random webhook secret when Stripe payments are configured')
        for key in ('STRIPE_SUCCESS_URL', 'STRIPE_CANCEL_URL'):
            value = (env.get(key) or '').strip()
            if not value:
                errors.append(f'{key} is required when Stripe payments are configured')
                continue
            url_error = _public_https_url_error(key, value)
            if url_error:
                errors.append(url_error)

    paddle_api_key = (env.get('PADDLE_API_KEY') or '').strip()
    paddle_webhook_secret = (env.get('PADDLE_WEBHOOK_SECRET') or '').strip()
    if paddle_api_key or paddle_webhook_secret:
        if _is_weak_production_secret(paddle_api_key, PLACEHOLDER_PAYMENT_SECRETS):
            errors.append('PADDLE_API_KEY must be a production Paddle API key when Paddle payments are configured')
        if _is_weak_production_secret(paddle_webhook_secret, PLACEHOLDER_PAYMENT_SECRETS):
            errors.append('PADDLE_WEBHOOK_SECRET must be a random webhook secret when Paddle payments are configured')
        if (env.get('PADDLE_SANDBOX') or 'true').strip().lower() in {'1', 'true', 'yes', 'on'}:
            errors.append('PADDLE_SANDBOX must be false when Paddle payments are configured in production')

    coinbase_api_key = (env.get('COINBASE_COMMERCE_API_KEY') or '').strip()
    coinbase_webhook_secret = (env.get('COINBASE_WEBHOOK_SECRET') or '').strip()
    if coinbase_api_key or coinbase_webhook_secret:
        if _is_weak_production_secret(coinbase_api_key, PLACEHOLDER_PAYMENT_SECRETS):
            errors.append(
                'COINBASE_COMMERCE_API_KEY must be a production API key when Coinbase payments are configured'
            )
        if _is_weak_production_secret(coinbase_webhook_secret, PLACEHOLDER_PAYMENT_SECRETS):
            errors.append(
                'COINBASE_WEBHOOK_SECRET must be a random webhook secret when Coinbase payments are configured'
            )

    return errors


def integration_bot_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for partially configured signed bot webhooks."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []

    slack_bot_token = (env.get('SLACK_BOT_TOKEN') or '').strip()
    slack_signing_secret = (env.get('SLACK_SIGNING_SECRET') or '').strip()
    if slack_bot_token or slack_signing_secret:
        if _is_weak_production_secret(slack_bot_token, PLACEHOLDER_BOT_SECRETS):
            errors.append('SLACK_BOT_TOKEN must be configured when Slack bot webhooks are enabled')
        if _is_weak_production_secret(slack_signing_secret, PLACEHOLDER_BOT_SECRETS):
            errors.append('SLACK_SIGNING_SECRET must be a random signing secret when Slack bot webhooks are enabled')

    discord_bot_token = (env.get('DISCORD_BOT_TOKEN') or '').strip()
    discord_public_key = (env.get('DISCORD_PUBLIC_KEY') or '').strip()
    if discord_bot_token or discord_public_key:
        if _is_weak_production_secret(discord_bot_token, PLACEHOLDER_BOT_SECRETS):
            errors.append('DISCORD_BOT_TOKEN must be configured when Discord bot webhooks are enabled')
        if not discord_public_key:
            errors.append('DISCORD_PUBLIC_KEY is required when Discord bot webhooks are enabled')
        elif not re.fullmatch(r'[0-9a-fA-F]{64}', discord_public_key):
            errors.append('DISCORD_PUBLIC_KEY must be a 64-character hex Ed25519 public key')

    telegram_bot_token = (env.get('TELEGRAM_BOT_TOKEN') or '').strip()
    telegram_webhook_secret = (env.get('TELEGRAM_WEBHOOK_SECRET') or '').strip()
    if telegram_bot_token or telegram_webhook_secret:
        if _is_weak_production_secret(telegram_bot_token, PLACEHOLDER_BOT_SECRETS):
            errors.append('TELEGRAM_BOT_TOKEN must be configured when Telegram bot webhooks are enabled')
        if _is_weak_production_secret(telegram_webhook_secret, PLACEHOLDER_BOT_SECRETS):
            errors.append('TELEGRAM_WEBHOOK_SECRET must be a random secret when Telegram bot webhooks are enabled')

    return errors


def automation_webhook_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for shared-secret automation webhooks."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    secret = (env.get('AUTOMATION_WEBHOOK_SECRET') or '').strip()
    if not secret:
        return []

    errors: list[str] = []
    if _is_weak_production_secret(secret, PLACEHOLDER_AUTOMATION_WEBHOOK_SECRETS):
        errors.append('AUTOMATION_WEBHOOK_SECRET must be a random secret with at least 32 characters')
    for key in ('METRICS_AUTH_TOKEN', 'SECRET_KEY', 'ENCRYPTION_SECRET'):
        if secret == (env.get(key) or '').strip():
            errors.append(f'AUTOMATION_WEBHOOK_SECRET must not reuse {key}')
    return errors


def support_handoff_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for unsafe GitHub support handoff configuration."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    support_repo = (env.get('SUPPORT_GITHUB_REPO') or '').strip()
    support_token = (env.get('SUPPORT_GITHUB_TOKEN') or '').strip()
    fallback_token = (env.get('GITHUB_TOKEN') or '').strip()
    repo = support_repo or ((env.get('GITHUB_REPOSITORY') or '').strip() if fallback_token else '')
    token = support_token or fallback_token
    handoff_secret = (env.get('SUPPORT_HANDOFF_SECRET') or '').strip()

    if not (support_repo or support_token or fallback_token or handoff_secret):
        return []

    errors: list[str] = []
    if not repo or '/' not in repo:
        errors.append('SUPPORT_GITHUB_REPO or GITHUB_REPOSITORY must be owner/repo when GitHub handoff is configured')
    if not token:
        errors.append('SUPPORT_GITHUB_TOKEN or GITHUB_TOKEN is required when GitHub handoff is configured')
    if _is_weak_production_secret(handoff_secret, PLACEHOLDER_SUPPORT_HANDOFF_SECRETS):
        errors.append('SUPPORT_HANDOFF_SECRET must be a random secret with at least 32 characters')

    for key in ('METRICS_AUTH_TOKEN', 'SECRET_KEY', 'ENCRYPTION_SECRET'):
        if handoff_secret and handoff_secret == (env.get(key) or '').strip():
            errors.append(f'SUPPORT_HANDOFF_SECRET must not reuse {key}')

    return errors


def default_model_configuration_errors(env: dict[str, str]) -> list[str]:
    """Return production errors for unsafe or unconfigured default models."""
    if (env.get('FLASK_ENV') or '').strip().lower() != 'production':
        return []

    errors: list[str] = []
    model_keys = (
        ('DEFAULT_GENERATION_MODEL', DEFAULT_PRODUCTION_GENERATION_MODEL),
        ('VIDEO_QA_DEFAULT_MODEL', env.get('DEFAULT_GENERATION_MODEL') or DEFAULT_PRODUCTION_GENERATION_MODEL),
    )

    for model_env_key, default_model in model_keys:
        model = (env.get(model_env_key) or default_model or '').strip()
        provider = model.split('/', 1)[0].strip().lower() if '/' in model else ''

        if provider == 'chatmock':
            errors.append(f'{model_env_key} must not use chatmock in production')
            continue
        if not provider:
            errors.append(f'{model_env_key} must include a provider prefix, for example zhipuai/GLM-4.5-Air')
            continue

        required_env_keys = MODEL_PROVIDER_ENV_KEYS.get(provider)
        if not required_env_keys:
            errors.append(f'{model_env_key} uses unsupported provider for production default model: {provider}')
            continue
        if not any((env.get(key) or '').strip() for key in required_env_keys):
            joined = ' or '.join(required_env_keys)
            errors.append(f'{joined} is required for {model_env_key}={model}')

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
        env.get('SECRET_KEY', ''),
        env.get('ENCRYPTION_SECRET', ''),
    ))
    errors.extend(content_security_policy_errors(
        security_env,
        env.get('CONTENT_SECURITY_POLICY') or default_content_security_policy(security_env),
    ))
    errors.extend(debug_configuration_errors(security_env, env))
    release_env = dict(env)
    release_env['FLASK_ENV'] = security_env
    errors.extend(release_metadata_configuration_errors(release_env))
    edge_env = dict(env)
    edge_env['FLASK_ENV'] = security_env
    errors.extend(trusted_host_configuration_errors(edge_env))
    errors.extend(edge_basic_auth_errors(edge_env))
    errors.extend(auth_mode_configuration_errors(edge_env))

    backup_env = dict(env)
    backup_env['FLASK_ENV'] = security_env
    errors.extend(backup_configuration_errors(backup_env))
    errors.extend(scheduler_configuration_errors(backup_env))
    errors.extend(rate_limit_configuration_errors(backup_env))
    errors.extend(publish_queue_backend_errors(backup_env))
    errors.extend(error_tracking_configuration_errors(env))
    errors.extend(monitor_alert_configuration_errors(env))
    errors.extend(public_app_url_configuration_errors(edge_env))
    errors.extend(outbound_webhook_configuration_errors(edge_env))
    errors.extend(payment_provider_configuration_errors(edge_env))
    errors.extend(integration_bot_configuration_errors(edge_env))
    errors.extend(automation_webhook_configuration_errors(edge_env))
    errors.extend(support_handoff_configuration_errors(edge_env))
    errors.extend(default_model_configuration_errors(edge_env))

    return errors
