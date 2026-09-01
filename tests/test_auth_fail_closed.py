"""production 인증 fail-closed / 개발 AUTH_BYPASS 테스트."""
from unittest.mock import patch

from flask import Flask, g, jsonify

from src.contexts.identity.interface.auth_decorators import require_auth
from src.contexts.identity.interface.auth_policy import is_auth_bypass_allowed


def _app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected")
    @require_auth
    def protected():
        return jsonify({"ok": True, "user_id": getattr(g, "user_id", "missing")})

    return app


def test_production_without_supabase_returns_503(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("AUTH_BYPASS", "false")
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected")
    assert resp.status_code == 503
    assert resp.get_json()["code"] == "AUTH_UNAVAILABLE"


def test_production_ignores_auth_bypass(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("AUTH_BYPASS", "true")
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected")
    assert resp.status_code == 503
    assert is_auth_bypass_allowed() is False


def test_development_bypass_allows_request(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("AUTH_BYPASS", "true")
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected")
    assert resp.status_code == 200
    assert resp.get_json()["user_id"] is None


def test_development_without_bypass_returns_401(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("AUTH_BYPASS", "false")
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "AUTH_REQUIRED"


def test_testing_bypass_allows_request(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("AUTH_BYPASS", "true")
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected")
    assert resp.status_code == 200


def test_production_accepts_signed_trusted_proxy(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "trusted_proxy")
    monkeypatch.setenv("AUTH_PROXY_SECRET", "s" * 64)
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected", headers={
            "X-Insight-Proxy-Secret": "s" * 64,
            "X-Insight-Proxy-User": "inbeom",
        })
    assert resp.status_code == 200
    assert resp.get_json()["user_id"] == "proxy_inbeom"


def test_production_rejects_forged_trusted_proxy(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "trusted_proxy")
    monkeypatch.setenv("AUTH_PROXY_SECRET", "s" * 64)
    with patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    ):
        client = _app().test_client()
        resp = client.get("/protected", headers={
            "X-Insight-Proxy-Secret": "wrong" * 16,
            "X-Insight-Proxy-User": "inbeom",
        })
    assert resp.status_code == 503
    assert resp.get_json()["code"] == "AUTH_UNAVAILABLE"
