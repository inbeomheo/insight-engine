"""Protected Prometheus metrics endpoint."""

from app import create_app


METRICS_TOKEN = 'metrics-token-1234567890abcdefABCDEF'


def _client(monkeypatch, *, token=METRICS_TOKEN):
    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', token)
    app = create_app({'TESTING': True})
    return app.test_client()


def test_metrics_requires_auth_when_token_is_configured(monkeypatch):
    client = _client(monkeypatch)

    response = client.get('/metrics')

    assert response.status_code == 401
    assert response.headers['WWW-Authenticate'] == 'Bearer realm="metrics"'


def test_metrics_rejects_wrong_token(monkeypatch):
    client = _client(monkeypatch)

    response = client.get('/metrics', headers={'Authorization': 'Bearer wrong-token'})

    assert response.status_code == 403


def test_metrics_accepts_bearer_token_and_omits_secret(monkeypatch):
    client = _client(monkeypatch)

    response = client.get('/metrics', headers={'Authorization': f'Bearer {METRICS_TOKEN}'})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type == 'text/plain; version=0.0.4; charset=utf-8'
    assert 'insight_engine_info{' in body
    assert 'insight_engine_requests_total' in body
    assert 'insight_engine_errors_total' in body
    assert METRICS_TOKEN not in body


def test_metrics_accepts_x_metrics_auth_token_header(monkeypatch):
    client = _client(monkeypatch)

    response = client.get('/metrics', headers={'X-Metrics-Auth-Token': METRICS_TOKEN})

    assert response.status_code == 200


def test_metrics_can_run_without_token_outside_production(monkeypatch):
    client = _client(monkeypatch, token='')

    response = client.get('/metrics')

    assert response.status_code == 200
    assert 'insight_engine_active_requests' in response.get_data(as_text=True)


def test_metrics_reports_server_error_when_production_token_is_missing(monkeypatch):
    client = _client(monkeypatch, token='')
    monkeypatch.setenv('FLASK_ENV', 'production')

    response = client.get('/metrics', headers={'Authorization': 'Bearer any-token'})

    assert response.status_code == 503
    assert 'not configured' in response.get_data(as_text=True)
