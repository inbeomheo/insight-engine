"""app_data volume backup and restore safeguards."""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from utils.app_data_backup import (
    backup_manifest_path,
    create_app_data_backup,
    file_manifest,
    latest_app_data_backup,
    load_backup_sidecar_manifest,
    restore_app_data_backup,
    verify_backup_archive,
    verify_backup_archive_with_sidecar,
    verify_latest_app_data_backup,
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
    env = os.environ.copy()
    env.pop('APP_DATA_BACKUP_REPLICA_DIR', None)
    env.pop('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS', None)

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
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['ok'] is True
    assert Path(payload['archive_path']).exists()
    assert payload['replica_restore'] is None


def test_app_data_backup_script_summary_omits_file_manifests(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
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
            '--replica-dir',
            str(replica_dir),
            '--summary',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload['ok'] is True
    assert payload['file_count'] == 1
    assert payload['size_bytes'] > 0
    assert payload['sha256']
    assert payload['manifest_present'] is True
    assert payload['replica']['enabled'] is True
    assert payload['replica_restore']['ok'] is True
    assert 'source_manifest' not in payload
    assert 'restored_manifest' not in payload


def test_app_data_backup_prunes_old_archives_when_max_backups_set(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    backup_dir.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    old_archives = []
    for index in range(3):
        archive = backup_dir / f'app_data_backup_20200101_00000{index}_000000.zip'
        archive.write_bytes(b'old')
        backup_manifest_path(archive).write_text('{}', encoding='utf-8')
        os.utime(archive, (index + 1, index + 1))
        old_archives.append(archive)

    payload = create_app_data_backup(source, backup_dir, max_backups=2)
    remaining = sorted(backup_dir.glob('app_data_backup_*.zip'))

    assert Path(payload['archive_path']).exists()
    assert len(remaining) == 2
    assert old_archives[0].exists() is False
    assert backup_manifest_path(old_archives[0]).exists() is False
    assert len(payload['pruned_archive_paths']) == 2


def test_app_data_backup_writes_sidecar_manifest_and_reports_latest_metadata(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    payload = create_app_data_backup(source, backup_dir)
    sidecar = load_backup_sidecar_manifest(payload['archive_path'])
    latest = latest_app_data_backup(backup_dir)

    assert Path(payload['manifest_path']).exists()
    assert sidecar['archive'] == Path(payload['archive_path']).name
    assert sidecar['sha256'] == payload['sha256']
    assert sidecar['source_manifest'] == payload['source_manifest']
    assert latest['archive'] == Path(payload['archive_path']).name
    assert latest['age_seconds'] >= 0
    assert latest['size_bytes'] > 0
    assert latest['is_zipfile'] is True
    assert latest['manifest_present'] is True
    assert latest['manifest_valid'] is True


def test_app_data_backup_replicates_archive_to_second_location(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    payload = create_app_data_backup(source, backup_dir, replica_dir=replica_dir)

    replica = payload['replica']
    assert replica is not None
    assert Path(replica['replica_path']).exists()
    assert Path(replica['manifest_path']).exists()
    assert Path(replica['replica_path']).read_bytes() == Path(payload['archive_path']).read_bytes()
    assert replica['sha256']
    assert replica['manifest_present'] is True


def test_app_data_backup_verifies_replica_archive_restore_with_sidecar(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    payload = create_app_data_backup(source, backup_dir, replica_dir=replica_dir)
    restore = verify_backup_archive(
        payload['replica']['replica_path'],
        payload['source_manifest'],
        tmp_path / 'replica_restore',
    )

    assert restore['ok'] is True
    assert restore['source_manifest'] == restore['restored_manifest']
    sidecar_restore = verify_backup_archive_with_sidecar(
        payload['replica']['replica_path'],
        tmp_path / 'replica_sidecar_restore',
    )

    assert sidecar_restore['ok'] is True
    assert sidecar_restore['sha256_ok'] is True
    assert sidecar_restore['restored_ok'] is True


def test_app_data_backup_prunes_replica_archives(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
    source.mkdir()
    replica_dir.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    old_archive = replica_dir / 'app_data_backup_20200101_000000_000000.zip'
    old_archive.write_bytes(b'old')
    backup_manifest_path(old_archive).write_text('{}', encoding='utf-8')
    os.utime(old_archive, (1, 1))

    payload = create_app_data_backup(
        source,
        backup_dir,
        replica_dir=replica_dir,
        max_replica_backups=1,
    )

    assert old_archive.exists() is False
    assert backup_manifest_path(old_archive).exists() is False
    assert len(list(replica_dir.glob('app_data_backup_*.zip'))) == 1
    assert len(payload['replica']['pruned_archive_paths']) == 1


def test_app_data_backup_script_applies_max_backups(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    backup_dir.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    old_archive = backup_dir / 'app_data_backup_20200101_000000_000000.zip'
    old_archive.write_bytes(b'old')
    os.utime(old_archive, (1, 1))

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'backup',
            '--source',
            str(source),
            '--backup-dir',
            str(backup_dir),
            '--max-backups',
            '1',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert Path(payload['archive_path']).exists()
    assert old_archive.exists() is False
    assert len(list(backup_dir.glob('app_data_backup_*.zip'))) == 1


def test_app_data_backup_script_replicates_archive(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'backup',
            '--source',
            str(source),
            '--backup-dir',
            str(backup_dir),
            '--replica-dir',
            str(replica_dir),
            '--max-replica-backups',
            '1',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert Path(payload['replica']['replica_path']).exists()
    assert Path(payload['replica']['manifest_path']).exists()
    assert Path(payload['replica']['replica_path']).read_bytes() == Path(payload['archive_path']).read_bytes()


def test_app_data_backup_script_rehearses_replica_restore(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
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
            '--replica-dir',
            str(replica_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload['ok'] is True
    assert payload['replica_restore']['ok'] is True
    assert payload['replica_restore']['source_manifest'] == payload['replica_restore']['restored_manifest']


def test_app_data_backup_script_drills_latest_replica_with_sidecar(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    replica_dir = tmp_path / 'replica'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    create_app_data_backup(source, backup_dir, replica_dir=replica_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'drill-latest',
            '--backup-dir',
            str(replica_dir),
            '--summary',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload['ok'] is True
    assert payload['file_count'] == 1
    assert payload['restored_file_count'] == 1
    assert 'source_manifest' not in payload
    assert 'restored_manifest' not in payload


def test_app_data_backup_latest_drill_reports_missing_sidecar(tmp_path):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    archive = backup_dir / 'app_data_backup_20200101_000000_000000.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('sample.txt', 'sample')

    result = verify_latest_app_data_backup(backup_dir, tmp_path / 'restore')

    assert result['ok'] is False
    assert 'manifest' in result['error']


def test_package_json_exposes_app_data_backup_rehearsal_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:app-data-backup'] == (
        "sh -c 'if [ -f .env ]; then set -a; . ./.env; set +a; fi; python3 scripts/backup_app_data.py rehearse --summary'"
    )
    assert package_json['scripts']['ops:restore-drill'] == (
        "sh -c 'if [ -f .env ]; then set -a; . ./.env; set +a; fi; python3 scripts/backup_app_data.py drill-latest --summary'"
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


def test_app_data_backup_script_restore_verifies_sidecar_by_default(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    restore_dir = tmp_path / 'restore'
    source.mkdir()
    (source / 'a.txt').write_text('A', encoding='utf-8')
    backup = create_app_data_backup(source, backup_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'restore',
            backup['archive_path'],
            '--target',
            str(restore_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload['ok'] is True
    assert payload['sidecar_verified'] is True
    assert file_manifest(source) == file_manifest(restore_dir)


def test_app_data_backup_script_restore_rejects_archive_without_sidecar(tmp_path):
    archive = tmp_path / 'legacy.zip'
    restore_dir = tmp_path / 'restore'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('sample.txt', 'sample')

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'restore',
            str(archive),
            '--target',
            str(restore_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload['ok'] is False
    assert 'sidecar' in payload['error']
    assert not (restore_dir / 'sample.txt').exists()


def test_app_data_backup_script_restore_rejects_tampered_archive_before_writing(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    restore_dir = tmp_path / 'restore'
    source.mkdir()
    (source / 'a.txt').write_text('A', encoding='utf-8')
    backup = create_app_data_backup(source, backup_dir)
    with zipfile.ZipFile(backup['archive_path'], 'a') as zf:
        zf.writestr('tampered.txt', 'changed')

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'scripts' / 'backup_app_data.py'),
            'restore',
            backup['archive_path'],
            '--target',
            str(restore_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload['ok'] is False
    assert 'sidecar' in payload['error']
    assert file_manifest(restore_dir) == {}
