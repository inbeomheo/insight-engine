"""Automation integration routes require auth or webhook secrets."""

import pytest

from app import create_app
from src.contexts.identity.interface import auth_decorators


def _client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    app = create_app({'TESTING': True})
    return app.test_client()


def _auth_enforced_client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)
    app = create_app({'TESTING': True})
    return app.test_client()


@pytest.mark.parametrize(
    ('path', 'payload'),
    (
        ('/api/webhooks/telegram/setwebhook', {'webhook_url': 'https://app.example.com/api/webhooks/telegram'}),
        ('/api/sync/airtable', {'title': 'Title', 'content': 'Body'}),
        ('/api/sync/gsheets', {'title': 'Title', 'content': 'Body'}),
        ('/api/webhook-relay', {'urls': ['https://hooks.example.com/a'], 'payload': {'ok': True}}),
    ),
)
def test_user_triggered_automation_routes_require_auth(monkeypatch, path, payload):
    client = _auth_enforced_client(monkeypatch)

    response = client.post(
        path,
        json=payload,
        headers={'Origin': 'http://localhost:3000'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'


@pytest.mark.parametrize(
    'path',
    (
        '/api/zapier/trigger',
        '/api/make/webhook',
        '/api/ifttt/trigger',
    ),
)
def test_automation_inbound_routes_fail_closed_without_secret_in_production(monkeypatch, path):
    client = _client(monkeypatch)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('AUTOMATION_WEBHOOK_SECRET', raising=False)

    response = client.post(path, json={})

    assert response.status_code == 503
    assert response.get_json()['code'] == 'AUTOMATION_WEBHOOK_SECRET_NOT_CONFIGURED'


def test_automation_inbound_routes_reject_wrong_secret(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setenv('AUTOMATION_WEBHOOK_SECRET', 'automation-secret-1234567890abcdef')

    response = client.post(
        '/api/ifttt/trigger',
        json={},
        headers={'X-Insight-Webhook-Secret': 'wrong'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTOMATION_WEBHOOK_AUTH_FAILED'


def test_automation_inbound_routes_accept_configured_secret(monkeypatch):
    client = _client(monkeypatch)
    secret = 'automation-secret-1234567890abcdef'
    monkeypatch.setenv('AUTOMATION_WEBHOOK_SECRET', secret)

    response = client.post(
        '/api/zapier/trigger',
        json={},
        headers={'X-Insight-Webhook-Secret': secret},
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'url이 필요합니다.'


def test_zapier_auth_test_accepts_bearer_webhook_secret(monkeypatch):
    client = _client(monkeypatch)
    secret = 'automation-secret-1234567890abcdef'
    monkeypatch.setenv('AUTOMATION_WEBHOOK_SECRET', secret)

    response = client.get(
        '/api/zapier/auth/test',
        headers={'Authorization': f'Bearer {secret}'},
    )

    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_telegram_webhook_fails_closed_without_secret_in_production(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('TELEGRAM_WEBHOOK_SECRET', raising=False)

    response = client.post('/api/webhooks/telegram', json={})

    assert response.status_code == 503
    assert response.get_json()['code'] == 'TELEGRAM_WEBHOOK_SECRET_NOT_CONFIGURED'


def test_telegram_webhook_rejects_wrong_secret(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'telegram-secret-1234567890abcdef')

    response = client.post(
        '/api/webhooks/telegram',
        json={},
        headers={'X-Telegram-Bot-Api-Secret-Token': 'wrong'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'TELEGRAM_WEBHOOK_AUTH_FAILED'


def test_telegram_webhook_accepts_configured_secret(monkeypatch):
    client = _client(monkeypatch)
    secret = 'telegram-secret-1234567890abcdef'
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', secret)

    response = client.post(
        '/api/webhooks/telegram',
        json={},
        headers={'X-Telegram-Bot-Api-Secret-Token': secret},
    )

    assert response.status_code == 200
    assert response.get_json()['ok'] is True
