"""Executable production readiness checks."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
_SAFE_SUPABASE_ENV = {
    'SUPABASE_URL': 'https://test-project.supabase.co',
    'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_test',
    'SUPABASE_SECRET_KEY': 'sb_secret_test',
    'PUBLIC_ORIGIN': 'https://app.example.com',
    'AUTO_BACKUP_ENABLED': 'true',
    'PLATFORM_VOLUME_BACKUPS_ENABLED': 'true',
}


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


def _run_readiness_check_args(args, env=None):
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'check_production_readiness.py'), *args],
        cwd=ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_readiness_check_passes_with_safe_minimum_production_env():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_can_load_explicit_env_file(tmp_path):
    env_file = tmp_path / 'production.env'
    env_file.write_text(
        '\n'.join([
            'FLASK_ENV=production',
            'SUPABASE_URL=https://test-project.supabase.co',
            'SUPABASE_PUBLISHABLE_KEY=sb_publishable_test',
            'SUPABASE_SECRET_KEY=sb_secret_test',
            'CORS_ORIGINS=https://app.example.com',
            'PUBLIC_ORIGIN=https://app.example.com',
            'METRICS_AUTH_TOKEN=metrics-token',
            f"ENCRYPTION_SECRET={'x' * 32}",
            'REDIS_URL=redis://redis:6379/0',
            'AUTO_BACKUP_ENABLED=true',
            'PLATFORM_VOLUME_BACKUPS_ENABLED=true',
            'AUTO_BACKUP_INTERVAL_HOURS=6',
            'MAX_BACKUPS=30',
            'APP_DATA_BACKUP_DIR=/mnt/backups/insight-engine',
        ]),
        encoding='utf-8',
    )

    result = _run_readiness_check_args(['--env-file', str(env_file)], {
        'FLASK_ENV': '',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
        'AUTO_BACKUP_INTERVAL_HOURS': '',
        'APP_DATA_BACKUP_DIR': '',
    })

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_env_file_does_not_fall_back_to_process_env(tmp_path):
    env_file = tmp_path / 'incomplete-production.env'
    env_file.write_text(
        '\n'.join([
            'FLASK_ENV=production',
            'CORS_ORIGINS=https://app.example.com',
        ]),
        encoding='utf-8',
    )

    result = _run_readiness_check_args(['--env-file', str(env_file)], {
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'REDIS_URL' in output


def test_readiness_check_reports_missing_env_file():
    result = _run_readiness_check_args(['--env-file', 'missing.production.env'])

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'env file not found' in output


def test_readiness_check_reports_missing_production_guards_together():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CORS_ORIGINS' in output
    assert 'PUBLIC_ORIGIN' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'SUPABASE_URL' in output
    assert 'SUPABASE_PUBLISHABLE_KEY' in output
    assert 'SUPABASE_SECRET_KEY' in output
    assert 'REDIS_URL' in output


def test_readiness_check_reports_all_required_vars_when_environment_is_empty():
    result = _run_readiness_check({
        'FLASK_ENV': '',
        'CORS_ORIGINS': '',
        'METRICS_AUTH_TOKEN': '',
        'ENCRYPTION_SECRET': '',
        'REDIS_URL': '',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'FLASK_ENV' in output
    assert 'CORS_ORIGINS' in output
    assert 'PUBLIC_ORIGIN' in output
    assert 'METRICS_AUTH_TOKEN' in output
    assert 'ENCRYPTION_SECRET' in output
    assert 'SUPABASE_URL' in output
    assert 'SUPABASE_PUBLISHABLE_KEY' in output
    assert 'SUPABASE_SECRET_KEY' in output
    assert 'REDIS_URL' in output


def test_readiness_check_rejects_unsafe_production_csp():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'CONTENT_SECURITY_POLICY': "default-src 'self'; script-src 'self' 'unsafe-inline'",
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'CONTENT_SECURITY_POLICY' in output
    assert 'unsafe-inline' in output


@pytest.mark.parametrize(
    ('public_origin', 'expected_error'),
    [
        ('http://app.example.com', 'PUBLIC_ORIGIN must be a valid HTTPS origin'),
        ('https://localhost', 'PUBLIC_ORIGIN must not use a local address'),
        (
            'https://app.example.com/path',
            'PUBLIC_ORIGIN must not contain a path, query, or fragment',
        ),
        (
            'https://user@app.example.com',
            'PUBLIC_ORIGIN must not contain user information',
        ),
    ],
)
def test_readiness_check_rejects_unsafe_public_origin(
    public_origin,
    expected_error,
):
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'PUBLIC_ORIGIN': public_origin,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert expected_error in output


def test_readiness_check_requires_automatic_backup_configuration():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
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
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '0',
        'MAX_BACKUPS': '30',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'AUTO_BACKUP_INTERVAL_HOURS' in output


@pytest.mark.parametrize(
    ('interval', 'max_backups', 'expected_error'),
    [
        ('721', '30', 'AUTO_BACKUP_INTERVAL_HOURS must be at most 720'),
        ('6', '10001', 'MAX_BACKUPS must be at most 10000'),
    ],
)
def test_readiness_check_rejects_unbounded_backup_configuration(
    interval,
    max_backups,
    expected_error,
):
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': interval,
        'MAX_BACKUPS': max_backups,
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert expected_error in output


def test_readiness_check_requires_external_app_data_backup_dir():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
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
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
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


def test_readiness_check_rejects_example_supabase_configuration():
    result = _run_readiness_check({
        'FLASK_ENV': 'production',
        'SUPABASE_URL': 'https://your-project.supabase.co',
        'SUPABASE_PUBLISHABLE_KEY': 'your-publishable-key',
        'SUPABASE_SECRET_KEY': 'your-secret-key',
        'AUTO_BACKUP_ENABLED': 'true',
        'PLATFORM_VOLUME_BACKUPS_ENABLED': 'true',
        'PUBLIC_ORIGIN': 'https://app.example.com',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPABASE_URL must not use the example placeholder' in output
    assert 'publishable/anon key must not use the example placeholder' in output
    assert 'secret/service_role key must not use the example placeholder' in output


def test_readiness_check_requires_secret_key_for_server_operations():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'SUPABASE_SECRET_KEY': '',
        'SUPABASE_SERVICE_ROLE_KEY': '',
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/app/persist/backups',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'SUPABASE_SECRET_KEY' in output
    assert 'SUPABASE_SERVICE_ROLE_KEY' in output


def test_readiness_check_accepts_platform_volume_backup_contract():
    env = {
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_ENABLED': 'false',
        'PLATFORM_VOLUME_BACKUPS_ENABLED': 'true',
        'AUTO_BACKUP_INTERVAL_HOURS': '',
        'APP_DATA_BACKUP_DIR': '',
    }

    result = _run_readiness_check(env)

    assert result.returncode == 0
    assert 'production readiness checks passed' in result.stdout


def test_readiness_check_rejects_deployment_without_any_backup_contract():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_ENABLED': 'false',
        'PLATFORM_VOLUME_BACKUPS_ENABLED': 'false',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'PLATFORM_VOLUME_BACKUPS_ENABLED must be true' in output


def test_portable_zip_cannot_replace_independent_platform_backup():
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_ENABLED': 'true',
        'PLATFORM_VOLUME_BACKUPS_ENABLED': 'false',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/app/persist/backups',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert 'independent recovery boundary' in output


@pytest.mark.parametrize(
    ('supabase_url', 'expected_error'),
    [
        ('not-a-url', 'SUPABASE_URL must be a valid HTTPS URL'),
        ('http://test-project.supabase.co', 'SUPABASE_URL must be a valid HTTPS URL'),
        (
            'https://127.0.0.1:54321',
            'SUPABASE_URL must not use a local address in production',
        ),
        (
            'https://localhost',
            'SUPABASE_URL must not use a local address in production',
        ),
        (
            'https://supabase.internal.local',
            'SUPABASE_URL must not use a local address in production',
        ),
    ],
)
def test_readiness_check_rejects_unsafe_supabase_url(
    supabase_url,
    expected_error,
):
    result = _run_readiness_check({
        **_SAFE_SUPABASE_ENV,
        'FLASK_ENV': 'production',
        'SUPABASE_URL': supabase_url,
        'CORS_ORIGINS': 'https://app.example.com',
        'METRICS_AUTH_TOKEN': 'metrics-token',
        'ENCRYPTION_SECRET': 'x' * 32,
        'REDIS_URL': 'redis://redis:6379/0',
        'AUTO_BACKUP_INTERVAL_HOURS': '6',
        'MAX_BACKUPS': '30',
        'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    })

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert expected_error in output


def test_package_json_exposes_verify_production_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:production'] == (
        'node scripts/run_python.cjs scripts/check_production_readiness.py'
    )
