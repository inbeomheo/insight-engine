"""Production readiness monitor script behavior."""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'monitor_readiness.py'
TEST_GIT_SHA = 'abcdef1234567890abcdef1234567890abcdef12'


def _monitor_env(**overrides):
    env = os.environ.copy()
    for key in (
        'METRICS_AUTH_TOKEN',
        'MONITOR_METRICS_AUTH_TOKEN',
        'ALERT_WEBHOOK_URL',
        'MONITOR_WEBHOOK_URL',
        'ALERT_WEBHOOK_REQUIRED',
        'MONITOR_WEBHOOK_REQUIRED',
    ):
        env.pop(key, None)
    env.update(overrides)
    return env


def _load_monitor_module():
    spec = importlib.util.spec_from_file_location('monitor_readiness', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


monitor_readiness = _load_monitor_module()


class _JsonHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append({
            'method': 'GET',
            'path': self.path,
            'headers': {key: value for key, value in self.headers.items()},
        })
        status_code, payload = self.server.routes.get(self.path, (404, {'error': 'not found'}))
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        for name, value in self.server.response_headers.items():
            self.send_header(name, value)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or '0')
        body = self.rfile.read(length)
        if self.path in self.server.post_routes:
            status_code, payload, headers = self.server.post_routes[self.path]
            response = json.dumps(payload).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            for name, value in self.server.response_headers.items():
                self.send_header(name, value)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return
        self.server.posts.append(json.loads(body.decode('utf-8')))
        response = b'{"ok": true}'
        self.send_response(self.server.post_status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *args):
        return


class _Server:
    def __init__(self, routes=None, post_status_code=200, response_headers=None, post_routes=None):
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), _JsonHandler)
        self.httpd.routes = routes or {}
        self.httpd.requests = []
        self.httpd.posts = []
        self.httpd.post_status_code = post_status_code
        self.httpd.post_routes = post_routes if post_routes is not None else {
            '/api/crypto/webhook': (401, {'error': '웹훅 서명 검증 실패'}, {}),
        }
        self.httpd.response_headers = response_headers if response_headers is not None else {
            'Content-Security-Policy': "default-src 'self'; script-src 'self'",
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '0',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
            'X-Request-ID': 'monitor-test-request',
        }
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    @property
    def base_url(self):
        host, port = self.httpd.server_address
        return f'http://{host}:{port}'

    @property
    def posts(self):
        return self.httpd.posts

    @property
    def requests(self):
        return self.httpd.requests


def _ready_routes():
    return {
        '/health': (
            200,
            {
                'status': 'healthy',
                'release': {
                    'version': 'v2.0',
                    'release': 'test-release',
                    'gitSha': TEST_GIT_SHA,
                    'buildTime': '2026-06-27T08:00:00Z',
                },
            },
        ),
        '/ready': (200, {'status': 'ready'}),
        '/': (401, {'error': 'Unauthorized'}),
    }


def test_monitor_readiness_passes_with_edge_auth_challenge():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1)

    assert report['status'] == 'ready'
    assert report['release']['release'] == 'test-release'
    assert [check['name'] for check in report['checks']] == [
        'health',
        'ready',
        'security_headers',
        'request_id_header',
        'edge_auth',
        'signed_webhook_edge_route',
    ]
    assert all(check['ok'] for check in report['checks'])


def test_monitor_readiness_detects_signed_webhook_blocked_by_basic_auth():
    with _Server(
        _ready_routes(),
        post_routes={
            '/api/crypto/webhook': (
                401,
                {},
                {'WWW-Authenticate': 'Basic realm="restricted"'},
            ),
        },
    ) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1)

    webhook_check = next(check for check in report['checks'] if check['name'] == 'signed_webhook_edge_route')
    assert report['status'] == 'not_ready'
    assert webhook_check['ok'] is False
    assert webhook_check['blocked_by_basic_auth'] is True


def test_monitor_readiness_verifies_expected_release_metadata():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(
            server.base_url,
            timeout=1,
            expected_release='test-release',
            expected_git_sha=TEST_GIT_SHA,
        )

    release_check = next(check for check in report['checks'] if check['name'] == 'release_metadata')
    assert report['status'] == 'ready'
    assert release_check['ok'] is True


def test_monitor_readiness_reports_expected_release_mismatch():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(
            server.base_url,
            timeout=1,
            expected_release='other-release',
            expected_git_sha=TEST_GIT_SHA,
        )

    release_check = next(check for check in report['checks'] if check['name'] == 'release_metadata')
    assert report['status'] == 'not_ready'
    assert release_check['ok'] is False
    assert 'release' in release_check['mismatches']


def test_monitor_readiness_require_https_rejects_http_base_url():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1, require_https=True)

    transport_check = next(check for check in report['checks'] if check['name'] == 'transport_security')
    assert report['status'] == 'not_ready'
    assert transport_check['ok'] is False
    assert transport_check['scheme'] == 'http'


def test_monitor_readiness_require_public_host_rejects_loopback_url():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1, require_public_host=True)

    public_host_check = next(check for check in report['checks'] if check['name'] == 'public_host')
    assert report['status'] == 'not_ready'
    assert public_host_check['ok'] is False
    assert public_host_check['host'] == '127.0.0.1'


def test_monitor_readiness_public_host_accepts_public_dns_resolution():
    with patch.object(
        monitor_readiness.socket,
        'getaddrinfo',
        return_value=[(monitor_readiness.socket.AF_INET, monitor_readiness.socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))],
    ):
        check = monitor_readiness.check_public_host(
            'https://app.example.com',
            require_public_host=True,
        )

    assert check['ok'] is True
    assert check['addresses'] == ['8.8.8.8']


def test_monitor_readiness_public_host_rejects_private_dns_resolution():
    with patch.object(
        monitor_readiness.socket,
        'getaddrinfo',
        return_value=[(monitor_readiness.socket.AF_INET, monitor_readiness.socket.SOCK_STREAM, 6, '', ('10.0.0.5', 443))],
    ):
        check = monitor_readiness.check_public_host(
            'https://app.example.com',
            require_public_host=True,
        )

    assert check['ok'] is False
    assert check['non_public_addresses'] == ['10.0.0.5']


def test_monitor_readiness_reports_tls_certificate_expiry_threshold():
    expires_at = time.time() + 40 * 86400
    with patch.object(monitor_readiness, '_tls_certificate_expires_at_epoch', return_value=expires_at):
        check = monitor_readiness.check_tls_certificate(
            'https://app.example.com',
            timeout=1,
            min_days=30,
        )

    assert check['ok'] is True
    assert check['days_remaining'] >= 39
    assert check['min_days'] == 30


def test_monitor_readiness_reports_tls_certificate_expiring_too_soon():
    expires_at = time.time() + 5 * 86400
    with patch.object(monitor_readiness, '_tls_certificate_expires_at_epoch', return_value=expires_at):
        check = monitor_readiness.check_tls_certificate(
            'https://app.example.com',
            timeout=1,
            min_days=30,
        )

    assert check['ok'] is False
    assert check['days_remaining'] < 30
    assert 'too soon' in check['message']


def test_monitor_readiness_cli_exits_nonzero_for_release_mismatch():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--expected-release',
                'other-release',
                '--expected-git-sha',
                TEST_GIT_SHA,
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    release_check = next(check for check in payload['checks'] if check['name'] == 'release_metadata')
    assert result.returncode == 2
    assert payload['status'] == 'not_ready'
    assert release_check['ok'] is False


def test_monitor_readiness_cli_exits_nonzero_when_https_is_required_for_http_url():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--require-https',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    transport_check = next(check for check in payload['checks'] if check['name'] == 'transport_security')
    assert result.returncode == 2
    assert payload['status'] == 'not_ready'
    assert transport_check['ok'] is False


def test_monitor_readiness_cli_exits_nonzero_when_public_host_is_required_for_local_url():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--require-public-host',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    public_host_check = next(check for check in payload['checks'] if check['name'] == 'public_host')
    assert result.returncode == 2
    assert payload['status'] == 'not_ready'
    assert public_host_check['ok'] is False


def test_monitor_readiness_reports_failed_runtime_components():
    routes = _ready_routes()
    routes['/ready'] = (
        503,
        {
            'status': 'not_ready',
            'components': {
                'redis': {'status': 'error', 'message': 'redis ping failed: TimeoutError'},
                'app_data': {'status': 'ok', 'message': 'writable'},
            },
        },
    )

    with _Server(routes) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1)

    ready_check = next(check for check in report['checks'] if check['name'] == 'ready')
    assert report['status'] == 'not_ready'
    assert ready_check['failed_components'] == {
        'redis': {'status': 'error', 'message': 'redis ping failed: TimeoutError'}
    }


def test_monitor_readiness_uses_metrics_token_for_authenticated_ready_diagnostics():
    routes = _ready_routes()
    routes['/ready'] = (
        200,
        {
            'status': 'ready',
            'components': {
                'redis': {'status': 'ok', 'message': 'redis ping succeeded'},
                'scheduler': {'status': 'ok', 'message': 'scheduler heartbeat is fresh'},
            },
        },
    )

    with _Server(routes) as server:
        report = monitor_readiness.run_checks(
            server.base_url,
            timeout=1,
            metrics_auth_token='monitor-secret-token',
        )
        ready_requests = [request for request in server.requests if request['path'] == '/ready']

    ready_check = next(check for check in report['checks'] if check['name'] == 'ready')
    assert report['status'] == 'ready'
    assert ready_check['authenticated'] is True
    assert ready_check['components_present'] is True
    assert ready_requests[0]['headers']['Authorization'] == 'Bearer monitor-secret-token'
    assert 'monitor-secret-token' not in json.dumps(report)


def test_monitor_readiness_fails_when_authenticated_ready_omits_components():
    with _Server(_ready_routes()) as server:
        report = monitor_readiness.run_checks(
            server.base_url,
            timeout=1,
            metrics_auth_token='monitor-secret-token',
        )

    ready_check = next(check for check in report['checks'] if check['name'] == 'ready')
    assert report['status'] == 'not_ready'
    assert ready_check['ok'] is False
    assert ready_check['authenticated'] is True
    assert ready_check['components_present'] is False
    assert 'diagnostics' in ready_check['message']


def test_monitor_readiness_reports_missing_security_headers():
    with _Server(_ready_routes(), response_headers={}) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1)

    headers_check = next(check for check in report['checks'] if check['name'] == 'security_headers')
    assert report['status'] == 'not_ready'
    assert headers_check['ok'] is False
    assert 'x-content-type-options' in headers_check['missing_or_invalid']


def test_monitor_readiness_reports_missing_request_id_header():
    response_headers = {
        'Content-Security-Policy': "default-src 'self'; script-src 'self'",
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '0',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    }
    with _Server(_ready_routes(), response_headers=response_headers) as server:
        report = monitor_readiness.run_checks(server.base_url, timeout=1)

    request_id_check = next(check for check in report['checks'] if check['name'] == 'request_id_header')
    assert report['status'] == 'not_ready'
    assert request_id_check['ok'] is False
    assert 'X-Request-ID' in request_id_check['message']


def test_monitor_readiness_posts_generic_webhook_alert_without_secrets():
    report = {
        'service': 'insight-engine',
        'status': 'not_ready',
        'base_url': 'https://app.example.com',
        'checks': [{'name': 'ready', 'ok': False}],
    }

    with _Server() as webhook:
        result = monitor_readiness.send_webhook_alert(f'{webhook.base_url}/hook', report, timeout=1)

        assert result['status_code'] == 200
        assert webhook.posts[0]['status'] == 'not_ready'
        assert webhook.posts[0]['text'].startswith('Insight Engine readiness is not_ready')
        assert webhook.posts[0]['content'].startswith('Insight Engine readiness is not_ready')
        assert webhook.posts[0]['base_url'] == 'https://app.example.com'


def test_monitor_readiness_cli_exits_nonzero_for_not_ready(tmp_path):
    routes = _ready_routes()
    routes['/ready'] = (503, {'status': 'not_ready', 'components': {}})

    with _Server(routes) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload['status'] == 'not_ready'
    assert payload['attempt'] == 1
    assert result.stderr == ''


def test_monitor_readiness_cli_reads_metrics_token_from_env_without_printing_secret():
    routes = _ready_routes()
    routes['/ready'] = (
        200,
        {
            'status': 'ready',
            'components': {
                'redis': {'status': 'ok', 'message': 'redis ping succeeded'},
            },
        },
    )

    with _Server(routes) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(MONITOR_METRICS_AUTH_TOKEN='monitor-env-token'),
            text=True,
            capture_output=True,
            check=False,
        )
        ready_requests = [request for request in server.requests if request['path'] == '/ready']

    payload = json.loads(result.stdout)
    ready_check = next(check for check in payload['checks'] if check['name'] == 'ready')
    assert result.returncode == 0
    assert ready_check['authenticated'] is True
    assert ready_check['components_present'] is True
    assert ready_requests[0]['headers']['Authorization'] == 'Bearer monitor-env-token'
    assert 'monitor-env-token' not in result.stdout
    assert 'monitor-env-token' not in result.stderr


def test_monitor_readiness_cli_sends_test_alert_when_ready():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--webhook-url',
                f'{server.base_url}/hook',
                '--send-test-alert',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

        posts = list(server.posts)

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload['status'] == 'ready'
    assert payload['alert_test']['status_code'] == 200
    assert posts[0]['status'] == 'test_alert'
    assert posts[0]['report']['message'] == 'Insight Engine monitor webhook test'


def test_monitor_readiness_cli_requires_webhook_for_test_alert():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--send-test-alert',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload['status'] == 'ready'
    assert payload['alert_test']['status'] == 'error'
    assert 'webhook url is required' in payload['alert_test']['message']


def test_monitor_readiness_cli_requires_webhook_when_configured():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--require-webhook',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload['status'] == 'ready'
    assert payload['alert']['status'] == 'error'
    assert 'webhook url is required' in payload['alert']['message']


def test_monitor_readiness_cli_rejects_invalid_required_webhook():
    with _Server(_ready_routes()) as server:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--base-url',
                server.base_url,
                '--require-webhook',
                '--webhook-url',
                'not-a-url',
                '--attempts',
                '1',
                '--retry-delay',
                '0',
                '--timeout',
                '1',
                '--dry-run',
            ],
            cwd=ROOT,
            env=_monitor_env(),
            text=True,
            capture_output=True,
            check=False,
        )

    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload['status'] == 'ready'
    assert payload['alert']['status'] == 'error'
    assert 'absolute http(s) URL' in payload['alert']['message']


def test_monitor_readiness_report_redacts_base_url_credentials():
    with _Server(_ready_routes()) as server:
        with_credentials = server.base_url.replace('http://', 'http://user:pass@')
        report = monitor_readiness.run_checks(with_credentials, timeout=1)

    assert report['status'] == 'ready'
    assert 'user:pass' not in report['base_url']


def test_package_json_exposes_ops_monitor_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['ops:monitor'] == (
        "sh -c 'if [ -f .env ]; then set -a; . ./.env; set +a; fi; "
        'PY=${PYTHON:-python3}; if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi; '
        '"$PY" scripts/monitor_readiness.py\''
    )
