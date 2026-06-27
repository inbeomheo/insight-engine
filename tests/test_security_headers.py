"""Security header defaults for production-facing responses."""
import json
from pathlib import Path

from app import create_app
from utils.production_readiness import default_content_security_policy


ROOT = Path(__file__).resolve().parents[1]
SAFE_METRICS_AUTH_TOKEN = 'metrics-token-1234567890abcdefABCDEF'
SAFE_SECRET_KEY = 'flask-secret-1234567890abcdefABCDEF'
SAFE_ENCRYPTION_SECRET = 'encrypt-secret-1234567890abcdefABCDEF'


def test_flask_responses_include_hardened_security_headers(monkeypatch):
    monkeypatch.setenv('CONTENT_SECURITY_POLICY', "default-src 'self'; script-src 'self'")
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health')

    assert response.headers['Content-Security-Policy'] == "default-src 'self'; script-src 'self'"
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-XSS-Protection'] == '0'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert 'camera=()' in response.headers['Permissions-Policy']


def test_flask_hsts_is_enabled_for_secure_requests(monkeypatch):
    monkeypatch.setenv('CONTENT_SECURITY_POLICY', default_content_security_policy('production'))
    app = create_app({'TESTING': True})
    client = app.test_client()

    response = client.get('/health', base_url='https://api.example.com')

    assert response.headers['Strict-Transport-Security'] == (
        'max-age=31536000; includeSubDomains; preload'
    )


def test_flask_secret_key_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-with-more-than-32-chars')
    app = create_app({'TESTING': True})

    assert app.secret_key == 'test-secret-key-with-more-than-32-chars'


def test_flask_session_cookies_are_secure_in_production(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('FLASK_DEBUG', '0')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)
    app = create_app({'TESTING': True})

    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_flask_rejects_debug_flags_in_production(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    monkeypatch.setenv('CORS_ORIGINS', 'https://app.example.com')
    monkeypatch.setenv('METRICS_AUTH_TOKEN', SAFE_METRICS_AUTH_TOKEN)
    monkeypatch.setenv('SECRET_KEY', SAFE_SECRET_KEY)
    monkeypatch.setenv('ENCRYPTION_SECRET', SAFE_ENCRYPTION_SECRET)

    try:
        create_app({'TESTING': True})
    except RuntimeError as exc:
        assert 'FLASK_DEBUG must be disabled in production' in str(exc)
    else:
        raise AssertionError('expected production debug configuration to fail closed')


def test_flask_session_cookies_are_httponly_in_development(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('SESSION_COOKIE_SECURE', '')
    app = create_app({'TESTING': True})

    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_flask_session_cookie_secure_can_be_forced_outside_production(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'true')
    app = create_app({'TESTING': True})

    assert app.config['SESSION_COOKIE_SECURE'] is True


def test_caddy_edge_adds_common_security_headers_without_frontend_csp():
    caddyfile = (ROOT / 'Caddyfile.deploy').read_text(encoding='utf-8')

    assert 'X-Content-Type-Options nosniff' in caddyfile
    assert 'X-Frame-Options DENY' in caddyfile
    assert 'X-XSS-Protection "0"' in caddyfile
    assert 'Referrer-Policy strict-origin-when-cross-origin' in caddyfile
    assert 'Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()"' in caddyfile
    assert 'Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"' in caddyfile
    assert 'Content-Security-Policy' not in caddyfile


def test_caddy_allows_only_signed_inbound_webhooks_before_basic_auth():
    caddyfile = (ROOT / 'Caddyfile.deploy').read_text(encoding='utf-8')

    assert caddyfile.index('handle @signedInboundWebhook') < caddyfile.index('basic_auth')
    for path in (
        '/api/payment/webhook',
        '/api/paddle/webhook',
        '/api/crypto/webhook',
        '/api/webhooks/slack',
        '/api/webhooks/discord',
        '/api/webhooks/telegram',
    ):
        assert path in caddyfile
    assert '/api/make/webhook' not in caddyfile


def test_caddy_routes_graphql_to_backend_behind_basic_auth():
    caddyfile = (ROOT / 'Caddyfile.deploy').read_text(encoding='utf-8')
    backend_matcher = next(line.strip() for line in caddyfile.splitlines() if line.strip().startswith('@backend path '))

    assert caddyfile.index('basic_auth') < caddyfile.index('@backend path')
    assert '/graphql' in backend_matcher
    assert '/graphql/*' in backend_matcher


def test_caddy_overwrites_forwarded_headers_for_each_reverse_proxy():
    caddyfile = (ROOT / 'Caddyfile.deploy').read_text(encoding='utf-8')

    reverse_proxy_count = sum(
        1
        for line in caddyfile.splitlines()
        if line.strip().startswith('reverse_proxy')
    )

    assert reverse_proxy_count > 0
    assert caddyfile.count('header_up X-Forwarded-Host {host}') == reverse_proxy_count
    assert caddyfile.count('header_up X-Forwarded-Proto {scheme}') == reverse_proxy_count


def test_caddy_validator_enforces_graphql_backend_route():
    validator = (ROOT / 'scripts' / 'validate_caddy_config.sh').read_text(encoding='utf-8')

    assert "'/graphql'" in validator
    assert "'/graphql/*'" in validator
    assert 'Caddy @backend matcher must include %s' in validator


def test_caddy_validator_enforces_public_route_contract():
    validator = (ROOT / 'scripts' / 'validate_caddy_config.sh').read_text(encoding='utf-8')

    assert '@publicShare' in validator
    assert '@signedInboundWebhook' in validator
    assert 'method GET' in validator
    assert 'method POST' in validator
    assert '/api/shares/*' in validator
    assert 'must not expose protected /api/shares create route' in validator
    assert 'public matchers must not expose protected path %s' in validator
    assert 'must remain before basic_auth' in validator
    assert 'X-Forwarded-Host' in validator
    assert 'X-Forwarded-Proto' in validator


def test_local_deploy_recreates_edge_for_caddyfile_changes():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    deploy_script = (ROOT / 'scripts' / 'deploy_local.sh').read_text(encoding='utf-8')

    assert package_json['scripts']['deploy:local'] == 'bash scripts/deploy_local.sh'
    assert 'APP_RELEASE="${APP_RELEASE:-$GIT_SHA}"' in deploy_script
    assert 'preserve_rollback_image || true' in deploy_script
    assert 'trap rollback_on_deploy_error ERR' in deploy_script
    assert 'INSIGHT_EXPECTED_RELEASE="$APP_RELEASE"' in deploy_script
    assert 'INSIGHT_EXPECTED_GIT_SHA="$GIT_SHA"' in deploy_script
    assert 'exec -T backend python3 scripts/backup_app_data.py backup --summary' in deploy_script
    assert 'up -d --build --wait --wait-timeout 180 --remove-orphans backend frontend' in deploy_script
    assert 'up -d --force-recreate --no-deps --wait --wait-timeout 60 --remove-orphans edge' in deploy_script
    assert 'npm run ops:monitor' in deploy_script
    assert 'trap - ERR' in deploy_script
    assert 'npm run docker:cleanup' in deploy_script
