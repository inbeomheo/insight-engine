"""Poll deployed Insight Engine readiness endpoints and optionally alert."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = 'insight-engine-readiness-monitor/1.0'
MAX_RESPONSE_BYTES = 1_000_000
REQUEST_ID_PATTERN = re.compile(r'^[A-Za-z0-9._:-]{1,128}$')
GIT_SHA_PATTERN = re.compile(r'^[0-9a-fA-F]{7,64}$')
PLACEHOLDER_RELEASE_VALUES = {'', 'local', 'unknown', 'dev', 'development', 'test', 'none', 'null'}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or '').strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or '').strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or '').strip()
    if not raw:
        return default
    return raw.lower() in {'1', 'true', 'yes', 'on'}


def _valid_utc_build_time(value: str) -> bool:
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except ValueError:
        return False


def _tls_certificate_expires_at_epoch(host: str, port: int, timeout: float) -> float:
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls_sock:
            certificate = tls_sock.getpeercert()
    not_after = certificate.get('notAfter') if isinstance(certificate, dict) else None
    if not not_after:
        raise ValueError('TLS certificate does not include notAfter')
    return float(ssl.cert_time_to_seconds(not_after))


def _is_public_ip(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.is_global


def normalize_base_url(base_url: str) -> str:
    """Return a normalized http(s) base URL without a trailing slash."""
    normalized = (base_url or '').strip().rstrip('/')
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('base URL must be an absolute http(s) URL')
    netloc = parsed.hostname or ''
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'
    return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, '', '', ''))


def public_base_url(base_url: str) -> str:
    """Return base_url without credentials for reports and alerts."""
    parsed = urllib.parse.urlparse(base_url)
    netloc = parsed.hostname or ''
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'
    return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, '', '', ''))


def validate_webhook_url(
    webhook_url: str,
    *,
    require_https: bool = False,
    require_public_host: bool = False,
) -> str:
    """Return a normalized alert webhook URL or raise ValueError."""
    normalized = (webhook_url or '').strip()
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('webhook URL must be an absolute http(s) URL')
    if parsed.username or parsed.password:
        raise ValueError('webhook URL must not include credentials')
    if require_https and parsed.scheme != 'https':
        raise ValueError('webhook URL must use HTTPS')
    if require_public_host:
        public_host_check = check_public_host(normalized, require_public_host=True)
        if public_host_check and not public_host_check.get('ok'):
            raise ValueError(f'webhook URL host must be public: {public_host_check.get("message")}')
    return normalized


def _request(
    path: str,
    base_url: str,
    timeout: float,
    *,
    method: str = 'GET',
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    url = f'{base_url}{path}'
    request_headers = {
        'Accept': 'application/json',
        'User-Agent': USER_AGENT,
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    status_code = None
    raw_body = b''
    headers: dict[str, str] = {}
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:
            status_code = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
            raw_body = response.read(MAX_RESPONSE_BYTES)
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        headers = {key.lower(): value for key, value in exc.headers.items()}
        raw_body = exc.read(MAX_RESPONSE_BYTES)
    except Exception as exc:
        return {
            'path': path,
            'status_code': None,
            'headers': {},
            'json': None,
            'error': f'{exc.__class__.__name__}: {exc}',
        }

    parsed_json = None
    if raw_body:
        try:
            parsed_json = json.loads(raw_body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_json = None

    return {
        'path': path,
        'status_code': status_code,
        'headers': headers,
        'json': parsed_json,
        'error': None,
    }


def _failed_components(payload: dict[str, Any] | None) -> dict[str, Any]:
    components = (payload or {}).get('components')
    if not isinstance(components, dict):
        return {}
    return {
        name: component
        for name, component in components.items()
        if isinstance(component, dict) and component.get('status') == 'error'
    }


def _metrics_auth_headers(metrics_auth_token: str = '') -> dict[str, str]:
    token = (metrics_auth_token or '').strip()
    if not token:
        return {}
    return {'Authorization': f'Bearer {token}'}


def check_health(base_url: str, timeout: float) -> dict[str, Any]:
    response = _request('/health', base_url, timeout)
    payload = response.get('json')
    ok = response.get('status_code') == 200 and isinstance(payload, dict) and payload.get('status') == 'healthy'
    release = payload.get('release') if isinstance(payload, dict) and isinstance(payload.get('release'), dict) else None
    return {
        'name': 'health',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': 'healthy' if ok else 'health endpoint did not return status=healthy',
        'release': release,
        'error': response.get('error'),
    }


def check_ready(base_url: str, timeout: float, *, metrics_auth_token: str = '') -> dict[str, Any]:
    response = _request('/ready', base_url, timeout, headers=_metrics_auth_headers(metrics_auth_token))
    payload = response.get('json')
    authenticated = bool((metrics_auth_token or '').strip())
    components_present = isinstance(payload, dict) and isinstance(payload.get('components'), dict)
    ok = (
        response.get('status_code') == 200
        and isinstance(payload, dict)
        and payload.get('status') == 'ready'
        and (not authenticated or components_present)
    )
    if ok:
        message = 'ready'
    elif authenticated and not components_present:
        message = 'authenticated readiness diagnostics did not include components'
    else:
        message = 'readiness endpoint did not return status=ready'
    return {
        'name': 'ready',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': message,
        'failed_components': _failed_components(payload if isinstance(payload, dict) else None),
        'authenticated': authenticated,
        'components_present': components_present,
        'error': response.get('error'),
    }


def check_edge_auth(base_url: str, timeout: float) -> dict[str, Any]:
    response = _request('/', base_url, timeout)
    ok = response.get('status_code') == 401
    return {
        'name': 'edge_auth',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': 'edge auth challenge present' if ok else 'root route is not protected by edge auth',
        'error': response.get('error'),
    }


def check_signed_webhook_edge_route(base_url: str, timeout: float) -> dict[str, Any]:
    response = _request(
        '/api/crypto/webhook',
        base_url,
        timeout,
        method='POST',
        body=b'{"type":"charge:confirmed","data":{}}',
        headers={
            'Content-Type': 'application/json',
            'X-CC-Webhook-Signature': 'invalid-monitor-signature',
        },
    )
    headers = response.get('headers') or {}
    authenticate = (headers.get('www-authenticate') or '').lower()
    reached_backend = response.get('status_code') == 401 and isinstance(response.get('json'), dict)
    blocked_by_basic_auth = 'basic' in authenticate
    ok = reached_backend and not blocked_by_basic_auth
    return {
        'name': 'signed_webhook_edge_route',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': (
            'signed inbound webhook reaches backend signature verification'
            if ok else
            'signed inbound webhook is not routed to backend signature verification'
        ),
        'blocked_by_basic_auth': blocked_by_basic_auth,
        'error': response.get('error'),
    }


def check_security_headers(base_url: str, timeout: float) -> dict[str, Any]:
    response = _request('/health', base_url, timeout)
    headers = response.get('headers') or {}
    required = {
        'content-security-policy': "default-src 'self'",
        'x-content-type-options': 'nosniff',
        'x-frame-options': 'DENY',
        'x-xss-protection': '0',
        'referrer-policy': 'strict-origin-when-cross-origin',
        'permissions-policy': 'camera=()',
    }
    if base_url.startswith('https://'):
        required['strict-transport-security'] = 'max-age='

    missing_or_invalid = {
        name: expected
        for name, expected in required.items()
        if expected.lower() not in (headers.get(name) or '').lower()
    }
    ok = response.get('status_code') == 200 and not missing_or_invalid
    return {
        'name': 'security_headers',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': 'security headers present' if ok else 'required security headers are missing or invalid',
        'missing_or_invalid': missing_or_invalid,
        'error': response.get('error'),
    }


def check_request_id_header(base_url: str, timeout: float) -> dict[str, Any]:
    response = _request('/health', base_url, timeout)
    headers = response.get('headers') or {}
    request_id = (headers.get('x-request-id') or '').strip()
    ok = (
        response.get('status_code') == 200
        and bool(request_id)
        and bool(REQUEST_ID_PATTERN.fullmatch(request_id))
    )
    return {
        'name': 'request_id_header',
        'ok': ok,
        'status_code': response.get('status_code'),
        'message': 'request id header present' if ok else 'X-Request-ID header is missing or invalid',
        'error': response.get('error'),
    }


def check_transport_security(base_url: str, *, require_https: bool) -> dict[str, Any] | None:
    """Validate that production monitoring is pointed at the HTTPS endpoint."""
    if not require_https:
        return None

    parsed = urllib.parse.urlparse(base_url)
    ok = parsed.scheme == 'https'
    return {
        'name': 'transport_security',
        'ok': ok,
        'message': 'base URL uses HTTPS' if ok else 'base URL must use HTTPS for production monitoring',
        'scheme': parsed.scheme or 'missing',
    }


def check_public_host(base_url: str, *, require_public_host: bool) -> dict[str, Any] | None:
    """Validate that production monitoring points at a public DNS/host target."""
    if not require_public_host:
        return None

    parsed = urllib.parse.urlparse(base_url)
    host = (parsed.hostname or '').strip().lower()
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    if not host:
        return {
            'name': 'public_host',
            'ok': False,
            'message': 'base URL must include a hostname',
            'host': 'missing',
            'addresses': [],
            'error': None,
        }

    if host in {'localhost', '0.0.0.0'} or host.endswith('.local'):
        return {
            'name': 'public_host',
            'ok': False,
            'message': 'base URL host must be public, not local',
            'host': host,
            'addresses': [],
            'error': None,
        }

    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        ok = literal_ip.is_global
        return {
            'name': 'public_host',
            'ok': ok,
            'message': 'base URL host is public' if ok else 'base URL host must be a public IP address',
            'host': host,
            'addresses': [str(literal_ip)],
            'error': None,
        }

    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except Exception as exc:
        return {
            'name': 'public_host',
            'ok': False,
            'message': 'base URL host could not be resolved',
            'host': host,
            'addresses': [],
            'error': f'{exc.__class__.__name__}: {exc}',
        }

    addresses = sorted({entry[4][0] for entry in resolved if entry and entry[4]})
    if not addresses:
        return {
            'name': 'public_host',
            'ok': False,
            'message': 'base URL host did not resolve to any addresses',
            'host': host,
            'addresses': [],
            'error': None,
        }

    non_public = [address for address in addresses if not _is_public_ip(address)]
    ok = not non_public
    return {
        'name': 'public_host',
        'ok': ok,
        'message': 'base URL host resolves to public addresses' if ok else 'base URL host resolves to non-public addresses',
        'host': host,
        'addresses': addresses,
        'non_public_addresses': non_public,
        'error': None,
    }


def check_tls_certificate(base_url: str, timeout: float, min_days: int) -> dict[str, Any] | None:
    """Validate public TLS certificate expiry for HTTPS monitors."""
    if min_days <= 0:
        return None

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != 'https':
        return {
            'name': 'tls_certificate',
            'ok': False,
            'message': 'TLS certificate check requires an HTTPS base URL',
            'days_remaining': None,
            'error': None,
        }

    host = parsed.hostname or ''
    port = parsed.port or 443
    if not host:
        return {
            'name': 'tls_certificate',
            'ok': False,
            'message': 'TLS certificate check requires a hostname',
            'days_remaining': None,
            'error': None,
        }

    try:
        expires_at_epoch = _tls_certificate_expires_at_epoch(host, port, timeout)
    except Exception as exc:
        return {
            'name': 'tls_certificate',
            'ok': False,
            'message': 'TLS certificate could not be inspected',
            'days_remaining': None,
            'error': f'{exc.__class__.__name__}: {exc}',
        }

    now_epoch = datetime.now(timezone.utc).timestamp()
    seconds_remaining = expires_at_epoch - now_epoch
    days_remaining = round(seconds_remaining / 86400, 1)
    ok = days_remaining >= min_days
    return {
        'name': 'tls_certificate',
        'ok': ok,
        'message': (
            'TLS certificate expiry is within threshold'
            if ok else
            'TLS certificate expires too soon'
        ),
        'expires_at': datetime.fromtimestamp(expires_at_epoch, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'days_remaining': days_remaining,
        'min_days': min_days,
        'error': None,
    }


def check_release_metadata(
    release: dict[str, Any] | None,
    *,
    expected_release: str = '',
    expected_git_sha: str = '',
    require_release_metadata: bool = False,
) -> dict[str, Any] | None:
    """Validate deployed release metadata when requested by the operator."""
    expected_release = (expected_release or '').strip()
    expected_git_sha = (expected_git_sha or '').strip()
    if not (require_release_metadata or expected_release or expected_git_sha):
        return None

    mismatches: dict[str, str] = {}
    if not isinstance(release, dict):
        return {
            'name': 'release_metadata',
            'ok': False,
            'message': 'release metadata is missing from /health',
            'mismatches': {'release': 'missing'},
        }

    release_id = str(release.get('release') or '').strip()
    git_sha = str(release.get('gitSha') or '').strip()
    build_time = str(release.get('buildTime') or '').strip()

    if require_release_metadata:
        if release_id.lower() in PLACEHOLDER_RELEASE_VALUES:
            mismatches['release'] = 'release is local/unknown'
        if not GIT_SHA_PATTERN.fullmatch(git_sha):
            mismatches['gitSha'] = 'gitSha is not a commit SHA'
        if not _valid_utc_build_time(build_time):
            mismatches['buildTime'] = 'buildTime is not UTC YYYY-MM-DDTHH:MM:SSZ'

    if expected_release and release_id != expected_release:
        mismatches['release'] = f'expected {expected_release}, got {release_id or "missing"}'
    if expected_git_sha and git_sha != expected_git_sha:
        mismatches['gitSha'] = f'expected {expected_git_sha}, got {git_sha or "missing"}'

    ok = not mismatches
    return {
        'name': 'release_metadata',
        'ok': ok,
        'message': 'release metadata matches expected deployment' if ok else 'release metadata mismatch',
        'mismatches': mismatches,
    }


def run_checks(
    base_url: str,
    *,
    timeout: float = 5.0,
    require_edge_auth: bool = True,
    metrics_auth_token: str = '',
    expected_release: str = '',
    expected_git_sha: str = '',
    require_release_metadata: bool = False,
    require_public_host: bool = False,
    require_https: bool = False,
    tls_min_days: int = 0,
) -> dict[str, Any]:
    """Run one readiness check pass and return a non-secret report."""
    normalized_base_url = normalize_base_url(base_url)
    report_base_url = public_base_url(normalized_base_url)
    started = time.perf_counter()
    health_check = check_health(normalized_base_url, timeout)
    checks = []
    public_host_check = check_public_host(normalized_base_url, require_public_host=require_public_host)
    if public_host_check:
        checks.append(public_host_check)
    transport_check = check_transport_security(normalized_base_url, require_https=require_https)
    if transport_check:
        checks.append(transport_check)
    tls_check = check_tls_certificate(normalized_base_url, timeout, tls_min_days)
    if tls_check:
        checks.append(tls_check)
    checks.extend([
        health_check,
        check_ready(normalized_base_url, timeout, metrics_auth_token=metrics_auth_token),
        check_security_headers(normalized_base_url, timeout),
        check_request_id_header(normalized_base_url, timeout),
    ])
    release_check = check_release_metadata(
        health_check.get('release'),
        expected_release=expected_release,
        expected_git_sha=expected_git_sha,
        require_release_metadata=require_release_metadata,
    )
    if release_check:
        checks.append(release_check)
    if require_edge_auth:
        checks.append(check_edge_auth(normalized_base_url, timeout))
        checks.append(check_signed_webhook_edge_route(normalized_base_url, timeout))

    ok = all(check['ok'] for check in checks)
    return {
        'service': 'insight-engine',
        'base_url': report_base_url,
        'status': 'ready' if ok else 'not_ready',
        'checks': checks,
        'release': health_check.get('release'),
        'duration_ms': round((time.perf_counter() - started) * 1000, 1),
    }


def run_with_retries(
    base_url: str,
    *,
    attempts: int,
    retry_delay: float,
    timeout: float,
    require_edge_auth: bool,
    metrics_auth_token: str = '',
    expected_release: str = '',
    expected_git_sha: str = '',
    require_release_metadata: bool = False,
    require_public_host: bool = False,
    require_https: bool = False,
    tls_min_days: int = 0,
) -> dict[str, Any]:
    """Run readiness checks until they pass or attempts are exhausted."""
    total_attempts = max(1, attempts)
    last_report: dict[str, Any] | None = None
    for attempt in range(1, total_attempts + 1):
        report = run_checks(
            base_url,
            timeout=timeout,
            require_edge_auth=require_edge_auth,
            metrics_auth_token=metrics_auth_token,
            expected_release=expected_release,
            expected_git_sha=expected_git_sha,
            require_release_metadata=require_release_metadata,
            require_public_host=require_public_host,
            require_https=require_https,
            tls_min_days=tls_min_days,
        )
        report['attempt'] = attempt
        report['attempts'] = total_attempts
        last_report = report
        if report['status'] == 'ready':
            return report
        if attempt < total_attempts:
            time.sleep(max(0.0, retry_delay))
    return last_report or {
        'service': 'insight-engine',
        'base_url': base_url,
        'status': 'not_ready',
        'checks': [],
        'attempt': 0,
        'attempts': total_attempts,
    }


def send_webhook_alert(
    webhook_url: str,
    report: dict[str, Any],
    *,
    timeout: float = 5.0,
    require_https: bool = False,
    require_public_host: bool = False,
) -> dict[str, Any]:
    """POST a generic alert payload to Slack/Discord/n8n-compatible webhooks."""
    normalized_webhook_url = validate_webhook_url(
        webhook_url,
        require_https=require_https,
        require_public_host=require_public_host,
    )
    payload = {
        'service': report.get('service', 'insight-engine'),
        'status': report.get('status'),
        'base_url': report.get('base_url'),
        'text': f"Insight Engine readiness is {report.get('status')} for {report.get('base_url')}",
        'content': f"Insight Engine readiness is {report.get('status')} for {report.get('base_url')}",
        'report': report,
    }
    body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
    request = urllib.request.Request(
        normalized_webhook_url,
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT,
        },
    )
    with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:
        response.read(MAX_RESPONSE_BYTES)
        return {'status_code': response.status}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--base-url',
        default=os.getenv('INSIGHT_BASE_URL') or os.getenv('APP_BASE_URL') or 'http://127.0.0.1:8090',
        help='Deployed app base URL. Defaults to INSIGHT_BASE_URL, APP_BASE_URL, or local Caddy.',
    )
    parser.add_argument(
        '--attempts',
        type=int,
        default=_env_int('MONITOR_ATTEMPTS', 2),
        help='Number of check attempts before reporting failure.',
    )
    parser.add_argument(
        '--retry-delay',
        type=float,
        default=_env_float('MONITOR_RETRY_DELAY_SECONDS', 5.0),
        help='Seconds to wait between failed attempts.',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=_env_float('MONITOR_TIMEOUT_SECONDS', 5.0),
        help='HTTP timeout in seconds.',
    )
    parser.add_argument(
        '--webhook-url',
        default=os.getenv('ALERT_WEBHOOK_URL') or os.getenv('MONITOR_WEBHOOK_URL') or '',
        help='Optional alert webhook URL for not_ready reports.',
    )
    parser.add_argument(
        '--metrics-auth-token',
        default=os.getenv('MONITOR_METRICS_AUTH_TOKEN') or os.getenv('METRICS_AUTH_TOKEN') or '',
        help='Bearer token used only to request authenticated /ready diagnostics. Prefer environment variables.',
    )
    parser.add_argument(
        '--require-webhook',
        action='store_true',
        default=_env_bool('ALERT_WEBHOOK_REQUIRED') or _env_bool('MONITOR_WEBHOOK_REQUIRED'),
        help='Fail the monitor run when no valid alert webhook is configured.',
    )
    parser.add_argument(
        '--require-webhook-https',
        action='store_true',
        default=_env_bool('MONITOR_WEBHOOK_REQUIRE_HTTPS'),
        help='Fail when the alert webhook URL is not HTTPS.',
    )
    parser.add_argument(
        '--require-webhook-public-host',
        action='store_true',
        default=_env_bool('MONITOR_WEBHOOK_REQUIRE_PUBLIC_HOST'),
        help='Fail when the alert webhook host is localhost, private, or resolves to non-public addresses.',
    )
    parser.add_argument(
        '--skip-edge-auth',
        action='store_true',
        help='Skip the root-path 401 Basic Auth challenge check.',
    )
    parser.add_argument(
        '--expected-release',
        default=os.getenv('INSIGHT_EXPECTED_RELEASE') or os.getenv('EXPECTED_APP_RELEASE') or '',
        help='Expected /health release.release value for this deployment.',
    )
    parser.add_argument(
        '--expected-git-sha',
        default=os.getenv('INSIGHT_EXPECTED_GIT_SHA') or os.getenv('EXPECTED_GIT_SHA') or '',
        help='Expected /health release.gitSha value for this deployment.',
    )
    parser.add_argument(
        '--require-release-metadata',
        action='store_true',
        default=_env_bool('MONITOR_REQUIRE_RELEASE_METADATA'),
        help='Fail when /health release metadata is missing or still local/unknown.',
    )
    parser.add_argument(
        '--require-public-host',
        action='store_true',
        default=_env_bool('MONITOR_REQUIRE_PUBLIC_HOST'),
        help='Fail when the monitored base URL is localhost, private IP, or resolves to non-public addresses.',
    )
    parser.add_argument(
        '--require-https',
        action='store_true',
        default=_env_bool('MONITOR_REQUIRE_HTTPS'),
        help='Fail when the monitored base URL is not HTTPS.',
    )
    parser.add_argument(
        '--tls-min-days',
        type=int,
        default=_env_int('MONITOR_TLS_MIN_DAYS', 0),
        help='Fail when the HTTPS certificate expires in fewer than this many days. 0 disables the check.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Do not send webhook alerts; only print the JSON report.',
    )
    parser.add_argument(
        '--send-test-alert',
        action='store_true',
        help='Send a webhook test message even when readiness checks pass.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = run_with_retries(
        args.base_url,
        attempts=args.attempts,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
        require_edge_auth=not args.skip_edge_auth,
        metrics_auth_token=args.metrics_auth_token,
        expected_release=args.expected_release,
        expected_git_sha=args.expected_git_sha,
        require_release_metadata=(
            args.require_release_metadata
            or bool(args.expected_release)
            or bool(args.expected_git_sha)
        ),
        require_public_host=args.require_public_host,
        require_https=args.require_https,
        tls_min_days=args.tls_min_days,
    )

    alert_test_failed = False
    alert_config_failed = False
    if args.require_webhook:
        if not args.webhook_url:
            report['alert'] = {'status': 'error', 'message': 'webhook url is required'}
            alert_config_failed = True
        else:
            try:
                validate_webhook_url(
                    args.webhook_url,
                    require_https=args.require_webhook_https,
                    require_public_host=args.require_webhook_public_host,
                )
            except ValueError as exc:
                report['alert'] = {'status': 'error', 'message': str(exc)}
                alert_config_failed = True

    if args.send_test_alert:
        if args.dry_run:
            report['alert_test'] = {'status': 'skipped', 'message': 'dry-run enabled'}
        elif not args.webhook_url:
            report['alert_test'] = {'status': 'error', 'message': 'webhook url is required'}
            alert_test_failed = True
        else:
            try:
                test_report = {
                    **report,
                    'status': 'test_alert',
                    'message': 'Insight Engine monitor webhook test',
                }
                report['alert_test'] = send_webhook_alert(
                    args.webhook_url,
                    test_report,
                    timeout=args.timeout,
                    require_https=args.require_webhook_https,
                    require_public_host=args.require_webhook_public_host,
                )
            except Exception as exc:
                report['alert_test'] = {'status': 'error', 'message': f'{exc.__class__.__name__}: {exc}'}
                alert_test_failed = True

    if report['status'] != 'ready' and args.webhook_url and not args.dry_run and not args.send_test_alert:
        try:
            report['alert'] = send_webhook_alert(
                args.webhook_url,
                report,
                timeout=args.timeout,
                require_https=args.require_webhook_https,
                require_public_host=args.require_webhook_public_host,
            )
        except Exception as exc:
            report['alert'] = {'error': f'{exc.__class__.__name__}: {exc}'}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'ready' and not alert_test_failed and not alert_config_failed else 2


if __name__ == '__main__':
    raise SystemExit(main())
