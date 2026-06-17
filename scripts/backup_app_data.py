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
    verify_backup_round_trip,
)


def _json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)

    backup = subparsers.add_parser('backup')
    backup.add_argument('--source', default=os.getenv('APP_DATA_DIR', 'data'))
    backup.add_argument('--backup-dir', default=os.getenv('APP_DATA_BACKUP_DIR', 'data_volume_backups'))

    restore = subparsers.add_parser('restore')
    restore.add_argument('archive')
    restore.add_argument('--target', default=os.getenv('APP_DATA_DIR', 'data'))
    restore.add_argument('--overwrite', action='store_true')

    rehearse = subparsers.add_parser('rehearse')
    rehearse.add_argument('--source', default=os.getenv('APP_DATA_DIR', 'data'))
    rehearse.add_argument('--backup-dir', default=os.getenv('APP_DATA_BACKUP_DIR', 'data_volume_backups'))

    args = parser.parse_args(argv)

    if args.command == 'backup':
        _json(create_app_data_backup(args.source, args.backup_dir))
        return 0

    if args.command == 'restore':
        _json(restore_app_data_backup(args.archive, args.target, overwrite=args.overwrite))
        return 0

    if args.command == 'rehearse':
        with tempfile.TemporaryDirectory(prefix='app-data-backup-rehearsal-') as tmp:
            payload = verify_backup_round_trip(args.source, Path(tmp))
        # Persist a real archive for operators to inspect.
        backup_payload = create_app_data_backup(args.source, args.backup_dir)
        payload['archive_path'] = backup_payload['archive_path']
        _json(payload)
        return 0 if payload['ok'] else 1

    return 2


if __name__ == '__main__':
    raise SystemExit(main())
