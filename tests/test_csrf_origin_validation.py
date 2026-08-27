"""CSRF origin checks must compare parsed origins, never hostname prefixes."""

from app import create_app


def _client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('SCHEDULER_ENABLED', 'false')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    app = create_app({'TESTING': False, 'RATELIMIT_ENABLED': False})
    return app.test_client()


def test_origin_hostname_prefix_is_rejected(monkeypatch):
    response = _client(monkeypatch).post(
        '/missing',
        base_url='https://app.example.com',
        headers={'Origin': 'https://app.example.com.evil.test'},
        json={},
    )

    assert response.status_code == 403
    assert response.get_json()['error'].startswith('CSRF')


def test_exact_configured_origin_is_allowed(monkeypatch):
    response = _client(monkeypatch).post(
        '/missing',
        base_url='http://internal-service',
        headers={'Origin': 'https://app.example.com'},
        json={},
    )

    assert response.status_code == 404


def test_referer_hostname_prefix_is_rejected(monkeypatch):
    response = _client(monkeypatch).post(
        '/missing',
        base_url='https://app.example.com',
        headers={'Referer': 'https://app.example.com.evil.test/form'},
        json={},
    )

    assert response.status_code == 403
