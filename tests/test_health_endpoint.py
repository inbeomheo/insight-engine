"""Public health endpoint data minimization."""

from app import create_app


METRICS_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'


def _set_production_env(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', METRICS_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)


def test_public_production_health_omits_runtime_counters(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health')
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['status'] == 'healthy'
    assert payload['environment'] == 'production'
    assert 'release' in payload
    assert 'request_count' not in payload
    assert 'error_count' not in payload
    assert 'error_rate' not in payload
    assert 'memory_usage_mb' not in payload


def test_production_health_includes_runtime_counters_with_metrics_token(monkeypatch):
    _set_production_env(monkeypatch)
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', headers={'Authorization': f'Bearer {METRICS_TOKEN}'})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['status'] == 'healthy'
    assert 'request_count' in payload
    assert 'error_count' in payload
    assert 'error_rate' in payload
    assert 'memory_usage_mb' in payload


def test_development_health_keeps_runtime_counters(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', '')
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health')
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['environment'] == 'development'
    assert 'request_count' in payload
    assert 'error_rate' in payload
