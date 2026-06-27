"""Create, restore, or rehearse app_data volume backups."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.app_data_backup import (  # noqa: E402
    create_app_data_backup,
    restore_app_data_backup,
    verify_backup_archive,
    verify_latest_app_data_backup,
    verify_backup_round_trip,
)


def _json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _summary(payload: dict) -> dict:
    """Return a log-safe backup summary without file manifests."""
    summary = {
        'ok': payload.get('ok', True),
        'archive_path': payload.get('archive_path'),
        'file_count': payload.get('file_count') or len(payload.get('source_manifest') or {}),
        'size_bytes': payload.get('size_bytes'),
        'sha256': payload.get('sha256'),
        'manifest_present': bool(payload.get('manifest_path')),
        'pruned_count': len(payload.get('pruned_archive_paths') or []),
    }

    replica = payload.get('replica')
    if replica:
        summary['replica'] = {
            'enabled': True,
            'size_bytes': replica.get('size_bytes'),
            'sha256': replica.get('sha256'),
            'manifest_present': bool(replica.get('manifest_path')),
            'pruned_count': len(replica.get('pruned_archive_paths') or []),
        }
    elif 'replica' in payload:
        summary['replica'] = {'enabled': False}

    replica_restore = payload.get('replica_restore')
    if replica_restore is not None:
        summary['replica_restore'] = {
            'ok': replica_restore.get('ok'),
            'restored_file_count': len(replica_restore.get('restored_manifest') or {}),
        }

    if 'restored_manifest' in payload:
        summary['restored_file_count'] = len(payload.get('restored_manifest') or {})

    return summary


def _optional_int_env(name: str) -> int | None:
    raw = (os.getenv(name) or '').strip()
    if not raw:
        return None
    return int(raw)


def _replica_max_backups() -> int | None:
    replica_value = _optional_int_env('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS')
    return replica_value if replica_value is not None else _optional_int_env('MAX_BACKUPS')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)

    backup = subparsers.add_parser('backup')
    backup.add_argument('--source', default=os.getenv('APP_DATA_DIR', 'data'))
    backup.add_argument('--backup-dir', default=os.getenv('APP_DATA_BACKUP_DIR', 'data_volume_backups'))
    backup.add_argument('--max-backups', type=int, default=_optional_int_env('MAX_BACKUPS'))
    backup.add_argument('--replica-dir', default=os.getenv('APP_DATA_BACKUP_REPLICA_DIR', ''))
    backup.add_argument('--max-replica-backups', type=int, default=_replica_max_backups())
    backup.add_argument('--summary', action='store_true', help='Omit per-file manifests from stdout.')

    restore = subparsers.add_parser('restore')
    restore.add_argument('archive')
    restore.add_argument('--target', default=os.getenv('APP_DATA_DIR', 'data'))
    restore.add_argument('--overwrite', action='store_true')
    restore.add_argument(
        '--skip-verify-sidecar',
        action='store_true',
        help='Restore without verifying the sidecar manifest. Use only for trusted legacy archives.',
    )

    drill_latest = subparsers.add_parser('drill-latest')
    drill_latest.add_argument(
        '--backup-dir',
        default=os.getenv('APP_DATA_BACKUP_REPLICA_DIR') or os.getenv('APP_DATA_BACKUP_DIR', 'data_volume_backups'),
    )
    drill_latest.add_argument('--restore-dir', default='')
    drill_latest.add_argument('--summary', action='store_true', help='Omit per-file manifests from stdout.')

    rehearse = subparsers.add_parser('rehearse')
    rehearse.add_argument('--source', default=os.getenv('APP_DATA_DIR', 'data'))
    rehearse.add_argument('--backup-dir', default=os.getenv('APP_DATA_BACKUP_DIR', 'data_volume_backups'))
    rehearse.add_argument('--max-backups', type=int, default=_optional_int_env('MAX_BACKUPS'))
    rehearse.add_argument('--replica-dir', default=os.getenv('APP_DATA_BACKUP_REPLICA_DIR', ''))
    rehearse.add_argument('--max-replica-backups', type=int, default=_replica_max_backups())
    rehearse.add_argument('--summary', action='store_true', help='Omit per-file manifests from stdout.')

    args = parser.parse_args(argv)

    if args.command == 'backup':
        payload = create_app_data_backup(
            args.source,
            args.backup_dir,
            max_backups=args.max_backups,
            replica_dir=args.replica_dir or None,
            max_replica_backups=args.max_replica_backups,
        )
        _json(_summary(payload) if args.summary else payload)
        return 0

    if args.command == 'restore':
        try:
            payload = restore_app_data_backup(
                args.archive,
                args.target,
                overwrite=args.overwrite,
                verify_sidecar=not args.skip_verify_sidecar,
            )
        except Exception as exc:
            _json({'ok': False, 'error': f'{exc.__class__.__name__}: {exc}'})
            return 1
        payload['ok'] = True
        _json(payload)
        return 0

    if args.command == 'drill-latest':
        if args.restore_dir:
            payload = verify_latest_app_data_backup(args.backup_dir, args.restore_dir)
            _json(_summary(payload) if args.summary else payload)
            return 0 if payload['ok'] else 1
        with tempfile.TemporaryDirectory(prefix='app-data-latest-restore-drill-') as tmp:
            payload = verify_latest_app_data_backup(args.backup_dir, Path(tmp) / 'restore')
            _json(_summary(payload) if args.summary else payload)
            return 0 if payload['ok'] else 1

    if args.command == 'rehearse':
        with tempfile.TemporaryDirectory(prefix='app-data-backup-rehearsal-') as tmp:
            work_dir = Path(tmp)
            payload = verify_backup_round_trip(args.source, work_dir / 'round-trip')
            # Persist a real archive for operators to inspect.
            backup_payload = create_app_data_backup(
                args.source,
                args.backup_dir,
                max_backups=args.max_backups,
                replica_dir=args.replica_dir or None,
                max_replica_backups=args.max_replica_backups,
            )
            payload['archive_path'] = backup_payload['archive_path']
            payload['file_count'] = backup_payload['file_count']
            payload['size_bytes'] = backup_payload['size_bytes']
            payload['sha256'] = backup_payload['sha256']
            payload['manifest_path'] = backup_payload['manifest_path']
            payload['pruned_archive_paths'] = backup_payload['pruned_archive_paths']
            payload['replica'] = backup_payload['replica']
            if backup_payload['replica']:
                payload['replica_restore'] = verify_backup_archive(
                    backup_payload['replica']['replica_path'],
                    backup_payload['source_manifest'],
                    work_dir / 'replica-restore',
                )
            else:
                payload['replica_restore'] = None
        _json(_summary(payload) if args.summary else payload)
        replica_ok = payload['replica_restore'] is None or payload['replica_restore']['ok']
        return 0 if payload['ok'] and replica_ok else 1

    return 2


if __name__ == '__main__':
    raise SystemExit(main())
