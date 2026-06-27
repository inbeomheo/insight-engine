"""CMS workflow routes require app authentication."""

from app import create_app
from src.contexts.identity.interface import auth_decorators


def _client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)
    app = create_app({'TESTING': True})
    return app.test_client()


def test_cms_publish_all_requires_auth(monkeypatch):
    client = _client(monkeypatch)

    response = client.post(
        '/api/cms/publish-all',
        json={
            'plugin_ids': ['ghost'],
            'title': 'Title',
            'content': 'Body',
            'plugin_configs': {},
        },
        headers={'Origin': 'http://localhost:3000'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'


def test_cms_validate_config_requires_auth(monkeypatch):
    client = _client(monkeypatch)

    response = client.post(
        '/api/cms/validate-config',
        json={'plugin_id': 'ghost', 'config': {}},
        headers={'Origin': 'http://localhost:3000'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'
