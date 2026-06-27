"""Production authentication mode fail-closed behavior."""

from flask import Flask, g, jsonify

from src.contexts.identity.interface import auth_decorators


def _app():
    app = Flask(__name__)

    @app.route('/protected')
    @auth_decorators.require_auth
    def protected():
        return jsonify({'userId': g.get('user_id')})

    return app


def test_production_requires_explicit_edge_mode_when_supabase_is_disabled(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('AUTH_MODE', raising=False)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: False)

    response = _app().test_client().get('/protected')

    assert response.status_code == 503
    assert response.get_json()['code'] == 'AUTH_PROVIDER_NOT_CONFIGURED'


def test_production_edge_mode_allows_edge_basic_auth_deployment(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('AUTH_MODE', 'edge')
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: False)

    response = _app().test_client().get('/protected')

    assert response.status_code == 200
    assert response.get_json() == {'userId': None}


def test_development_keeps_supabase_disabled_bypass(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.delenv('AUTH_MODE', raising=False)
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: False)

    response = _app().test_client().get('/protected')

    assert response.status_code == 200
    assert response.get_json() == {'userId': None}
