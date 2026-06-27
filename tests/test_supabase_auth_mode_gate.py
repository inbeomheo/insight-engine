"""Production AUTH_MODE=supabase enforces a global app auth gate."""

from unittest.mock import patch

from app import create_app
from src.contexts.identity.interface import auth_decorators


SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'


def _set_supabase_production_env(monkeypatch, tmp_path):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('AUTH_MODE', 'supabase')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)
    monkeypatch.setenv('SUPABASE_URL', 'https://project.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')
    monkeypatch.setenv('SHARE_PAGE_DIR', str(tmp_path / 'shares'))


def _client(monkeypatch, tmp_path):
    _set_supabase_production_env(monkeypatch, tmp_path)
    app = create_app({'TESTING': True})
    return app.test_client()


def test_supabase_auth_mode_rejects_undecorated_private_get(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)

    response = client.get('/api/mcp/plugins')

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'


def test_supabase_auth_mode_rejects_when_provider_missing(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: False)

    response = client.get('/api/mcp/plugins')

    assert response.status_code == 503
    assert response.get_json()['code'] == 'AUTH_PROVIDER_NOT_CONFIGURED'


def test_supabase_auth_mode_allows_public_auth_config(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)

    response = client.get('/api/auth/config')

    assert response.status_code == 200
    assert response.get_json()['enabled'] is True


def test_supabase_auth_mode_allows_public_share_reads(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)

    response = client.get('/api/shares/missing-share')

    assert response.status_code == 404
    assert response.get_json()['error'] == '공유 페이지를 찾을 수 없습니다.'


def test_supabase_auth_mode_allows_signed_webhooks_to_reach_signature_check(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)

    with patch('services.integrations.slack_bot_service.slack_bot_service') as slack_bot_service:
        slack_bot_service.verify_signature.return_value = False
        response = client.post(
            '/api/webhooks/slack',
            data=b'{}',
            headers={
                'X-Slack-Request-Timestamp': '1782560000',
                'X-Slack-Signature': 'v0=bad',
            },
        )

    assert response.status_code == 401
    assert 'Slack' in response.get_json()['error']


def test_supabase_auth_mode_validates_private_route_once(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    calls = []

    def fake_validate(token):
        calls.append(token)
        from flask import g
        g.user_id = 'user-1'
        g.user_email = 'user@example.com'
        g.access_token = token
        return {'valid': True, 'error': None, 'code': None}

    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)
    monkeypatch.setattr(auth_decorators, '_validate_token', fake_validate)

    response = client.post(
        '/api/providers/validate',
        json={},
        headers={'Authorization': 'Bearer valid-token'},
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'provider_id가 필요합니다.'
    assert calls == ['valid-token']
