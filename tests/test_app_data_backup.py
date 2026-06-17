"""app_data volume backup and restore safeguards."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from utils.app_data_backup import (
    create_app_data_backup,
    file_manifest,
    restore_app_data_backup,
    verify_backup_round_trip,
)


ROOT = Path(__file__).resolve().parents[1]


def test_app_data_backup_round_trip_preserves_files(tmp_path):
    source = tmp_path / 'app_data'
    source.mkdir()
    (source / 'content.json').write_text('{"title":"hello"}', encoding='utf-8')
    nested = source / 'chroma_db'
    nested.mkdir()
    (nested / 'index.bin').write_bytes(b'abc123')

    result = verify_backup_round_trip(source, tmp_path / 'rehearsal')

    assert result['ok'] is True
    assert result['source_manifest'] == result['restored_manifest']
    assert result['archive_path'].endswith('.zip')


def test_app_data_backup_restore_rejects_zip_slip(tmp_path):
    archive = tmp_path / 'malicious.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('../evil.txt', 'owned')

    with pytest.raises(ValueError):
        restore_app_data_backup(archive, tmp_path / 'restore')

    assert not (tmp_path / 'evil.txt').exists()


def test_app_data_backup_script_rehearses_configured_dirs(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'external_backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'rehearse',
            '--source',
            str(source),
            '--backup-dir',
            str(backup_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['ok'] is True
    assert Path(payload['archive_path']).exists()


def test_package_json_exposes_app_data_backup_rehearsal_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:app-data-backup'] == (
        'python scripts/backup_app_data.py rehearse'
    )


def test_app_data_backup_helpers_restore_explicit_archive(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    restore_dir = tmp_path / 'restore'
    source.mkdir()
    (source / 'a.txt').write_text('A', encoding='utf-8')

    backup = create_app_data_backup(source, backup_dir)
    restore_app_data_backup(backup['archive_path'], restore_dir)

    assert file_manifest(source) == file_manifest(restore_dir)
