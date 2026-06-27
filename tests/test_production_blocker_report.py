"""Production blocker report contract."""
import json

from scripts import production_blocker_report


def _source_report(status='ok'):
    return {
        'status': status,
        'checks': [
            {'name': 'git_worktree_clean', 'status': status, 'message': 'Git worktree is clean'},
        ],
    }


def _host_report(status='ok'):
    checks = [
        {'name': 'redis_overcommit_memory', 'status': 'ok', 'message': 'vm.overcommit_memory is set'},
    ]
    if status == 'error':
        checks.append({
            'name': 'app_data_backup_mount',
            'status': 'error',
            'message': 'APP_DATA_BACKUP_VOLUME is not configured',
        })
    return {'status': status, 'checks': checks}


def test_production_blocker_report_summarizes_missing_cutover_requirements(monkeypatch):
    monkeypatch.setattr(
        production_blocker_report.check_release_source_state,
        'run_checks',
        lambda **_kwargs: _source_report(),
    )
    monkeypatch.setattr(
        production_blocker_report.check_host_prereqs,
        'run_checks',
        lambda **_kwargs: _host_report(status='error'),
    )

    report = production_blocker_report.run_report(env={'FLASK_ENV': 'production'})

    messages = [blocker['message'] for blocker in report['blockers']]
    assert report['status'] == 'blocked'
    assert any('ERROR_TRACKING_REQUIRED' in message for message in messages)
    assert any('ALERT_WEBHOOK_REQUIRED' in message for message in messages)
    assert any('INSIGHT_BASE_URL or APP_BASE_URL' in message for message in messages)
    assert any('APP_DATA_BACKUP_VOLUME' in message for message in messages)


def test_production_blocker_report_is_ready_when_strict_sections_pass(monkeypatch):
    env = {
        'FLASK_ENV': 'production',
        'ERROR_TRACKING_REQUIRED': 'true',
        'ALERT_WEBHOOK_REQUIRED': 'true',
        'INSIGHT_BASE_URL': 'https://insight.example.com',
        'ALERT_WEBHOOK_URL': 'https://hooks.example.com/insight',
    }
    monkeypatch.setattr(
        production_blocker_report.check_release_source_state,
        'run_checks',
        lambda **_kwargs: _source_report(),
    )
    monkeypatch.setattr(
        production_blocker_report.check_host_prereqs,
        'run_checks',
        lambda **_kwargs: _host_report(),
    )
    monkeypatch.setattr(
        production_blocker_report,
        'production_readiness_errors',
        lambda _env: [],
    )
    monkeypatch.setattr(
        production_blocker_report.monitor_readiness,
        'check_public_host',
        lambda *_args, **_kwargs: {'name': 'public_host', 'ok': True, 'message': 'public'},
    )
    monkeypatch.setattr(
        production_blocker_report.monitor_readiness,
        'check_tls_certificate',
        lambda *_args, **_kwargs: {'name': 'tls_certificate', 'ok': True, 'message': 'tls ok'},
    )
    monkeypatch.setattr(
        production_blocker_report.monitor_readiness,
        'validate_webhook_url',
        lambda *_args, **_kwargs: 'https://hooks.example.com/insight',
    )

    report = production_blocker_report.run_report(env=env)

    assert report['status'] == 'ready'
    assert report['blocker_count'] == 0
    assert {section['name'] for section in report['sections']} == {
        'release_source',
        'production_environment',
        'host_prerequisites',
        'public_endpoint',
        'alert_webhook',
    }


def test_package_json_exposes_production_status_script():
    package_json = json.loads((production_blocker_report.ROOT / 'package.json').read_text(encoding='utf-8'))

    assert 'scripts/production_blocker_report.py' in package_json['scripts']['ops:production-status']
