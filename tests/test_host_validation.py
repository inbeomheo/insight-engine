"""Production Host header validation."""

from app import create_app


SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'


def _set_production_env(monkeypatch, *, trusted_hosts=''):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('TRUSTED_HOSTS', trusted_hosts)
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)


def test_production_allows_cors_origin_host(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', base_url='https://app.example.com')

    assert response.status_code == 200


def test_production_rejects_untrusted_host(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', base_url='https://evil.example.com')

    assert response.status_code == 400
    assert 'Host' in response.get_json()['error']


def test_production_rejects_spoofed_x_forwarded_host(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get(
        '/health',
        base_url='https://app.example.com',
        headers={'X-Forwarded-Host': 'evil.example.com'},
    )

    assert response.status_code == 400


def test_production_allows_explicit_trusted_host(monkeypatch):
    _set_production_env(monkeypatch, trusted_hosts='admin.example.com')
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', base_url='https://admin.example.com')

    assert response.status_code == 200


def test_production_allows_local_healthcheck_host(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', base_url='http://127.0.0.1:5001')

    assert response.status_code == 200
