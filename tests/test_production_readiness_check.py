"""Executable production readiness checks."""
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'
SAFE_SUPPORT_HANDOFF_SECRET = 'support-handoff-1234567890abcdefABCDEF'
SAFE_GIT_SHA = 'abcdef1234567890abcdef1234567890abcdef12'
SAFE_STRIPE_SECRET_KEY = 'stripe-live-ci-key-1234567890abcdefABCDEFghiJKLMN'
SAFE_STRIPE_WEBHOOK_SECRET = 'stripe-webhook-ci-secret-1234567890abcdefABCDEFghi'
SAFE_PADDLE_API_KEY = 'pdl_live_1234567890abcdefABCDEFghiJKLMN'
SAFE_PADDLE_WEBHOOK_SECRET = 'paddle_webhook_1234567890abcdefABCDEF'
SAFE_COINBASE_API_KEY = 'coinbase_api_1234567890abcdefABCDEF'
SAFE_COINBASE_WEBHOOK_SECRET = 'coinbase_webhook_1234567890abcdefABCDEF'
SAFE_SLACK_BOT_TOKEN = 'slack-bot-token-1234567890abcdefABCDEF'
SAFE_SLACK_SIGNING_SECRET = 'slack_signing_1234567890abcdefABCDEF'
SAFE_DISCORD_BOT_TOKEN = 'discord_bot_1234567890abcdefABCDEF'
SAFE_DISCORD_PUBLIC_KEY = 'a' * 64
SAFE_TELEGRAM_BOT_TOKEN = '123456789:telegram_bot_token_1234567890abcdefABCDEF'
SAFE_TELEGRAM_WEBHOOK_SECRET = 'telegram_webhook_1234567890abcdefABCDEF'
SAFE_AUTOMATION_WEBHOOK_SECRET = 'automation_webhook_1234567890abcdefABCDEF'


def _safe_minimum_env(**overrides):
    env = {
        'FLASK_ENV': 'production',
        'AUTH_MODE': 'edge',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'BASIC_AUTH_USER': 'ci-admin',
        'BASIC_AUTH_HASH': '$2a$14$cihashplaceholdercihashplaceholdercihashplaceholdercihashp',
        'SECRET_KEY': SAFE_SECRET_KEY,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'RATE_LIMIT_ENABLED': 'true',
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'APP_DATA_BACKUP_MAX_AGE_HOURS': '12',
        'MAX_BACKUPS': '30',
        'APP_DATA_DIR': '/app/data',
        'AGENT_DB_PATH': '/app/data/agent_state.db',
        'APP_CACHE_DIR': '/app/cache',
        'AI_CACHE_DB': '/app/cache/ai_cache.db',
        'CHROMA_DB_PATH': '/app/data/chroma_db',
        'FEEDBACK_DATA_DIR': '/app/data/feedback',
        'FEEDBACK_STORE_DIR': '/app/data/feedback',
        'FINETUNE_OUTPUT_DIR': '/app/data/finetune',
        'GRAPH_STORE_PATH': '/app/data/graph_store',
        'JOB_STORE_DIR': '/app/data/jobs',
        'PREFERENCE_DATA_PATH': '/app/data/preferences.jsonl',
        'SHARE_PAGE_DIR': '/app/data/shared_pages',
        'USER_MEMORY_PATH': '/app/data/user_memory',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
        'CONTENT_BACKUP_DIR': '/mnt/backups/insight-engine/content-library',
        'APP_DATA_BACKUP_REPLICA_DIR': '/mnt/backup-replica/insight-engine',
        'SCHEDULER_ENABLED': 'true',
        'SCHEDULER_HEARTBEAT_FILE': '/tmp/insight-engine-scheduler.heartbeat',
        'PUBLISH_QUEUE_BACKEND': 'redis',
        'ZAI_API_KEY': 'test-zai-key',
        'TRUSTED_HOSTS': '',
        'SUPPORT_HANDOFF_SECRET': '',
        'SUPPORT_GITHUB_REPO': '',
        'SUPPORT_GITHUB_TOKEN': '',
        'GITHUB_REPOSITORY': '',
        'GITHUB_TOKEN': '',
        'APP_VERSION': 'v2.0',
        'APP_RELEASE': SAFE_GIT_SHA,
        'GIT_SHA': SAFE_GIT_SHA,
        'BUILD_TIME': '2026-06-27T08:00:00Z',
    }
    env.update(overrides)
    return env


def _run_readiness_check(env):
    process_env = os.environ.copy()
    process_env.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'check_production_readiness.py')],
        cwd=ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_readiness_check_passes_with_safe_minimum_production_env():
    result = _run_readiness_check(_safe_minimum_env())

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_reports_missing_production_guards_together():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'AUTH_MODE': '',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'BASIC_AUTH_USER': '',
        'BASIC_AUTH_HASH': '',
        'SECRET_KEY': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CORS_ORIGINS' in output
    assert 'AUTH_MODE' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'BASIC_AUTH_USER' in output
    assert 'BASIC_AUTH_HASH' in output
    assert 'SECRET_KEY' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'REDIS_URL' in output
    assert 'APP_RELEASE' in output
    assert 'GIT_SHA' in output
    assert 'BUILD_TIME' in output


def test_readiness_check_reports_all_required_vars_when_environment_is_empty():
    result = _run_readiness_check({
        'FLASK_ENV': '',
        'AUTH_MODE': '',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'BASIC_AUTH_USER': '',
        'BASIC_AUTH_HASH': '',
        'SECRET_KEY': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'FLASK_ENV' in output
    assert 'AUTH_MODE' in output
    assert 'CORS_ORIGINS' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'BASIC_AUTH_USER' in output
    assert 'BASIC_AUTH_HASH' in output
    assert 'SECRET_KEY' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'REDIS_URL' in output


def test_readiness_check_requires_real_release_metadata_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        APP_RELEASE='local',
        GIT_SHA='local',
        BUILD_TIME='unknown',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_RELEASE' in output
    assert 'local/unknown' in output
    assert 'GIT_SHA' in output
    assert 'BUILD_TIME' in output


def test_readiness_check_rejects_unsafe_production_csp():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'CONTENT_SECURITY_POLICY': "default-src 'self'; script-src 'self' 'unsafe-inline'",
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CONTENT_SECURITY_POLICY' in output
    assert 'unsafe-inline' in output


def test_readiness_check_rejects_debug_flags_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        FLASK_DEBUG='true',
        DEBUG='1',
        APP_DEBUG='yes',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'FLASK_DEBUG' in output
    assert 'DEBUG' in output
    assert 'APP_DEBUG' in output
    assert 'disabled in production' in output


def test_readiness_check_allows_extra_trusted_host():
    result = _run_readiness_check(_safe_minimum_env(TRUSTED_HOSTS='admin.example.com'))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_unsafe_trusted_host():
    result = _run_readiness_check(_safe_minimum_env(TRUSTED_HOSTS='*'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'TRUSTED_HOSTS' in output
    assert 'unsafe host' in output


def test_readiness_check_rejects_local_trusted_host_override():
    result = _run_readiness_check(_safe_minimum_env(TRUSTED_HOSTS='localhost'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'TRUSTED_HOSTS' in output
    assert 'local host' in output


def test_readiness_check_rejects_cors_url_paths_and_credentials():
    result = _run_readiness_check(_safe_minimum_env(
        CORS_ORIGINS='https://app.example.com/app,https://user:pass@admin.example.com',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CORS_ORIGINS' in output
    assert 'origins without path' in output
    assert 'must not include credentials' in output


def test_readiness_check_rejects_private_ip_trusted_host():
    result = _run_readiness_check(_safe_minimum_env(TRUSTED_HOSTS='10.0.0.5'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'TRUSTED_HOSTS' in output
    assert 'private or reserved IP' in output


def test_readiness_check_rejects_unsafe_public_app_base_urls():
    result = _run_readiness_check(_safe_minimum_env(
        INSIGHT_BASE_URL='http://127.0.0.1:8090',
        APP_BASE_URL='https://10.0.0.5',
        PUBLIC_ORIGIN='https://app.example.com/share-root',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'INSIGHT_BASE_URL' in output
    assert 'absolute HTTPS URL' in output
    assert 'APP_BASE_URL' in output
    assert 'private or reserved IP' in output
    assert 'PUBLIC_ORIGIN' in output
    assert 'origins without path' in output


def test_readiness_check_accepts_public_app_base_urls():
    result = _run_readiness_check(_safe_minimum_env(
        INSIGHT_BASE_URL='https://insight.example.com',
        APP_BASE_URL='https://app.example.com',
        PUBLIC_ORIGIN='https://share.example.com',
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_unsafe_outbound_webhooks():
    result = _run_readiness_check(_safe_minimum_env(
        WEBHOOK_ENABLED='true',
        WEBHOOK_URL='',
        SLACK_WEBHOOK_URL='http://hooks.slack.com/services/T/B/C',
        DISCORD_WEBHOOK_URL='https://10.0.0.5/webhook',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'WEBHOOK_URL' in output
    assert 'WEBHOOK_ENABLED=true' in output
    assert 'SLACK_WEBHOOK_URL' in output
    assert 'absolute HTTPS URL' in output
    assert 'DISCORD_WEBHOOK_URL' in output
    assert 'private or reserved IP' in output


def test_readiness_check_accepts_safe_outbound_webhooks():
    result = _run_readiness_check(_safe_minimum_env(
        WEBHOOK_ENABLED='true',
        WEBHOOK_URL='https://hooks.example.com/insight-engine',
        SLACK_WEBHOOK_URL='https://hooks.slack.com/services/T/B/C',
        DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/123/token',
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_requires_explicit_auth_mode():
    result = _run_readiness_check(_safe_minimum_env(AUTH_MODE=''))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AUTH_MODE' in output
    assert 'edge or supabase' in output


def test_readiness_check_requires_supabase_when_auth_mode_supabase():
    result = _run_readiness_check(_safe_minimum_env(
        AUTH_MODE='supabase',
        SUPABASE_URL='',
        SUPABASE_ANON_KEY='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPABASE_URL' in output
    assert 'SUPABASE_ANON_KEY' in output


def test_readiness_check_accepts_supabase_auth_mode_with_supabase_config():
    result = _run_readiness_check(_safe_minimum_env(
        AUTH_MODE='supabase',
        SUPABASE_URL='https://project.supabase.co',
        SUPABASE_ANON_KEY='anon-key',
    ))

    assert result.returncode == 0


def test_readiness_check_rejects_plaintext_edge_basic_auth_secret():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'BASIC_AUTH_USER': 'admin',
        'BASIC_AUTH_HASH': 'plaintext-password',
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
        'PUBLISH_QUEUE_BACKEND': 'redis',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'BASIC_AUTH_USER' in output
    assert 'BASIC_AUTH_HASH' in output
    assert 'caddy hash-password' in output


def test_readiness_check_requires_automatic_backup_configuration():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '',
        'MAX_BACKUPS': '3',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AUTO_BACKUP_INTERVAL_HOURS' in output
    assert 'MAX_BACKUPS' in output


def test_readiness_check_rejects_invalid_backup_interval():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '0',
        'MAX_BACKUPS': '30',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AUTO_BACKUP_INTERVAL_HOURS' in output


def test_readiness_check_rejects_backup_max_age_lower_than_interval():
    result = _run_readiness_check(_safe_minimum_env(
        AUTO_BACKUP_INTERVAL_HOURS='6',
        APP_DATA_BACKUP_MAX_AGE_HOURS='3',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_DATA_BACKUP_MAX_AGE_HOURS' in output
    assert 'AUTO_BACKUP_INTERVAL_HOURS' in output


def test_readiness_check_requires_external_app_data_backup_dir():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_DIR': '/app/data',
        'APP_DATA_BACKUP_DIR': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_DATA_BACKUP_DIR' in output


def test_readiness_check_rejects_app_data_backup_dir_inside_app_data():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_DIR': '/app/data',
        'APP_DATA_BACKUP_DIR': '/app/data/backups',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_DATA_BACKUP_DIR' in output
    assert 'outside APP_DATA_DIR' in output


def test_readiness_check_requires_app_cache_dir():
    result = _run_readiness_check(_safe_minimum_env(APP_CACHE_DIR=''))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_CACHE_DIR' in output


def test_readiness_check_rejects_app_cache_dir_inside_app_data():
    result = _run_readiness_check(_safe_minimum_env(APP_CACHE_DIR='/app/data/cache'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_CACHE_DIR' in output
    assert 'outside APP_DATA_DIR' in output


def test_readiness_check_rejects_runtime_data_path_outside_app_data():
    result = _run_readiness_check(_safe_minimum_env(
        GRAPH_STORE_PATH='/tmp/graph_store',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'GRAPH_STORE_PATH' in output
    assert 'inside APP_DATA_DIR' in output


def test_readiness_check_rejects_content_backup_dir_inside_app_data():
    result = _run_readiness_check(_safe_minimum_env(
        CONTENT_BACKUP_DIR='/app/data/backups/content-library',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CONTENT_BACKUP_DIR' in output
    assert 'outside APP_DATA_DIR' in output


def test_readiness_check_rejects_invalid_content_backup_retention():
    result = _run_readiness_check(_safe_minimum_env(
        CONTENT_BACKUP_MAX_BACKUPS='0',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CONTENT_BACKUP_MAX_BACKUPS' in output


def test_readiness_check_rejects_ai_cache_db_outside_app_cache_dir():
    result = _run_readiness_check(
        _safe_minimum_env(AI_CACHE_DB='/tmp/ai_cache.db')
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AI_CACHE_DB' in output
    assert 'inside APP_CACHE_DIR' in output


def test_readiness_check_rejects_invalid_ai_cache_retention():
    result = _run_readiness_check(_safe_minimum_env(
        AI_CACHE_TTL_DAYS='0',
        AI_CACHE_MAX_SIZE_MB='invalid',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AI_CACHE_TTL_DAYS' in output
    assert 'AI_CACHE_MAX_SIZE_MB' in output


def test_readiness_check_requires_distributed_publish_queue_backend():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': SAFE_METRICS_AUTH_TOKEN,
        'ENCRYPTION_SECRET': SAFE_ENCRYPTION_SECRET,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
        'PUBLISH_QUEUE_BACKEND': 'file',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'PUBLISH_QUEUE_BACKEND' in output
    assert 'redis' in output


def test_readiness_check_requires_rate_limiter_in_production():
    result = _run_readiness_check(_safe_minimum_env(RATE_LIMIT_ENABLED='false'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'RATE_LIMIT_ENABLED' in output
    assert 'production' in output


def test_readiness_check_requires_scheduler_heartbeat_when_scheduler_is_enabled():
    result = _run_readiness_check(_safe_minimum_env(SCHEDULER_HEARTBEAT_FILE=''))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SCHEDULER_HEARTBEAT_FILE' in output


def test_readiness_check_allows_missing_scheduler_heartbeat_when_scheduler_is_disabled():
    result = _run_readiness_check(_safe_minimum_env(
        SCHEDULER_ENABLED='false',
        SCHEDULER_HEARTBEAT_FILE='',
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_invalid_scheduler_heartbeat_max_age():
    for value in ('29', 'not-a-number'):
        result = _run_readiness_check(_safe_minimum_env(
            SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS=value,
        ))

        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert 'SCHEDULER_HEARTBEAT_MAX_AGE_SECONDS' in output


def test_readiness_check_rejects_memory_rate_limit_storage_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        REDIS_URL='memory://',
        PUBLISH_QUEUE_REDIS_URL='redis://redis:6379/0',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'REDIS_URL' in output
    assert 'redis://' in output


def test_readiness_check_rejects_memory_publish_queue_storage_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        REDIS_URL='redis://redis:6379/0',
        PUBLISH_QUEUE_REDIS_URL='memory://',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'PUBLISH_QUEUE_REDIS_URL' in output or 'REDIS_URL' in output
    assert 'redis://' in output


def test_readiness_check_requires_sentry_when_error_tracking_is_required():
    result = _run_readiness_check(_safe_minimum_env(
        ERROR_TRACKING_REQUIRED='true',
        SENTRY_DSN='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SENTRY_DSN' in output
    assert 'ERROR_TRACKING_REQUIRED' in output


def test_readiness_check_requires_flask_secret_key():
    result = _run_readiness_check(_safe_minimum_env(SECRET_KEY='dev-secret'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SECRET_KEY' in output
    assert 'at least 32 characters' in output


def test_readiness_check_rejects_weak_metrics_token():
    result = _run_readiness_check(_safe_minimum_env(METRICS_AUTH_TOKEN='metrics-token'))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'random token' in output


def test_readiness_check_rejects_low_diversity_secret_values():
    result = _run_readiness_check(_safe_minimum_env(ENCRYPTION_SECRET='x' * 32))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'ENCRYPTION_SECRET' in output
    assert 'random secret' in output


def test_readiness_check_rejects_reused_production_secrets():
    result = _run_readiness_check(_safe_minimum_env(ENCRYPTION_SECRET=SAFE_SECRET_KEY))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'ENCRYPTION_SECRET' in output
    assert 'SECRET_KEY' in output
    assert 'must not reuse' in output


def test_readiness_check_allows_strong_support_github_handoff_config():
    result = _run_readiness_check(_safe_minimum_env(
        SUPPORT_HANDOFF_SECRET=SAFE_SUPPORT_HANDOFF_SECRET,
        SUPPORT_GITHUB_REPO='acme/insight-engine',
        SUPPORT_GITHUB_TOKEN='ghp_testtoken1234567890',
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_incomplete_support_github_handoff_config():
    result = _run_readiness_check(_safe_minimum_env(
        SUPPORT_GITHUB_REPO='acme/insight-engine',
        SUPPORT_HANDOFF_SECRET=SAFE_SUPPORT_HANDOFF_SECRET,
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPPORT_GITHUB_TOKEN' in output
    assert 'GitHub handoff' in output


def test_readiness_check_rejects_weak_support_handoff_secret():
    result = _run_readiness_check(_safe_minimum_env(
        SUPPORT_HANDOFF_SECRET='support-handoff-secret',
        SUPPORT_GITHUB_REPO='acme/insight-engine',
        SUPPORT_GITHUB_TOKEN='ghp_testtoken1234567890',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPPORT_HANDOFF_SECRET' in output
    assert 'random secret' in output


def test_readiness_check_rejects_reused_support_handoff_secret():
    result = _run_readiness_check(_safe_minimum_env(
        SUPPORT_HANDOFF_SECRET=SAFE_ENCRYPTION_SECRET,
        SUPPORT_GITHUB_REPO='acme/insight-engine',
        SUPPORT_GITHUB_TOKEN='ghp_testtoken1234567890',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPPORT_HANDOFF_SECRET' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'must not reuse' in output


def test_readiness_check_rejects_chatmock_default_model_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        DEFAULT_GENERATION_MODEL='chatmock/gpt-5.3-codex-spark',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'DEFAULT_GENERATION_MODEL' in output
    assert 'chatmock' in output


def test_readiness_check_requires_default_model_provider_key():
    result = _run_readiness_check(_safe_minimum_env(
        ZAI_API_KEY='',
        ZHIPUAI_API_KEY='',
        DEFAULT_GENERATION_MODEL='zhipuai/GLM-4.5-Air',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'ZAI_API_KEY' in output
    assert 'DEFAULT_GENERATION_MODEL' in output


def test_readiness_check_rejects_invalid_sentry_sample_rates():
    result = _run_readiness_check(_safe_minimum_env(
        SENTRY_TRACES_SAMPLE_RATE='2',
        SENTRY_PROFILES_SAMPLE_RATE='not-a-number',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SENTRY_TRACES_SAMPLE_RATE' in output
    assert 'SENTRY_PROFILES_SAMPLE_RATE' in output


def test_readiness_check_requires_alert_webhook_when_enabled():
    result = _run_readiness_check(_safe_minimum_env(
        ALERT_WEBHOOK_REQUIRED='true',
        ALERT_WEBHOOK_URL='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'ALERT_WEBHOOK_URL' in output
    assert 'ALERT_WEBHOOK_REQUIRED=true' in output


def test_readiness_check_rejects_non_https_alert_webhook_in_production():
    result = _run_readiness_check(_safe_minimum_env(
        ALERT_WEBHOOK_URL='http://hooks.example.com/insight-engine',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'ALERT_WEBHOOK_URL' in output
    assert 'HTTPS URL' in output


def test_readiness_check_allows_complete_live_payment_provider_config():
    result = _run_readiness_check(_safe_minimum_env(
        STRIPE_SECRET_KEY=SAFE_STRIPE_SECRET_KEY,
        STRIPE_WEBHOOK_SECRET=SAFE_STRIPE_WEBHOOK_SECRET,
        STRIPE_SUCCESS_URL='https://app.example.com/billing/success',
        STRIPE_CANCEL_URL='https://app.example.com/billing/canceled',
        PADDLE_API_KEY=SAFE_PADDLE_API_KEY,
        PADDLE_WEBHOOK_SECRET=SAFE_PADDLE_WEBHOOK_SECRET,
        PADDLE_SANDBOX='false',
        COINBASE_COMMERCE_API_KEY=SAFE_COINBASE_API_KEY,
        COINBASE_WEBHOOK_SECRET=SAFE_COINBASE_WEBHOOK_SECRET,
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_incomplete_stripe_payment_config():
    result = _run_readiness_check(_safe_minimum_env(
        STRIPE_SECRET_KEY='sk_test_xxx',
        STRIPE_WEBHOOK_SECRET='',
        STRIPE_SUCCESS_URL='http://localhost:3000/billing?success=true',
        STRIPE_CANCEL_URL='https://app.example.com/billing/canceled',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'STRIPE_SECRET_KEY' in output
    assert 'STRIPE_WEBHOOK_SECRET' in output
    assert 'STRIPE_SUCCESS_URL' in output


def test_readiness_check_rejects_incomplete_paddle_payment_config():
    result = _run_readiness_check(_safe_minimum_env(
        PADDLE_API_KEY=SAFE_PADDLE_API_KEY,
        PADDLE_WEBHOOK_SECRET='',
        PADDLE_SANDBOX='true',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'PADDLE_WEBHOOK_SECRET' in output
    assert 'PADDLE_SANDBOX' in output


def test_readiness_check_rejects_incomplete_coinbase_payment_config():
    result = _run_readiness_check(_safe_minimum_env(
        COINBASE_COMMERCE_API_KEY=SAFE_COINBASE_API_KEY,
        COINBASE_WEBHOOK_SECRET='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'COINBASE_WEBHOOK_SECRET' in output


def test_readiness_check_allows_complete_signed_bot_webhook_config():
    result = _run_readiness_check(_safe_minimum_env(
        SLACK_BOT_TOKEN=SAFE_SLACK_BOT_TOKEN,
        SLACK_SIGNING_SECRET=SAFE_SLACK_SIGNING_SECRET,
        DISCORD_BOT_TOKEN=SAFE_DISCORD_BOT_TOKEN,
        DISCORD_PUBLIC_KEY=SAFE_DISCORD_PUBLIC_KEY,
        TELEGRAM_BOT_TOKEN=SAFE_TELEGRAM_BOT_TOKEN,
        TELEGRAM_WEBHOOK_SECRET=SAFE_TELEGRAM_WEBHOOK_SECRET,
        AUTOMATION_WEBHOOK_SECRET=SAFE_AUTOMATION_WEBHOOK_SECRET,
    ))

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_incomplete_slack_bot_webhook_config():
    result = _run_readiness_check(_safe_minimum_env(
        SLACK_BOT_TOKEN=SAFE_SLACK_BOT_TOKEN,
        SLACK_SIGNING_SECRET='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SLACK_SIGNING_SECRET' in output


def test_readiness_check_rejects_invalid_discord_bot_webhook_config():
    result = _run_readiness_check(_safe_minimum_env(
        DISCORD_BOT_TOKEN=SAFE_DISCORD_BOT_TOKEN,
        DISCORD_PUBLIC_KEY='not-a-hex-key',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'DISCORD_PUBLIC_KEY' in output
    assert '64-character hex' in output


def test_readiness_check_rejects_incomplete_telegram_bot_webhook_config():
    result = _run_readiness_check(_safe_minimum_env(
        TELEGRAM_BOT_TOKEN=SAFE_TELEGRAM_BOT_TOKEN,
        TELEGRAM_WEBHOOK_SECRET='',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'TELEGRAM_WEBHOOK_SECRET' in output


def test_readiness_check_rejects_weak_automation_webhook_secret():
    result = _run_readiness_check(_safe_minimum_env(
        AUTOMATION_WEBHOOK_SECRET='change-me',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AUTOMATION_WEBHOOK_SECRET' in output


def test_readiness_check_requires_backup_replica_dir():
    result = _run_readiness_check(_safe_minimum_env(APP_DATA_BACKUP_REPLICA_DIR=''))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_DATA_BACKUP_REPLICA_DIR' in output


def test_readiness_check_rejects_backup_replica_dir_inside_backup_dir():
    result = _run_readiness_check(_safe_minimum_env(
        APP_DATA_BACKUP_DIR='/mnt/backups/insight-engine',
        APP_DATA_BACKUP_REPLICA_DIR='/mnt/backups/insight-engine/replica',
    ))

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'APP_DATA_BACKUP_REPLICA_DIR' in output
    assert 'separate from APP_DATA_BACKUP_DIR' in output


def test_package_json_exposes_verify_production_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:production'] == (
        "sh -c 'if [ -f .env ]; then set -a; . ./.env; set +a; fi; python3 scripts/check_production_readiness.py'"
    )
