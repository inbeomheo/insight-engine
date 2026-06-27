"""Check non-secret host prerequisites for Docker production deployments."""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYSCTL_CONFIG_PATTERNS = [
    '/usr/lib/sysctl.d/*.conf',
    '/usr/local/lib/sysctl.d/*.conf',
    '/lib/sysctl.d/*.conf',
    '/etc/sysctl.d/*.conf',
    '/etc/sysctl.conf',
]
UNSUITABLE_BACKUP_FSTYPES = {
    '',
    'aufs',
    'bpf',
    'cgroup',
    'cgroup2',
    'configfs',
    'debugfs',
    'devpts',
    'devtmpfs',
    'efivarfs',
    'fusectl',
    'hugetlbfs',
    'mqueue',
    'overlay',
    'proc',
    'pstore',
    'ramfs',
    'securityfs',
    'squashfs',
    'sysfs',
    'tmpfs',
    'tracefs',
}


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _check(status: str, name: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {'name': name, 'status': status, 'message': message}
    payload.update(extra)
    return payload


def _run(command: list[str], *, cwd: Path = ROOT, timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def docker_daemon_check() -> dict[str, Any]:
    try:
        result = _run(['docker', 'info', '--format', '{{.ServerVersion}}'])
    except Exception as exc:
        return _check('error', 'docker_daemon', f'docker daemon is unavailable: {exc.__class__.__name__}')

    version = result.stdout.strip()
    if result.returncode != 0:
        return _check('error', 'docker_daemon', 'docker daemon is unavailable')
    return _check('ok', 'docker_daemon', 'docker daemon is available', version=version)


def docker_compose_check(compose_file: Path) -> dict[str, Any]:
    try:
        result = _run(['docker', 'compose', '-f', str(compose_file), 'config', '--quiet'])
    except Exception as exc:
        return _check('error', 'docker_compose_config', f'docker compose config failed: {exc.__class__.__name__}')

    if result.returncode != 0:
        return _check('error', 'docker_compose_config', 'docker compose config is invalid')
    return _check('ok', 'docker_compose_config', 'docker compose config is valid')


def redis_overcommit_check(sysctl_path: Path, *, required: bool) -> dict[str, Any]:
    try:
        value = sysctl_path.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        status = 'error' if required else 'warning'
        return _check(status, 'redis_overcommit_memory', 'vm.overcommit_memory is unavailable on this host')
    except Exception as exc:
        status = 'error' if required else 'warning'
        return _check(status, 'redis_overcommit_memory', f'vm.overcommit_memory could not be read: {exc.__class__.__name__}')

    if value == '1':
        return _check('ok', 'redis_overcommit_memory', 'vm.overcommit_memory is set for Redis background save/AOF', value=value)

    status = 'error' if required else 'warning'
    return _check(
        status,
        'redis_overcommit_memory',
        'vm.overcommit_memory should be 1 for Redis background save/AOF reliability',
        value=value,
        expected='1',
    )


def _parse_sysctl_assignment(line: str) -> tuple[str, str] | None:
    content = line.split('#', 1)[0].strip()
    if not content:
        return None

    if '=' in content:
        key, value = content.split('=', 1)
    else:
        parts = content.split(None, 1)
        if len(parts) != 2:
            return None
        key, value = parts

    return key.strip(), value.strip()


def _expand_sysctl_config_paths(patterns: list[str] | None = None) -> list[Path]:
    resolved: list[Path] = []
    for pattern in patterns or DEFAULT_SYSCTL_CONFIG_PATTERNS:
        matches = sorted(glob.glob(pattern))
        if matches:
            resolved.extend(Path(match) for match in matches)
        else:
            resolved.append(Path(pattern))
    return resolved


def redis_overcommit_persistence_check(config_paths: list[Path], *, required: bool) -> dict[str, Any]:
    """Check that vm.overcommit_memory=1 is present in persistent sysctl config."""
    if not required:
        return _check('skipped', 'redis_overcommit_memory_persistent', 'persistent overcommit check is not required')

    assignments: list[dict[str, Any]] = []
    read_errors: list[str] = []
    for path in config_paths:
        try:
            text = path.read_text(encoding='utf-8')
        except FileNotFoundError:
            continue
        except Exception as exc:
            read_errors.append(f'{path}: {exc.__class__.__name__}')
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            assignment = _parse_sysctl_assignment(line)
            if not assignment:
                continue
            key, value = assignment
            if key == 'vm.overcommit_memory':
                assignments.append({'path': str(path), 'line': line_no, 'value': value})

    if not assignments:
        return _check(
            'error',
            'redis_overcommit_memory_persistent',
            'vm.overcommit_memory=1 must be persisted in sysctl config for production hosts',
            checked_paths=[str(path) for path in config_paths],
            read_errors=read_errors,
        )

    effective = assignments[-1]
    if effective.get('value') == '1':
        return _check(
            'ok',
            'redis_overcommit_memory_persistent',
            'vm.overcommit_memory is persisted in sysctl config',
            path=effective.get('path'),
            line=effective.get('line'),
        )

    return _check(
        'error',
        'redis_overcommit_memory_persistent',
        'persistent vm.overcommit_memory must be 1 for Redis background save/AOF reliability',
        value=effective.get('value'),
        expected='1',
        path=effective.get('path'),
        line=effective.get('line'),
    )


def _write_probe(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.insight-host-check-', dir=path, delete=False) as handle:
        handle.write(b'1')
        tmp_path = Path(handle.name)
    tmp_path.unlink(missing_ok=True)
    return True


def _volume_path_check(name: str, raw_path: str, *, required: bool) -> dict[str, Any]:
    value = (raw_path or '').strip()
    if not value:
        status = 'error' if required else 'skipped'
        return _check(status, name, f'{name.upper()} is not configured')

    path = Path(value)
    if not path.is_absolute():
        status = 'error' if required else 'warning'
        return _check(status, name, f'{name.upper()} should be an absolute host path for production backups', path=value)

    try:
        _write_probe(path)
    except Exception as exc:
        return _check('error', name, f'{name.upper()} is not writable: {exc.__class__.__name__}', path=str(path))

    return _check('ok', name, f'{name.upper()} is an absolute writable host path', path=str(path))


def _mount_info(path: Path) -> dict[str, str]:
    result = _run([
        'findmnt',
        '--json',
        '-T',
        str(path),
        '-o',
        'SOURCE,TARGET,FSTYPE,OPTIONS',
    ])
    if result.returncode != 0:
        raise RuntimeError('findmnt failed')

    payload = json.loads(result.stdout or '{}')
    filesystems = payload.get('filesystems') or []
    if not filesystems:
        raise RuntimeError('findmnt returned no filesystems')
    filesystem = filesystems[0]
    return {
        'source': str(filesystem.get('source') or ''),
        'target': str(filesystem.get('target') or ''),
        'fstype': str(filesystem.get('fstype') or ''),
        'options': str(filesystem.get('options') or ''),
    }


def _same_mount(left: dict[str, str], right: dict[str, str]) -> bool:
    if left.get('target') and left.get('target') == right.get('target'):
        return True
    return bool(left.get('source') and left.get('source') == right.get('source'))


def _backup_mount_storage_error(info: dict[str, str]) -> str | None:
    fstype = (info.get('fstype') or '').strip().lower()
    if fstype in UNSUITABLE_BACKUP_FSTYPES:
        return f'backup mounts must use durable storage, not {fstype or "unknown"}'
    source = (info.get('source') or '').strip().lower()
    if source.startswith('/dev/loop') or source == 'loop':
        return 'backup mounts must use external disk or network storage, not loopback files'
    options = {option.strip().lower() for option in (info.get('options') or '').split(',') if option.strip()}
    if 'loop' in options:
        return 'backup mounts must use external disk or network storage, not loopback files'
    if 'ro' in options:
        return 'backup mounts must be writable'
    return None


def backup_mount_checks(env: dict[str, str], *, required: bool) -> list[dict[str, Any]]:
    if not required:
        return []

    checks: list[dict[str, Any]] = []
    paths = {
        'app_data_backup_mount': ('APP_DATA_BACKUP_VOLUME', (env.get('APP_DATA_BACKUP_VOLUME') or '').strip()),
        'app_data_backup_replica_mount': (
            'APP_DATA_BACKUP_REPLICA_VOLUME',
            (env.get('APP_DATA_BACKUP_REPLICA_VOLUME') or '').strip(),
        ),
    }
    mount_info: dict[str, dict[str, str]] = {}

    try:
        app_root_mount = _mount_info(ROOT)
    except Exception as exc:
        checks.append(_check(
            'error',
            'app_root_mount',
            f'app root mount could not be checked: {exc.__class__.__name__}',
        ))
        app_root_mount = {}

    for name, (env_key, raw_path) in paths.items():
        if not raw_path:
            checks.append(_check('error', name, f'{env_key} is not configured'))
            continue

        path = Path(raw_path)
        if not path.is_absolute():
            checks.append(_check('error', name, f'{env_key} must be an absolute host path', path=raw_path))
            continue

        try:
            info = _mount_info(path)
        except Exception as exc:
            checks.append(_check('error', name, f'{env_key} mount could not be checked: {exc.__class__.__name__}', path=str(path)))
            continue

        mount_info[name] = info
        storage_error = _backup_mount_storage_error(info)
        if storage_error:
            checks.append(_check(
                'error',
                name,
                f'{env_key} {storage_error}',
                path=str(path),
                mount_target=info.get('target'),
                mount_source=info.get('source'),
                fstype=info.get('fstype'),
            ))
        elif app_root_mount and _same_mount(info, app_root_mount):
            checks.append(_check(
                'error',
                name,
                f'{env_key} must be on a filesystem mounted separately from the app workspace',
                path=str(path),
                mount_target=info.get('target'),
                mount_source=info.get('source'),
            ))
        else:
            checks.append(_check(
                'ok',
                name,
                f'{env_key} is mounted separately from the app workspace',
                path=str(path),
                mount_target=info.get('target'),
                fstype=info.get('fstype'),
            ))

    backup_info = mount_info.get('app_data_backup_mount')
    replica_info = mount_info.get('app_data_backup_replica_mount')
    if backup_info and replica_info:
        if _same_mount(backup_info, replica_info):
            checks.append(_check(
                'error',
                'app_data_backup_mount_separation',
                'backup and replica volumes must be on separate mounted filesystems',
                backup_mount=backup_info.get('target'),
                replica_mount=replica_info.get('target'),
            ))
        else:
            checks.append(_check(
                'ok',
                'app_data_backup_mount_separation',
                'backup and replica volumes are on separate mounted filesystems',
            ))

    return checks


def backup_volume_checks(env: dict[str, str], *, required: bool, require_mounts: bool = False) -> list[dict[str, Any]]:
    backup = _volume_path_check('app_data_backup_volume', env.get('APP_DATA_BACKUP_VOLUME', ''), required=required)
    replica = _volume_path_check(
        'app_data_backup_replica_volume',
        env.get('APP_DATA_BACKUP_REPLICA_VOLUME', ''),
        required=required,
    )
    checks = [backup, replica]

    backup_path = (env.get('APP_DATA_BACKUP_VOLUME') or '').strip()
    replica_path = (env.get('APP_DATA_BACKUP_REPLICA_VOLUME') or '').strip()
    if backup_path and replica_path:
        try:
            backup_resolved = Path(backup_path).resolve()
            replica_resolved = Path(replica_path).resolve()
            if backup_resolved == replica_resolved:
                checks.append(_check(
                    'error',
                    'app_data_backup_volume_separation',
                    'backup and replica volumes must be separate paths',
                    path=str(backup_resolved),
                ))
            else:
                checks.append(_check(
                    'ok',
                    'app_data_backup_volume_separation',
                    'backup and replica volumes are separate paths',
                ))
        except Exception as exc:
            checks.append(_check(
                'error',
                'app_data_backup_volume_separation',
                f'backup volume separation could not be checked: {exc.__class__.__name__}',
            ))

    checks.extend(backup_mount_checks(env, required=require_mounts))

    return checks


def run_checks(
    *,
    compose_file: Path,
    env: dict[str, str],
    require_overcommit: bool,
    require_external_backups: bool,
    sysctl_path: Path,
    require_persistent_overcommit: bool = False,
    sysctl_config_paths: list[Path] | None = None,
    require_backup_mounts: bool = False,
) -> dict[str, Any]:
    checks = [
        docker_daemon_check(),
        docker_compose_check(compose_file),
        redis_overcommit_check(sysctl_path, required=require_overcommit),
        redis_overcommit_persistence_check(
            sysctl_config_paths or _expand_sysctl_config_paths(),
            required=require_persistent_overcommit,
        ),
        *backup_volume_checks(env, required=require_external_backups, require_mounts=require_backup_mounts),
    ]
    status = 'error' if any(check['status'] == 'error' for check in checks) else 'ok'
    return {
        'service': 'insight-engine',
        'status': status,
        'checks': checks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--compose-file',
        default=os.getenv('HOST_CHECK_COMPOSE_FILE') or 'docker-compose.deploy.yml',
        help='Docker Compose deployment file to validate.',
    )
    parser.add_argument(
        '--require-overcommit',
        action='store_true',
        default=_truthy(os.getenv('HOST_CHECK_REQUIRE_OVERCOMMIT')),
        help='Fail unless vm.overcommit_memory is 1.',
    )
    parser.add_argument(
        '--require-persistent-overcommit',
        action='store_true',
        default=_truthy(os.getenv('HOST_CHECK_REQUIRE_PERSISTENT_OVERCOMMIT')),
        help='Fail unless vm.overcommit_memory=1 is present in persistent sysctl config.',
    )
    parser.add_argument(
        '--require-external-backups',
        action='store_true',
        default=_truthy(os.getenv('HOST_CHECK_REQUIRE_EXTERNAL_BACKUPS')),
        help='Fail unless backup/replica compose volume sources are absolute writable host paths.',
    )
    parser.add_argument(
        '--require-backup-mounts',
        action='store_true',
        default=_truthy(os.getenv('HOST_CHECK_REQUIRE_BACKUP_MOUNTS')),
        help='Fail unless backup/replica host paths are mounted separately from the app workspace and each other.',
    )
    parser.add_argument(
        '--sysctl-path',
        default=os.getenv('HOST_CHECK_OVERCOMMIT_PATH') or '/proc/sys/vm/overcommit_memory',
        help='Path used to read vm.overcommit_memory.',
    )
    parser.add_argument(
        '--sysctl-config-path',
        action='append',
        default=None,
        help='Persistent sysctl config path or glob to inspect. Repeatable.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = run_checks(
        compose_file=(ROOT / args.compose_file).resolve(),
        env=dict(os.environ),
        require_overcommit=args.require_overcommit,
        require_persistent_overcommit=args.require_persistent_overcommit,
        require_external_backups=args.require_external_backups,
        require_backup_mounts=args.require_backup_mounts,
        sysctl_path=Path(args.sysctl_path),
        sysctl_config_paths=_expand_sysctl_config_paths(args.sysctl_config_path),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
