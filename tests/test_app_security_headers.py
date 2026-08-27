"""Application-level security header integration tests."""

import pytest
from flask import jsonify, request

from app import create_app
from utils.production_readiness import PRODUCTION_CONTENT_SECURITY_POLICY


def _set_common_env(monkeypatch, flask_env: str) -> None:
    monkeypatch.setenv('FLASK_ENV', flask_env)
    monkeypatch.setenv('SCHEDULER_ENABLED', 'false')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('PUBLIC_ORIGIN', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', 'test-metrics-token')
    monkeypatch.setenv('ENCRYPTION_SECRET', 'x' * 32)
    monkeypatch.setenv('AUTO_BACKUP_ENABLED', 'false')
    monkeypatch.setenv('PLATFORM_VOLUME_BACKUPS_ENABLED', 'true')
    monkeypatch.setenv('SUPABASE_URL', 'https://project-ref.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test')
    monkeypatch.setenv('SUPABASE_SECRET_KEY', 'sb_secret_test')


def test_production_csp_is_applied_to_success_and_error_responses(monkeypatch):
    _set_common_env(monkeypatch, 'production')
    monkeypatch.delenv('CONTENT_SECURITY_POLICY', raising=False)
    app = create_app({'TESTING': True})
    client = app.test_client()

    success = client.get('/health', base_url='https://app.example.com')
    not_found = client.get('/missing', base_url='https://app.example.com')

    assert success.status_code == 200
    assert not_found.status_code == 404
    for response in (success, not_found):
        assert (
            response.headers['Content-Security-Policy']
            == PRODUCTION_CONTENT_SECURITY_POLICY
        )
        assert "'unsafe-inline'" not in response.headers['Content-Security-Policy']
        assert "'unsafe-eval'" not in response.headers['Content-Security-Policy']


def test_development_custom_csp_is_applied_verbatim(monkeypatch):
    _set_common_env(monkeypatch, 'development')
    custom_csp = "default-src 'none'; frame-ancestors 'none'"
    monkeypatch.setenv('CONTENT_SECURITY_POLICY', custom_csp)
    app = create_app({'TESTING': True})

    response = app.test_client().get('/health')

    assert response.status_code == 200
    assert response.headers['Content-Security-Policy'] == custom_csp


def test_production_boot_fails_without_canonical_public_origin(monkeypatch):
    _set_common_env(monkeypatch, 'production')
    monkeypatch.delenv('PUBLIC_ORIGIN')

    with pytest.raises(RuntimeError, match='PUBLIC_ORIGIN is required'):
        create_app({'TESTING': True})


def test_production_boot_requires_independent_platform_backup(monkeypatch):
    _set_common_env(monkeypatch, 'production')
    monkeypatch.setenv('PLATFORM_VOLUME_BACKUPS_ENABLED', 'false')

    with pytest.raises(
        RuntimeError,
        match='PLATFORM_VOLUME_BACKUPS_ENABLED must be true in production',
    ):
        create_app({'TESTING': True})


def test_production_boot_requires_supabase_admin_secret(monkeypatch):
    _set_common_env(monkeypatch, 'production')
    monkeypatch.delenv('SUPABASE_SECRET_KEY')
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)

    with pytest.raises(RuntimeError, match='SUPABASE_SECRET_KEY'):
        create_app({'TESTING': True})


def test_one_normalized_proxy_hop_restores_client_ip_https_and_host(monkeypatch):
    _set_common_env(monkeypatch, 'production')
    app = create_app({'TESTING': True})

    @app.get('/_proxy-contract')
    def proxy_contract():
        return jsonify({
            'remote_addr': request.remote_addr,
            'scheme': request.scheme,
            'host': request.host,
        })

    response = app.test_client().get(
        '/_proxy-contract',
        base_url='http://railway-internal',
        headers={
            'X-Forwarded-For': '203.0.113.25',
            'X-Forwarded-Proto': 'https',
            'X-Forwarded-Host': 'app.example.com',
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        'remote_addr': '203.0.113.25',
        'scheme': 'https',
        'host': 'app.example.com',
    }
    assert response.headers['Strict-Transport-Security'].startswith('max-age=')
