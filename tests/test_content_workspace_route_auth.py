"""Content workspace write routes require app authentication."""

import pytest

from app import create_app
from src.contexts.identity.interface import auth_decorators


def _client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)
    app = create_app({'TESTING': True})
    return app.test_client()


@pytest.mark.parametrize(
    ('method', 'path'),
    (
        ('POST', '/api/content/content-1/versions'),
        ('POST', '/api/content/content-1/versions/version-1/restore'),
        ('POST', '/api/folders'),
        ('PUT', '/api/folders/folder-1'),
        ('DELETE', '/api/folders/folder-1'),
        ('PUT', '/api/content/content-1/folder'),
        ('POST', '/api/notifications/notification-1/read'),
        ('POST', '/api/notifications/read-all'),
        ('POST', '/api/collab/session'),
        ('POST', '/api/collab/session/session-1/update'),
        ('POST', '/api/collab/session/session-1/heartbeat'),
        ('POST', '/api/collab/session/session-1/leave'),
    ),
)
def test_content_workspace_write_routes_require_auth(monkeypatch, method, path):
    client = _client(monkeypatch)

    response = client.open(
        path,
        method=method,
        json={},
        headers={'Origin': 'http://localhost:3000'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'
