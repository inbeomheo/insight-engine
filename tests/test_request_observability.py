"""Request correlation headers and access logging."""
import logging
import re

from app import create_app


REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9._:-]{1,128}$')


def test_response_includes_generated_request_id_header():
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health')

    request_id = response.headers.get('X-Request-ID')
    assert response.status_code == 200
    assert request_id
    assert REQUEST_ID_RE.fullmatch(request_id)


def test_response_preserves_safe_client_request_id_header():
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', headers={'X-Request-ID': 'client.req-123'})

    assert response.headers['X-Request-ID'] == 'client.req-123'


def test_response_replaces_unsafe_client_request_id_header():
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', headers={'X-Request-ID': 'bad request id'})

    request_id = response.headers['X-Request-ID']
    assert request_id != 'bad request id'
    assert REQUEST_ID_RE.fullmatch(request_id)


def test_500_response_includes_request_id_for_support_correlation():
    app = create_app({'TESTING': True, 'PROPAGATE_EXCEPTIONS': False})

    @app.route('/boom')
    def boom():
        raise RuntimeError('boom')

    client = app.test_client()

    response = client.get('/boom', headers={'X-Request-ID': 'support-case-42'})
    payload = response.get_json()

    assert response.status_code == 500
    assert response.headers['X-Request-ID'] == 'support-case-42'
    assert payload['requestId'] == 'support-case-42'
    assert payload['error'].startswith('[서버 오류]')


def test_access_log_includes_request_id_release_method_path_status_and_duration(caplog, monkeypatch):
    monkeypatch.setenv('APP_RELEASE', 'unit-release')
    app = create_app({'TESTING': True})
    client = app.test_client()

    with caplog.at_level(logging.INFO, logger='api.access'):
        response = client.get('/health', headers={'X-Request-ID': 'log-req-1'})

    assert response.status_code == 200
    log_text = '\n'.join(record.getMessage() for record in caplog.records)
    assert (
        'request_complete request_id=log-req-1 release=unit-release '
        'method=GET path=/health status=200 duration_ms='
    ) in log_text
