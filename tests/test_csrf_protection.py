"""CSRF origin enforcement for production deployments."""

from unittest.mock import patch

from app import create_app


SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'


def _set_security_env(monkeypatch, *, flask_env):
    monkeypatch.setenv('FLASK_ENV', flask_env)
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)


def test_csrf_rejects_file_origin_in_production(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    response = client.post('/api/close', json={'clientId': 'csrf-prod'}, headers={'Origin': 'file://'})

    assert response.status_code == 403
    assert 'CSRF' in response.get_json()['error']


def test_csrf_allows_configured_https_origin_in_production(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    response = client.post(
        '/api/close',
        json={'clientId': 'csrf-prod'},
        headers={'Origin': 'https://app.example.com'},
    )

    assert response.status_code == 200
    assert response.get_json()['ok'] is True


def test_csrf_rejects_origin_with_allowed_host_prefix(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    response = client.post(
        '/api/close',
        base_url='https://app.example.com',
        json={'clientId': 'csrf-prefix-origin'},
        headers={'Origin': 'https://app.example.com.evil.test'},
    )

    assert response.status_code == 403
    assert 'CSRF' in response.get_json()['error']


def test_csrf_rejects_referer_with_allowed_host_prefix(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    response = client.post(
        '/api/close',
        base_url='https://app.example.com',
        json={'clientId': 'csrf-prefix-referer'},
        headers={'Referer': 'https://app.example.com.evil.test/path'},
    )

    assert response.status_code == 403
    assert 'CSRF' in response.get_json()['error']


def test_csrf_keeps_file_origin_exception_for_development(monkeypatch):
    _set_security_env(monkeypatch, flask_env='development')
    app = create_app()
    client = app.test_client()

    response = client.post('/api/close', json={'clientId': 'csrf-dev'}, headers={'Origin': 'file://'})

    assert response.status_code == 200
    assert response.get_json()['ok'] is True


def test_csrf_allows_signed_payment_webhook_without_browser_origin(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    with patch('services.payment.stripe_service.stripe_service') as stripe_service:
        stripe_service.handle_webhook.return_value = {'success': True}
        response = client.post(
            '/api/payment/webhook',
            data=b'payload',
            headers={'Stripe-Signature': 'signed'},
        )

    assert response.status_code == 200


def test_csrf_allows_signed_integration_webhook_to_verify_signature(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

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


def test_csrf_still_rejects_ordinary_post_without_browser_origin(monkeypatch):
    _set_security_env(monkeypatch, flask_env='production')
    app = create_app()
    client = app.test_client()

    response = client.post('/api/close', json={'clientId': 'csrf-prod'})

    assert response.status_code == 403
    assert 'CSRF' in response.get_json()['error']
