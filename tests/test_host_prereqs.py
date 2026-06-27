"""Host prerequisite checks for Docker production deployments."""
import json
from pathlib import Path
from unittest.mock import patch

from scripts import check_host_prereqs


def _completed(returncode=0, stdout='ok\n'):
    class Completed:
        def __init__(self):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ''
    return Completed()


def _findmnt_completed(source, target, fstype='ext4', options='rw,relatime'):
    return _completed(stdout=json.dumps({
        'filesystems': [
            {'source': source, 'target': target, 'fstype': fstype, 'options': options},
        ],
    }))


def test_host_prereqs_warns_for_overcommit_without_strict_requirement(tmp_path):
    sysctl = tmp_path / 'overcommit_memory'
    sysctl.write_text('0\n', encoding='utf-8')

    with patch.object(check_host_prereqs, '_run', return_value=_completed()):
        report = check_host_prereqs.run_checks(
            compose_file=Path('docker-compose.deploy.yml'),
            env={},
            require_overcommit=False,
            require_external_backups=False,
            sysctl_path=sysctl,
        )

    overcommit = next(check for check in report['checks'] if check['name'] == 'redis_overcommit_memory')
    assert report['status'] == 'ok'
    assert overcommit['status'] == 'warning'


def test_host_prereqs_can_require_overcommit(tmp_path):
    sysctl = tmp_path / 'overcommit_memory'
    sysctl.write_text('0\n', encoding='utf-8')

    with patch.object(check_host_prereqs, '_run', return_value=_completed()):
        report = check_host_prereqs.run_checks(
            compose_file=Path('docker-compose.deploy.yml'),
            env={},
            require_overcommit=True,
            require_external_backups=False,
            sysctl_path=sysctl,
        )

    overcommit = next(check for check in report['checks'] if check['name'] == 'redis_overcommit_memory')
    assert report['status'] == 'error'
    assert overcommit['status'] == 'error'


def test_host_prereqs_accepts_persistent_overcommit_config(tmp_path):
    conf = tmp_path / '99-insight-engine.conf'
    conf.write_text('# comment\nvm.overcommit_memory = 1\n', encoding='utf-8')

    check = check_host_prereqs.redis_overcommit_persistence_check([conf], required=True)

    assert check['status'] == 'ok'
    assert check['name'] == 'redis_overcommit_memory_persistent'
    assert check['path'] == str(conf)


def test_host_prereqs_rejects_missing_persistent_overcommit_config(tmp_path):
    check = check_host_prereqs.redis_overcommit_persistence_check([tmp_path / 'missing.conf'], required=True)

    assert check['status'] == 'error'
    assert 'persisted' in check['message']


def test_host_prereqs_rejects_persistent_overcommit_zero(tmp_path):
    conf = tmp_path / '99-insight-engine.conf'
    conf.write_text('vm.overcommit_memory = 0\n', encoding='utf-8')

    check = check_host_prereqs.redis_overcommit_persistence_check([conf], required=True)

    assert check['status'] == 'error'
    assert check['value'] == '0'


def test_host_prereqs_accepts_external_backup_paths(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'

    with patch.object(check_host_prereqs, '_run', return_value=_completed()):
        report = check_host_prereqs.run_checks(
            compose_file=Path('docker-compose.deploy.yml'),
            env={
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            require_overcommit=False,
            require_external_backups=True,
            sysctl_path=tmp_path / 'missing',
        )

    assert report['status'] == 'ok'
    assert backup.is_dir()
    assert replica.is_dir()
    assert any(check['name'] == 'app_data_backup_volume_separation' for check in report['checks'])


def test_host_prereqs_rejects_named_backup_volumes_when_external_required(tmp_path):
    with patch.object(check_host_prereqs, '_run', return_value=_completed()):
        report = check_host_prereqs.run_checks(
            compose_file=Path('docker-compose.deploy.yml'),
            env={
                'APP_DATA_BACKUP_VOLUME': 'insight_app_backups',
                'APP_DATA_BACKUP_REPLICA_VOLUME': 'insight_app_backup_replica',
            },
            require_overcommit=False,
            require_external_backups=True,
            sysctl_path=tmp_path / 'missing',
        )

    assert report['status'] == 'error'
    assert any(check['status'] == 'error' for check in report['checks'])


def test_host_prereqs_accepts_backup_and_replica_on_separate_mounts(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    backup.mkdir()
    replica.mkdir()

    def fake_run(command, **_kwargs):
        if command[0] == 'findmnt':
            path = command[3]
            if path == str(check_host_prereqs.ROOT):
                return _findmnt_completed('/dev/root', '/')
            if path == str(backup):
                return _findmnt_completed('/dev/backup-disk', str(backup))
            if path == str(replica):
                return _findmnt_completed('/dev/replica-disk', str(replica))
        return _completed()

    with patch.object(check_host_prereqs, '_run', side_effect=fake_run):
        checks = check_host_prereqs.backup_mount_checks(
            {
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            required=True,
        )

    assert all(check['status'] == 'ok' for check in checks)
    assert any(check['name'] == 'app_data_backup_mount_separation' for check in checks)


def test_host_prereqs_rejects_backup_mounts_on_app_filesystem(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    backup.mkdir()
    replica.mkdir()

    with patch.object(
        check_host_prereqs,
        '_run',
        return_value=_findmnt_completed('/dev/root', '/'),
    ):
        checks = check_host_prereqs.backup_mount_checks(
            {
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            required=True,
        )

    assert any(check['status'] == 'error' for check in checks)
    assert any(
        check['name'] in {'app_data_backup_mount', 'app_data_backup_replica_mount'}
        and 'app workspace' in check['message']
        for check in checks
    )
    assert any(check['name'] == 'app_data_backup_mount_separation' for check in checks)


def test_host_prereqs_rejects_ephemeral_backup_mounts(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    backup.mkdir()
    replica.mkdir()

    def fake_run(command, **_kwargs):
        if command[0] == 'findmnt':
            path = command[3]
            if path == str(check_host_prereqs.ROOT):
                return _findmnt_completed('/dev/root', '/')
            if path == str(backup):
                return _findmnt_completed('tmpfs', str(backup), fstype='tmpfs')
            if path == str(replica):
                return _findmnt_completed('overlay', str(replica), fstype='overlay')
        return _completed()

    with patch.object(check_host_prereqs, '_run', side_effect=fake_run):
        checks = check_host_prereqs.backup_mount_checks(
            {
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            required=True,
        )

    storage_checks = [
        check for check in checks
        if check['name'] in {'app_data_backup_mount', 'app_data_backup_replica_mount'}
    ]
    assert all(check['status'] == 'error' for check in storage_checks)
    assert any(check.get('fstype') == 'tmpfs' for check in storage_checks)
    assert any(check.get('fstype') == 'overlay' for check in storage_checks)


def test_host_prereqs_rejects_loopback_backup_mounts(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    backup.mkdir()
    replica.mkdir()

    def fake_run(command, **_kwargs):
        if command[0] == 'findmnt':
            path = command[3]
            if path == str(check_host_prereqs.ROOT):
                return _findmnt_completed('/dev/root', '/')
            if path == str(backup):
                return _findmnt_completed('/dev/loop3', str(backup), fstype='ext4')
            if path == str(replica):
                return _findmnt_completed('/dev/replica-disk', str(replica), fstype='ext4', options='rw,loop')
        return _completed()

    with patch.object(check_host_prereqs, '_run', side_effect=fake_run):
        checks = check_host_prereqs.backup_mount_checks(
            {
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            required=True,
        )

    storage_checks = [
        check for check in checks
        if check['name'] in {'app_data_backup_mount', 'app_data_backup_replica_mount'}
    ]
    assert all(check['status'] == 'error' for check in storage_checks)
    assert all('loopback' in check['message'] for check in storage_checks)


def test_host_prereqs_rejects_system_backup_mounts(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    backup.mkdir()
    replica.mkdir()

    def fake_run(command, **_kwargs):
        if command[0] == 'findmnt':
            path = command[3]
            if path == str(check_host_prereqs.ROOT):
                return _findmnt_completed('/dev/root', '/')
            if path == str(backup):
                return _findmnt_completed('/dev/nvme0n1p2', '/boot', fstype='ext4')
            if path == str(replica):
                return _findmnt_completed('/dev/nvme0n1p1', '/boot/efi', fstype='vfat')
        return _completed()

    with patch.object(check_host_prereqs, '_run', side_effect=fake_run):
        checks = check_host_prereqs.backup_mount_checks(
            {
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            required=True,
        )

    storage_checks = [
        check for check in checks
        if check['name'] in {'app_data_backup_mount', 'app_data_backup_replica_mount'}
    ]
    assert all(check['status'] == 'error' for check in storage_checks)
    assert all('system mount' in check['message'] for check in storage_checks)


def test_host_prereqs_can_require_backup_mounts_in_full_report(tmp_path):
    backup = tmp_path / 'backups'
    replica = tmp_path / 'replica'
    sysctl = tmp_path / 'overcommit_memory'
    sysctl_conf = tmp_path / '99-insight-engine.conf'
    backup.mkdir()
    replica.mkdir()
    sysctl.write_text('1\n', encoding='utf-8')
    sysctl_conf.write_text('vm.overcommit_memory = 1\n', encoding='utf-8')

    def fake_run(command, **_kwargs):
        if command[0] == 'findmnt':
            path = command[3]
            if path == str(check_host_prereqs.ROOT):
                return _findmnt_completed('/dev/root', '/')
            if path == str(backup):
                return _findmnt_completed('/dev/backup-disk', str(backup))
            if path == str(replica):
                return _findmnt_completed('/dev/replica-disk', str(replica))
        return _completed(stdout='28.0.0\n')

    with patch.object(check_host_prereqs, '_run', side_effect=fake_run):
        report = check_host_prereqs.run_checks(
            compose_file=Path('docker-compose.deploy.yml'),
            env={
                'APP_DATA_BACKUP_VOLUME': str(backup),
                'APP_DATA_BACKUP_REPLICA_VOLUME': str(replica),
            },
            require_overcommit=True,
            require_persistent_overcommit=True,
            require_external_backups=True,
            require_backup_mounts=True,
            sysctl_path=sysctl,
            sysctl_config_paths=[sysctl_conf],
        )

    assert report['status'] == 'ok'
    assert any(check['name'] == 'app_data_backup_mount_separation' for check in report['checks'])
    assert any(check['name'] == 'redis_overcommit_memory_persistent' for check in report['checks'])


def test_host_prereqs_docker_checks_use_non_secret_commands():
    with patch.object(check_host_prereqs, '_run', return_value=_completed(stdout='28.0.0\n')) as run:
        docker = check_host_prereqs.docker_daemon_check()

    assert docker['status'] == 'ok'
    assert run.call_args.args[0] == ['docker', 'info', '--format', '{{.ServerVersion}}']


def test_host_prereqs_package_script_is_exposed():
    package_json = (check_host_prereqs.ROOT / 'package.json').read_text(encoding='utf-8')

    assert (
        '"ops:host-check": "sh -c \'if [ -f .env ]; then set -a; . ./.env; set +a; fi; '
        'PY=${PYTHON:-python3}; if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi; '
        '\\"$PY\\" scripts/check_host_prereqs.py\'"'
    ) in package_json
