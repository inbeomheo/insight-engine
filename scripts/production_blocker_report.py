"""Summarize production cutover blockers without hiding external prerequisites."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_host_prereqs, check_release_source_state, monitor_readiness  # noqa: E402
from utils.production_readiness import production_readiness_errors  # noqa: E402


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


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


def _check(status: str, name: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {'name': name, 'status': status, 'message': message}
    payload.update(extra)
    return payload


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_env_file(env: dict[str, str], env_file: Path) -> dict[str, str]:
    """Load simple KEY=VALUE lines for direct CLI use, preserving existing env values."""
    loaded = dict(env)
    if not env_file.exists():
        return loaded

    try:
        lines = env_file.read_text(encoding='utf-8').splitlines()
    except OSError:
        return loaded

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        key = key.strip()
        if not key or key in loaded:
            continue
        loaded[key] = _strip_env_value(value)
    return loaded


def _strict_production_env(env: dict[str, str]) -> dict[str, str]:
    strict = _cutover_default_env(env)
    strict['FLASK_ENV'] = 'production'
    strict['ERROR_TRACKING_REQUIRED'] = 'true'
    strict['ALERT_WEBHOOK_REQUIRED'] = 'true'
    return strict


def _git_head(root: Path = ROOT) -> str:
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def _cutover_default_env(env: dict[str, str]) -> dict[str, str]:
    """Mirror production_cutover_check.sh release metadata defaults for preflight reporting."""
    defaults = dict(env)
    git_sha = (defaults.get('GIT_SHA') or _git_head()).strip()
    defaults.setdefault('APP_VERSION', 'v2.0')
    if git_sha:
        defaults.setdefault('GIT_SHA', git_sha)
        defaults.setdefault('APP_RELEASE', git_sha)
    defaults.setdefault('BUILD_TIME', datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    return defaults


def cutover_policy_checks(env: dict[str, str]) -> list[dict[str, Any]]:
    base_url = (env.get('INSIGHT_BASE_URL') or env.get('APP_BASE_URL') or '').strip()
    checks = [
        _check(
            'ok' if (env.get('FLASK_ENV') or '').strip().lower() == 'production' else 'error',
            'flask_env_production',
            'FLASK_ENV is production' if (env.get('FLASK_ENV') or '').strip().lower() == 'production'
            else 'FLASK_ENV must be production for cutover',
        ),
        _check(
            'ok' if _truthy(env.get('ERROR_TRACKING_REQUIRED')) else 'error',
            'error_tracking_required',
            'ERROR_TRACKING_REQUIRED is enabled' if _truthy(env.get('ERROR_TRACKING_REQUIRED'))
            else 'ERROR_TRACKING_REQUIRED must be true for production cutover',
        ),
        _check(
            'ok' if _truthy(env.get('ALERT_WEBHOOK_REQUIRED')) else 'error',
            'alert_webhook_required',
            'ALERT_WEBHOOK_REQUIRED is enabled' if _truthy(env.get('ALERT_WEBHOOK_REQUIRED'))
            else 'ALERT_WEBHOOK_REQUIRED must be true for production cutover',
        ),
        _check(
            'ok' if base_url else 'error',
            'public_base_url_configured',
            'INSIGHT_BASE_URL or APP_BASE_URL is configured' if base_url
            else 'INSIGHT_BASE_URL or APP_BASE_URL is required for production cutover',
        ),
    ]
    return checks


def production_env_section(env: dict[str, str]) -> dict[str, Any]:
    policy_checks = cutover_policy_checks(env)
    errors = production_readiness_errors(_strict_production_env(env))
    checks = policy_checks + [
        _check('error', 'production_readiness', error)
        for error in errors
    ]
    if not errors:
        checks.append(_check('ok', 'production_readiness', 'production readiness environment checks passed'))
    status = 'error' if any(check['status'] == 'error' for check in checks) else 'ok'
    return {
        'name': 'production_environment',
        'status': status,
        'checks': checks,
        'error_count': sum(1 for check in checks if check['status'] == 'error'),
    }


def public_endpoint_section(env: dict[str, str], *, timeout: float, tls_min_days: int) -> dict[str, Any]:
    base_url = (env.get('INSIGHT_BASE_URL') or env.get('APP_BASE_URL') or '').strip()
    checks: list[dict[str, Any]] = []
    if not base_url:
        return {
            'name': 'public_endpoint',
            'status': 'error',
            'checks': [_check('error', 'public_endpoint', 'INSIGHT_BASE_URL or APP_BASE_URL is not configured')],
        }

    try:
        normalized = monitor_readiness.normalize_base_url(base_url)
    except ValueError as exc:
        return {
            'name': 'public_endpoint',
            'status': 'error',
            'checks': [_check('error', 'public_endpoint', str(exc))],
        }

    for check in (
        monitor_readiness.check_transport_security(normalized, require_https=True),
        monitor_readiness.check_public_host(normalized, require_public_host=True),
        monitor_readiness.check_tls_certificate(normalized, timeout, tls_min_days),
    ):
        if check:
            checks.append(_monitor_check_to_status(check))

    status = 'error' if any(check['status'] == 'error' for check in checks) else 'ok'
    return {
        'name': 'public_endpoint',
        'status': status,
        'base_url': monitor_readiness.public_base_url(normalized),
        'checks': checks,
    }


def alert_webhook_section(env: dict[str, str]) -> dict[str, Any]:
    webhook_url = (env.get('ALERT_WEBHOOK_URL') or env.get('MONITOR_WEBHOOK_URL') or '').strip()
    if not webhook_url:
        return {
            'name': 'alert_webhook',
            'status': 'error',
            'checks': [_check('error', 'alert_webhook', 'ALERT_WEBHOOK_URL or MONITOR_WEBHOOK_URL is required')],
        }

    try:
        monitor_readiness.validate_webhook_url(
            webhook_url,
            require_https=True,
            require_public_host=True,
        )
    except ValueError as exc:
        return {
            'name': 'alert_webhook',
            'status': 'error',
            'checks': [_check('error', 'alert_webhook', str(exc))],
        }

    return {
        'name': 'alert_webhook',
        'status': 'ok',
        'checks': [_check('ok', 'alert_webhook', 'alert webhook is HTTPS and public-host validated')],
    }


def source_section(root: Path) -> dict[str, Any]:
    report = check_release_source_state.run_checks(root=root, require_clean=True, require_pushed=True)
    return {
        'name': 'release_source',
        'status': report['status'],
        'checks': report['checks'],
    }


def host_section(env: dict[str, str]) -> dict[str, Any]:
    report = check_host_prereqs.run_checks(
        compose_file=(ROOT / 'docker-compose.deploy.yml').resolve(),
        env=env,
        require_overcommit=True,
        require_persistent_overcommit=True,
        require_external_backups=True,
        require_backup_mounts=True,
        sysctl_path=Path(os.getenv('HOST_CHECK_OVERCOMMIT_PATH') or '/proc/sys/vm/overcommit_memory'),
        sysctl_config_paths=check_host_prereqs._expand_sysctl_config_paths(None),
    )
    return {
        'name': 'host_prerequisites',
        'status': report['status'],
        'checks': report['checks'],
    }


def live_monitor_section(env: dict[str, str], *, timeout: float, tls_min_days: int) -> dict[str, Any]:
    base_url = (env.get('INSIGHT_BASE_URL') or env.get('APP_BASE_URL') or '').strip()
    if not base_url:
        return {
            'name': 'live_public_monitor',
            'status': 'error',
            'checks': [_check('error', 'live_public_monitor', 'INSIGHT_BASE_URL or APP_BASE_URL is not configured')],
        }

    try:
        report = monitor_readiness.run_checks(
            base_url,
            timeout=timeout,
            metrics_auth_token=(env.get('MONITOR_METRICS_AUTH_TOKEN') or env.get('METRICS_AUTH_TOKEN') or ''),
            expected_release=(env.get('APP_RELEASE') or env.get('GIT_SHA') or ''),
            expected_git_sha=(env.get('GIT_SHA') or ''),
            require_release_metadata=True,
            require_public_host=True,
            require_https=True,
            tls_min_days=tls_min_days,
        )
    except Exception as exc:
        return {
            'name': 'live_public_monitor',
            'status': 'error',
            'checks': [_check('error', 'live_public_monitor', f'{exc.__class__.__name__}: {exc}')],
        }

    return {
        'name': 'live_public_monitor',
        'status': 'ok' if report['status'] == 'ready' else 'error',
        'base_url': report.get('base_url'),
        'checks': [_monitor_check_to_status(check) for check in report.get('checks', [])],
        'release': report.get('release'),
        'duration_ms': report.get('duration_ms'),
    }


def _monitor_check_to_status(check: dict[str, Any]) -> dict[str, Any]:
    converted = dict(check)
    ok = bool(converted.pop('ok', False))
    converted['status'] = 'ok' if ok else 'error'
    converted.setdefault('message', converted.get('name', 'monitor check'))
    return converted


def _collect_blockers(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for section in sections:
        for check in section.get('checks', []):
            if check.get('status') != 'error':
                continue
            blockers.append({
                'section': section.get('name'),
                'check': check.get('name'),
                'message': check.get('message'),
            })
    return blockers


def run_report(
    *,
    env: dict[str, str],
    root: Path = ROOT,
    live_monitor: bool = False,
    timeout: float = 5.0,
    tls_min_days: int = 21,
) -> dict[str, Any]:
    sections = [
        source_section(root),
        production_env_section(env),
        host_section(env),
        public_endpoint_section(env, timeout=timeout, tls_min_days=tls_min_days),
        alert_webhook_section(env),
    ]
    if live_monitor:
        sections.append(live_monitor_section(env, timeout=timeout, tls_min_days=tls_min_days))

    blockers = _collect_blockers(sections)
    return {
        'service': 'insight-engine',
        'status': 'blocked' if blockers else 'ready',
        'sections': sections,
        'blockers': blockers,
        'blocker_count': len(blockers),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--env-file',
        default=os.getenv('PRODUCTION_STATUS_ENV_FILE') or '.env',
        help='Optional env file to load when variables are not already present.',
    )
    parser.add_argument(
        '--live-monitor',
        action='store_true',
        default=_truthy(os.getenv('PRODUCTION_STATUS_LIVE_MONITOR')),
        help='Also run live public readiness checks against INSIGHT_BASE_URL/APP_BASE_URL.',
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=_env_float('MONITOR_TIMEOUT_SECONDS', 5.0),
        help='Network timeout for DNS/TLS/live monitor checks.',
    )
    parser.add_argument(
        '--tls-min-days',
        type=int,
        default=_env_int('MONITOR_TLS_MIN_DAYS', 21),
        help='Minimum acceptable TLS certificate days remaining.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    env = load_env_file(dict(os.environ), (ROOT / args.env_file).resolve())
    report = run_report(
        env=env,
        live_monitor=args.live_monitor,
        timeout=args.timeout,
        tls_min_days=args.tls_min_days,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
