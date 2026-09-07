"""app_data volume backup and restore safeguards."""
import hashlib
import fcntl
import json
import importlib.util
import os
import signal
import sqlite3
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from utils.app_data_backup import (
    BACKUP_MANIFEST_MEMBER,
    STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS,
    cleanup_stale_backup_artifacts,
    create_and_prune_app_data_backup,
    create_app_data_backup,
    file_manifest,
    prune_app_data_backups,
    recover_interrupted_restore,
    restore_app_data_backup,
    verify_app_data_backup,
    verify_and_finalize_app_data_backup,
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


def test_app_data_backup_does_not_follow_external_symlinks(tmp_path):
    source = tmp_path / 'data'
    external = tmp_path / 'external'
    source.mkdir()
    external.mkdir()
    (source / 'safe.txt').write_text('safe', encoding='utf-8')
    (external / 'secret.txt').write_text('secret', encoding='utf-8')
    (source / 'linked-file').symlink_to(external / 'secret.txt')
    (source / 'linked-dir').symlink_to(external, target_is_directory=True)

    payload = create_app_data_backup(source, tmp_path / 'backups')

    assert payload['source_manifest'] == {'safe.txt': file_manifest(source)['safe.txt']}
    with zipfile.ZipFile(payload['archive_path']) as archive:
        assert archive.namelist() == ['safe.txt', BACKUP_MANIFEST_MEMBER]


def test_app_data_backup_embeds_and_validates_file_manifest(tmp_path):
    source = tmp_path / 'data'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    payload = create_app_data_backup(source, tmp_path / 'backups')
    restored = restore_app_data_backup(payload['archive_path'], tmp_path / 'restore')

    assert restored['manifest_source'] == 'embedded'
    assert restored['restored_manifest'] == payload['source_manifest']
    with zipfile.ZipFile(payload['archive_path']) as archive:
        manifest = json.loads(archive.read(BACKUP_MANIFEST_MEMBER))
    assert manifest == {
        'algorithm': 'sha256',
        'files': payload['source_manifest'],
        'version': 1,
    }


def test_empty_backup_with_embedded_manifest_restores_safely(tmp_path):
    source = tmp_path / 'empty-source'
    source.mkdir()

    payload = create_app_data_backup(source, tmp_path / 'backups')
    restored = restore_app_data_backup(payload['archive_path'], tmp_path / 'restore')

    assert restored['manifest_source'] == 'embedded'
    assert restored['restored_manifest'] == {}


@pytest.mark.parametrize('with_file', [False, True])
def test_manifestless_archive_never_overwrites_existing_target(tmp_path, with_file):
    archive = tmp_path / 'legacy.zip'
    target = tmp_path / 'data'
    target.mkdir()
    (target / 'old.txt').write_text('old', encoding='utf-8')
    original_manifest = file_manifest(target)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        if with_file:
            zf.writestr('new.txt', b'new')

    with pytest.raises(ValueError, match='missing the embedded manifest'):
        restore_app_data_backup(archive, target, overwrite=True)

    assert file_manifest(target) == original_manifest
    assert not list(tmp_path.glob('.data.restore-*'))


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


def test_rehearsal_verifies_the_exact_persisted_archive(monkeypatch, tmp_path, capsys):
    module = _load_backup_script()
    archive = tmp_path / 'backups' / 'app_data_backup_exact.zip'
    archive.parent.mkdir()
    archive.write_bytes(b'archive')
    manifest = {'sample.txt': 'a' * 64}
    verified_paths = []

    monkeypatch.setattr(
        module,
        'create_app_data_backup',
        lambda *_args, **_kwargs: {
            'archive_path': str(archive),
            'file_count': 1,
            'source_manifest': manifest,
            'size_bytes': archive.stat().st_size,
        },
    )

    def verify(path, *, expected_manifest):
        verified_paths.append(Path(path).resolve())
        assert expected_manifest == manifest
        return {
            'ok': True,
            'restored_file_count': 1,
            'restored_manifest': manifest,
            'sqlite_databases_checked': [],
            'manifest_source': 'embedded',
        }

    monkeypatch.setattr(module, 'verify_app_data_backup', verify)

    result = module.main([
        'rehearse',
        '--source', str(tmp_path / 'source'),
        '--backup-dir', str(archive.parent),
    ])

    assert result == 0
    assert verified_paths == [archive.resolve()]
    assert Path(json.loads(capsys.readouterr().out)['archive_path']) == archive.resolve()


def test_package_json_exposes_app_data_backup_rehearsal_script():
    package_json = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    assert package_json['scripts']['verify:app-data-backup'] == (
        'node scripts/run_python.cjs scripts/backup_app_data.py rehearse'
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


def test_restore_validates_before_atomically_replacing_existing_target(tmp_path):
    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')

    result = restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not (target / 'old.txt').exists()
    assert result['previous_target_cleanup_pending'] is None


def test_restore_commits_through_atomic_exchange_when_supported(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    exchanges = []

    def emulate_exchange(staging, live_target):
        old_tree = staging.parent / 'emulated-old-tree'
        os.replace(live_target, old_tree)
        os.replace(staging, live_target)
        os.replace(old_tree, staging)
        exchanges.append((staging, live_target))
        return True

    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', emulate_exchange)

    result = restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    assert len(exchanges) == 1
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not (target / 'old.txt').exists()
    assert result['previous_target_cleanup_pending'] is None


def test_backup_archive_and_directory_are_fsynced_before_success(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    events = []
    real_fsync_file = backup_module._fsync_file
    real_fsync_directory = backup_module._fsync_directory
    real_replace = backup_module.os.replace

    def record_file(path):
        events.append(('file', Path(path).name))
        return real_fsync_file(path)

    def record_directory(path):
        events.append(('directory', Path(path).resolve()))
        return real_fsync_directory(path)

    def record_replace(source_path, destination_path):
        events.append(('replace', Path(source_path).name, Path(destination_path).name))
        return real_replace(source_path, destination_path)

    monkeypatch.setattr(backup_module, '_fsync_file', record_file)
    monkeypatch.setattr(backup_module, '_fsync_directory', record_directory)
    monkeypatch.setattr(backup_module.os, 'replace', record_replace)

    payload = create_app_data_backup(source, backup_dir)
    archive = Path(payload['archive_path'])
    temporary_name = archive.with_suffix('.zip.tmp').name
    expected_order = [
        ('directory', backup_dir.resolve()),
        ('directory', tmp_path.resolve()),
        ('file', temporary_name),
        ('replace', temporary_name, archive.name),
        ('file', archive.name),
        ('directory', backup_dir.resolve()),
    ]

    assert events == expected_order


def test_nested_restore_parent_directories_are_durably_created(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    target = tmp_path / 'new-parent' / 'nested-parent' / 'restore'
    fsynced_directories = []
    real_fsync_directory = backup_module._fsync_directory

    def record_directory(path):
        fsynced_directories.append(Path(path).resolve())
        return real_fsync_directory(path)

    monkeypatch.setattr(backup_module, '_fsync_directory', record_directory)

    resolved_target = backup_module._target_restore_path(target)

    new_parent = tmp_path / 'new-parent'
    nested_parent = new_parent / 'nested-parent'
    assert resolved_target == nested_parent.resolve() / 'restore'
    assert nested_parent.is_dir()
    # Each new directory and the parent entry that names it must reach fsync
    # before restore staging/rename can use the path.
    assert fsynced_directories == [
        new_parent.resolve(),
        tmp_path.resolve(),
        nested_parent.resolve(),
        new_parent.resolve(),
    ]


def test_archive_directory_fsync_failure_prevents_verify_and_prune(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    verify_called = False
    prune_called = False
    real_fsync_directory = backup_module._fsync_directory

    def fail_backup_directory_fsync(path):
        if Path(path).resolve() == backup_dir.resolve():
            raise OSError('simulated archive directory fsync failure')
        return real_fsync_directory(path)

    def record_verify(*_args, **_kwargs):
        nonlocal verify_called
        verify_called = True

    def record_prune(*_args, **_kwargs):
        nonlocal prune_called
        prune_called = True

    monkeypatch.setattr(backup_module, '_fsync_directory', fail_backup_directory_fsync)
    monkeypatch.setattr(backup_module, 'verify_app_data_backup', record_verify)
    monkeypatch.setattr(backup_module, 'prune_app_data_backups', record_prune)

    with pytest.raises(OSError, match='archive directory fsync failure'):
        create_and_prune_app_data_backup(source, backup_dir, max_backups=1)

    assert verify_called is False
    assert prune_called is False


def test_staging_file_fsync_failure_never_reaches_target_commit(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_fsync_file = backup_module._fsync_file

    def fail_staged_file_fsync(path):
        candidate = Path(path)
        if 'staged' in candidate.parts and any(
            part.startswith('.data.restore-') for part in candidate.parts
        ):
            raise OSError('simulated staged file fsync failure')
        return real_fsync_file(path)

    monkeypatch.setattr(backup_module, '_fsync_file', fail_staged_file_fsync)
    monkeypatch.setattr(
        backup_module,
        '_atomic_exchange_directories',
        lambda *_args: pytest.fail('commit must not start before staged fsync'),
    )

    with pytest.raises(OSError, match='staged file fsync failure'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    assert (target / 'old.txt').read_text(encoding='utf-8') == 'old'
    assert not (target / 'new.txt').exists()
    assert not list(tmp_path.glob('.data.restore-*'))


def test_staged_tree_and_exchange_parents_are_fsynced_before_cleanup(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'nested').mkdir()
    (source / 'nested' / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    events = []
    real_fsync_tree = backup_module._fsync_tree
    real_fsync_directory = backup_module._fsync_directory
    real_remove = backup_module._remove_restore_transaction

    def record_tree(path):
        events.append(('tree', Path(path)))
        return real_fsync_tree(path)

    def record_directory(path):
        events.append(('directory', Path(path)))
        return real_fsync_directory(path)

    def emulate_exchange(staging, live_target):
        old_tree = staging.parent / 'emulated-old-tree'
        os.replace(live_target, old_tree)
        os.replace(staging, live_target)
        os.replace(old_tree, staging)
        events.append(('exchange', staging.parent))
        return True

    def record_cleanup(transaction_root):
        events.append(('cleanup', transaction_root))
        return real_remove(transaction_root)

    monkeypatch.setattr(backup_module, '_fsync_tree', record_tree)
    monkeypatch.setattr(backup_module, '_fsync_directory', record_directory)
    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', emulate_exchange)
    monkeypatch.setattr(backup_module, '_remove_restore_transaction', record_cleanup)

    restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    tree_index = next(index for index, event in enumerate(events) if event[0] == 'tree')
    exchange_index = next(index for index, event in enumerate(events) if event[0] == 'exchange')
    cleanup_index = next(index for index, event in enumerate(events) if event[0] == 'cleanup')
    transaction_root = events[exchange_index][1]
    post_exchange_directories = [
        event[1]
        for event in events[exchange_index + 1:cleanup_index]
        if event[0] == 'directory'
    ]

    assert tree_index < exchange_index < cleanup_index
    assert transaction_root in post_exchange_directories
    assert target.parent.resolve() in [path.resolve() for path in post_exchange_directories]


def test_extracting_phase_marker_exists_before_archive_extraction(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    source.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    target = tmp_path / 'data'
    captured = {}

    def fail_after_reading_marker(_archive, staging, *, expected_manifest):
        del expected_manifest
        marker = staging.parent / backup_module.RESTORE_TRANSACTION_MARKER
        captured.update(json.loads(marker.read_text(encoding='utf-8')))
        raise OSError('simulated extraction power loss')

    monkeypatch.setattr(
        backup_module,
        '_extract_and_validate_archive',
        fail_after_reading_marker,
    )

    with pytest.raises(OSError, match='simulated extraction power loss'):
        restore_app_data_backup(backup['archive_path'], target)

    assert captured['version'] == backup_module.RESTORE_TRANSACTION_VERSION
    assert captured['phase'] == 'extracting'
    assert captured['strategy'] is None
    assert not list(tmp_path.glob('.data.restore-*'))


def test_exchange_power_loss_after_swap_is_recovered_by_fingerprint(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')

    def exchange_then_lose_power(staging, live_target):
        old_tree = staging.parent / 'emulated-old-tree'
        os.replace(live_target, old_tree)
        os.replace(staging, live_target)
        os.replace(old_tree, staging)
        raise OSError('simulated power loss after exchange')

    monkeypatch.setattr(
        backup_module,
        '_atomic_exchange_directories',
        exchange_then_lose_power,
    )

    with pytest.raises(OSError, match='simulated power loss after exchange'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    transaction = next(tmp_path.glob('.data.restore-*'))
    marker = json.loads(
        (transaction / backup_module.RESTORE_TRANSACTION_MARKER).read_text(encoding='utf-8')
    )
    assert marker['phase'] == 'exchange_pending'
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert (transaction / 'staged' / 'old.txt').read_text(encoding='utf-8') == 'old'

    recovered = recover_interrupted_restore(target)

    assert recovered == [str(target.resolve())]
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not list(tmp_path.glob('.data.restore-*'))


def test_exchange_power_loss_before_parent_fsync_is_recovered(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_fsync_directory = backup_module._fsync_directory
    exchanged = False

    def emulate_exchange(staging, live_target):
        nonlocal exchanged
        old_tree = staging.parent / 'emulated-old-tree'
        os.replace(live_target, old_tree)
        os.replace(staging, live_target)
        os.replace(old_tree, staging)
        exchanged = True
        return True

    def fail_first_exchange_fsync(path):
        if exchanged and Path(path).name.startswith('.data.restore-'):
            raise OSError('simulated power loss before exchange fsync')
        return real_fsync_directory(path)

    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', emulate_exchange)
    monkeypatch.setattr(backup_module, '_fsync_directory', fail_first_exchange_fsync)

    with pytest.raises(OSError, match='simulated power loss before exchange fsync'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    monkeypatch.setattr(backup_module, '_fsync_directory', real_fsync_directory)
    recovered = recover_interrupted_restore(target)

    assert recovered == [str(target.resolve())]
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not list(tmp_path.glob('.data.restore-*'))


def test_non_exchange_power_loss_after_previous_move_recovers_on_retry(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_replace = backup_module.os.replace
    failed = False

    def move_previous_then_lose_power(source_path, destination_path):
        nonlocal failed
        result = real_replace(source_path, destination_path)
        if (
            not failed
            and Path(source_path) == target.resolve()
            and Path(destination_path).name == 'previous'
        ):
            failed = True
            raise OSError('simulated power loss after previous move')
        return result

    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', lambda *_args: False)
    monkeypatch.setattr(backup_module.os, 'replace', move_previous_then_lose_power)

    with pytest.raises(OSError, match='simulated power loss after previous move'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    transaction = next(tmp_path.glob('.data.restore-*'))
    marker = json.loads(
        (transaction / backup_module.RESTORE_TRANSACTION_MARKER).read_text(encoding='utf-8')
    )
    assert marker['phase'] == 'non_exchange_pending'
    assert not target.exists()
    assert (transaction / 'previous' / 'old.txt').read_text(encoding='utf-8') == 'old'

    monkeypatch.setattr(backup_module.os, 'replace', real_replace)
    # A direct retry first restores the durable previous tree, then performs the
    # requested restore again without leaving an orphan transaction.
    restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not (target / 'old.txt').exists()
    assert not list(tmp_path.glob('.data.restore-*'))


def test_non_exchange_power_loss_after_new_install_keeps_verified_target(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_replace = backup_module.os.replace
    failed = False

    def install_then_lose_power(source_path, destination_path):
        nonlocal failed
        result = real_replace(source_path, destination_path)
        if (
            not failed
            and Path(source_path).name == 'staged'
            and Path(destination_path) == target.resolve()
        ):
            failed = True
            raise OSError('simulated power loss after new install')
        return result

    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', lambda *_args: False)
    monkeypatch.setattr(backup_module.os, 'replace', install_then_lose_power)

    with pytest.raises(OSError, match='simulated power loss after new install'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    transaction = next(tmp_path.glob('.data.restore-*'))
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert (transaction / 'previous' / 'old.txt').read_text(encoding='utf-8') == 'old'

    monkeypatch.setattr(backup_module.os, 'replace', real_replace)
    recovered = recover_interrupted_restore(target)

    assert recovered == [str(target.resolve())]
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not list(tmp_path.glob('.data.restore-*'))


def test_first_install_power_loss_after_rename_finishes_on_recovery(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_replace = backup_module.os.replace
    failed = False

    def install_then_lose_power(source_path, destination_path):
        nonlocal failed
        result = real_replace(source_path, destination_path)
        if (
            not failed
            and Path(source_path).name == 'staged'
            and Path(destination_path) == target.resolve()
        ):
            failed = True
            raise OSError('simulated first-install power loss')
        return result

    monkeypatch.setattr(backup_module.os, 'replace', install_then_lose_power)

    with pytest.raises(OSError, match='simulated first-install power loss'):
        restore_app_data_backup(backup['archive_path'], target)

    transaction = next(tmp_path.glob('.data.restore-*'))
    marker = json.loads(
        (transaction / backup_module.RESTORE_TRANSACTION_MARKER).read_text(encoding='utf-8')
    )
    assert marker['phase'] == 'install_pending'

    monkeypatch.setattr(backup_module.os, 'replace', real_replace)
    recovered = recover_interrupted_restore(target)

    assert recovered == [str(target.resolve())]
    assert (target / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert not list(tmp_path.glob('.data.restore-*'))


def test_restore_and_recovery_reject_symbolic_link_target(tmp_path):
    source = tmp_path / 'source'
    external = tmp_path / 'external'
    target = tmp_path / 'data'
    source.mkdir()
    external.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (external / 'keep.txt').write_text('keep', encoding='utf-8')
    target.symlink_to(external, target_is_directory=True)
    backup = create_app_data_backup(source, tmp_path / 'backups')

    with pytest.raises(ValueError, match='symbolic link'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)
    with pytest.raises(ValueError, match='symbolic link'):
        recover_interrupted_restore(target)

    assert (external / 'keep.txt').read_text(encoding='utf-8') == 'keep'
    assert not (external / 'new.txt').exists()


def test_restore_manifest_failure_leaves_existing_target_unchanged(tmp_path):
    archive = tmp_path / 'tampered.zip'
    target = tmp_path / 'data'
    target.mkdir()
    (target / 'old.txt').write_text('old', encoding='utf-8')
    original_manifest = file_manifest(target)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('new.txt', b'new')
        zf.writestr(BACKUP_MANIFEST_MEMBER, json.dumps({
            'algorithm': 'sha256',
            'files': {'new.txt': hashlib.sha256(b'different').hexdigest()},
            'version': 1,
        }))

    with pytest.raises(ValueError, match='embedded manifest'):
        restore_app_data_backup(archive, target, overwrite=True)

    assert file_manifest(target) == original_manifest
    assert not list(tmp_path.glob('.data.restore-*'))


def test_restore_corrupt_sqlite_leaves_existing_target_unchanged(tmp_path):
    archive = tmp_path / 'corrupt-sqlite.zip'
    target = tmp_path / 'data'
    target.mkdir()
    (target / 'old.txt').write_text('old', encoding='utf-8')
    original_manifest = file_manifest(target)
    broken_database = b'SQLite format 3\x00' + b'broken'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('broken.db', broken_database)

    with pytest.raises(ValueError, match='SQLite integrity check failed'):
        restore_app_data_backup(archive, target, overwrite=True)

    assert file_manifest(target) == original_manifest
    assert not list(tmp_path.glob('.data.restore-*'))


def test_restore_commit_disk_error_rolls_back_existing_target(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    original_manifest = file_manifest(target)
    real_replace = backup_module.os.replace
    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', lambda *_args: False)

    def fail_staged_commit(source_path, destination_path):
        if Path(source_path).name == 'staged' and Path(destination_path) == target.resolve():
            raise OSError('simulated disk failure')
        return real_replace(source_path, destination_path)

    monkeypatch.setattr(backup_module.os, 'replace', fail_staged_commit)

    with pytest.raises(OSError, match='simulated disk failure'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    assert file_manifest(target) == original_manifest
    assert not (target / 'new.txt').exists()
    assert not list(tmp_path.glob('.data.restore-*'))


def test_restore_preserves_recovery_copy_if_rollback_itself_fails(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')
    real_replace = backup_module.os.replace
    monkeypatch.setattr(backup_module, '_atomic_exchange_directories', lambda *_args: False)

    def fail_commit_and_rollback(source_path, destination_path):
        source_name = Path(source_path).name
        if source_name in {'staged', 'previous'}:
            raise OSError(f'simulated {source_name} rename failure')
        return real_replace(source_path, destination_path)

    monkeypatch.setattr(backup_module.os, 'replace', fail_commit_and_rollback)

    with pytest.raises(RuntimeError, match='previous data remains at'):
        restore_app_data_backup(backup['archive_path'], target, overwrite=True)

    transactions = list(tmp_path.glob('.data.restore-*'))
    assert len(transactions) == 1
    assert (transactions[0] / 'previous' / 'old.txt').read_text(encoding='utf-8') == 'old'


def test_startup_recovers_previous_tree_from_interrupted_restore(tmp_path):
    import utils.app_data_backup as backup_module

    target = tmp_path / 'data'
    transaction = tmp_path / '.data.restore-interrupted'
    previous = transaction / 'previous'
    previous.mkdir(parents=True)
    (previous / 'old.txt').write_text('old', encoding='utf-8')
    backup_module._write_restore_transaction_marker(transaction, target)

    recovered = recover_interrupted_restore(target)

    resolved_target = target.parent.resolve() / target.name
    assert recovered == [str(resolved_target)]
    assert (resolved_target / 'old.txt').read_text(encoding='utf-8') == 'old'
    assert not transaction.exists()


def test_restore_without_overwrite_never_replaces_nonempty_target(tmp_path):
    source = tmp_path / 'source'
    target = tmp_path / 'data'
    source.mkdir()
    target.mkdir()
    (source / 'new.txt').write_text('new', encoding='utf-8')
    (target / 'old.txt').write_text('old', encoding='utf-8')
    backup = create_app_data_backup(source, tmp_path / 'backups')

    with pytest.raises(FileExistsError, match='already exists'):
        restore_app_data_backup(backup['archive_path'], target)

    assert (target / 'old.txt').read_text(encoding='utf-8') == 'old'
    assert not (target / 'new.txt').exists()


def test_app_data_backup_retention_only_removes_owned_archives(tmp_path):
    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    archives = []
    for index in range(4):
        archive = backup_dir / f'app_data_backup_20260827_00000{index}_000000000.zip'
        archive.write_bytes(str(index).encode())
        archive.touch()
        archives.append(archive)
    unrelated = backup_dir / 'operator-export.zip'
    unrelated.write_bytes(b'keep')

    removed = prune_app_data_backups(backup_dir, 2)

    assert len(removed) == 2
    assert len(list(backup_dir.glob('app_data_backup_*.zip'))) == 2
    assert unrelated.exists()


def test_create_and_prune_backup_enforces_max_backups(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    for _ in range(3):
        create_and_prune_app_data_backup(source, backup_dir, max_backups=2)

    assert len(list(backup_dir.glob('app_data_backup_*.zip'))) == 2
    assert not list(backup_dir.glob('*.tmp'))


def test_new_backup_cleans_only_stale_owned_incomplete_artifacts(
    tmp_path, monkeypatch,
):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    backup_dir.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    stale_tmp = backup_dir / 'app_data_backup_20200101_000000_000000000.zip.tmp'
    stale_pending = backup_dir / 'app_data_backup_20200101_000001_000000000.zip.pending'
    young_tmp = backup_dir / 'app_data_backup_20200101_000002_000000000.zip.tmp'
    unrelated = backup_dir / 'operator-export.zip.tmp'
    symlink = backup_dir / 'app_data_backup_20200101_000003_000000000.zip.tmp'
    for artifact in (stale_tmp, stale_pending, young_tmp, unrelated):
        artifact.write_bytes(b'incomplete')
    symlink.symlink_to(unrelated)

    real_cleanup = backup_module.cleanup_stale_backup_artifacts
    calls = []

    def cleanup_for_new_backup(path):
        calls.append(Path(path).resolve())
        return real_cleanup(
            path,
            now_seconds=time.time() + STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS + 1,
        )

    # Keep one correctly named artifact young by actively locking it. This also
    # proves a second backup cannot remove a file that is still being written.
    descriptor = os.open(young_tmp, os.O_RDONLY)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monkeypatch.setattr(backup_module, 'cleanup_stale_backup_artifacts', cleanup_for_new_backup)
    try:
        create_app_data_backup(source, backup_dir)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert calls == [backup_dir.resolve()]
    assert not stale_tmp.exists()
    assert not stale_pending.exists()
    assert young_tmp.exists()
    assert unrelated.exists()
    assert symlink.is_symlink()


def test_stale_artifact_cleanup_requires_current_uid_and_fsyncs_directory(
    tmp_path, monkeypatch,
):
    import utils.app_data_backup as backup_module

    backup_dir = tmp_path / 'backups'
    backup_dir.mkdir()
    artifact = backup_dir / 'app_data_backup_20200101_000000_000000000.zip.pending'
    artifact.write_bytes(b'incomplete')
    future = time.time() + STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS + 1
    actual_uid = os.geteuid()

    monkeypatch.setattr(backup_module.os, 'geteuid', lambda: actual_uid + 1)
    assert cleanup_stale_backup_artifacts(backup_dir, now_seconds=future) == []
    assert artifact.exists()

    monkeypatch.setattr(backup_module.os, 'geteuid', lambda: actual_uid)
    fsynced = []
    real_fsync_directory = backup_module._fsync_directory

    def record_fsync(path):
        fsynced.append(Path(path).resolve())
        return real_fsync_directory(path)

    monkeypatch.setattr(backup_module, '_fsync_directory', record_fsync)
    removed = cleanup_stale_backup_artifacts(backup_dir, now_seconds=future)

    assert removed == [str(artifact.resolve())]
    assert not artifact.exists()
    assert fsynced == [backup_dir.resolve()]


def test_pending_archive_is_locked_during_active_verification(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    payload = create_app_data_backup(source, backup_dir, pending=True)
    pending = Path(payload['archive_path'])
    observed = []

    def verifier(_archive, *, expected_manifest):
        assert expected_manifest == payload['source_manifest']
        removed = cleanup_stale_backup_artifacts(
            backup_dir,
            now_seconds=time.time() + STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS + 1,
        )
        observed.append((removed, pending.exists()))
        return {'ok': True}

    finalized = verify_and_finalize_app_data_backup(
        payload,
        backup_dir,
        verifier=verifier,
    )

    assert observed == [([], True)]
    assert Path(finalized['archive_path']).is_file()


def test_verified_new_backup_is_pinned_against_a_future_mtime_candidate(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    sample = source / 'sample.txt'
    sample.write_text('older-known-good', encoding='utf-8')
    older_payload = create_app_data_backup(source, backup_dir)
    older_archive = Path(older_payload['archive_path'])
    past_time = time.time() - 10_000
    os.utime(older_archive, (past_time, past_time))

    sample.write_text('newly-verified', encoding='utf-8')
    future_archive = backup_dir / 'app_data_backup_20990101_000000_000000000.zip'
    future_archive.write_bytes(b'unverified-future-archive')
    future_time = time.time() + 10_000_000
    os.utime(future_archive, (future_time, future_time))

    payload = create_and_prune_app_data_backup(source, backup_dir, max_backups=2)
    new_archive = Path(payload['archive_path'])

    assert new_archive.is_file()
    assert payload['verification']['ok'] is True
    assert not future_archive.exists()
    assert {
        archive.resolve() for archive in backup_dir.glob('app_data_backup_*.zip')
    } == {new_archive.resolve(), older_archive.resolve()}


def test_pending_backup_is_hidden_from_retention_until_verification(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('pending', encoding='utf-8')

    payload = create_app_data_backup(source, backup_dir, pending=True)
    pending_archive = Path(payload['archive_path'])

    assert pending_archive.name.endswith('.zip.pending')
    assert pending_archive.is_file()
    assert list(backup_dir.glob('app_data_backup_*.zip')) == []

    finalized = verify_and_finalize_app_data_backup(payload, backup_dir)
    final_archive = Path(finalized['archive_path'])
    assert final_archive.name.endswith('.zip')
    assert final_archive.is_file()
    assert not pending_archive.exists()


def test_verified_backup_includes_wal_and_passes_sqlite_integrity(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    database = source / 'chroma.sqlite3'
    connection = sqlite3.connect(database)
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA wal_autocheckpoint=0')
        connection.execute('CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)')
        connection.commit()
        connection.execute('INSERT INTO notes(body) VALUES (?)', ('committed-in-wal',))
        connection.commit()
        assert database.with_name(f'{database.name}-wal').is_file()

        payload = create_and_prune_app_data_backup(source, backup_dir, max_backups=2)
    finally:
        connection.close()

    assert payload['verification']['ok'] is True
    assert payload['verification']['sqlite_databases_checked'] == ['chroma.sqlite3']
    with zipfile.ZipFile(payload['archive_path']) as archive:
        assert 'chroma.sqlite3-wal' in archive.namelist()
    restore = restore_app_data_backup(payload['archive_path'], tmp_path / 'restored')
    assert restore['restored_manifest'] == payload['source_manifest']
    assert file_manifest(tmp_path / 'restored') == payload['source_manifest']


def test_failed_restore_verification_happens_before_prune(tmp_path, monkeypatch):
    import utils.app_data_backup as backup_module

    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    backup_dir.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')
    old_archives = []
    for index in range(2):
        archive = backup_dir / f'app_data_backup_20260827_00000{index}_000000000.zip'
        archive.write_bytes(b'known-good')
        old_archives.append(archive)

    prune_called = False

    def fail_verification(*_args, **_kwargs):
        raise ValueError('restore rehearsal failed')

    def record_prune(*_args, **_kwargs):
        nonlocal prune_called
        prune_called = True
        return []

    monkeypatch.setattr(backup_module, 'verify_app_data_backup', fail_verification)
    monkeypatch.setattr(backup_module, 'prune_app_data_backups', record_prune)

    with pytest.raises(ValueError, match='restore rehearsal failed'):
        create_and_prune_app_data_backup(source, backup_dir, max_backups=1)

    assert prune_called is False
    assert all(archive.read_bytes() == b'known-good' for archive in old_archives)
    assert set(backup_dir.glob('app_data_backup_*.zip')) == set(old_archives)


def test_corrupt_sqlite_restore_is_rejected(tmp_path):
    archive = tmp_path / 'corrupt-sqlite.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('broken.db', b'SQLite format 3\x00' + b'broken')

    with pytest.raises(ValueError, match='SQLite integrity check failed'):
        verify_app_data_backup(archive)


def _load_backup_script():
    script = ROOT / 'scripts' / 'backup_app_data.py'
    spec = importlib.util.spec_from_file_location('backup_app_data_test', script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('raise_inside', [False, True])
def test_quiesce_always_resumes_writer_group(monkeypatch, raise_inside):
    module = _load_backup_script()
    events = []
    monkeypatch.setattr(module.sys, 'platform', 'linux')
    monkeypatch.setattr(module.os, 'getpgid', lambda pid: pid)
    monkeypatch.setattr(module.os, 'getpgrp', lambda: 9999)
    monkeypatch.setattr(
        module.os,
        'killpg',
        lambda process_group, sent_signal: events.append((process_group, sent_signal)),
    )
    monkeypatch.setattr(module, '_wait_until_process_group_stopped', lambda *_args: None)
    monkeypatch.setattr(module.signal, 'setitimer', lambda *_args: (0.0, 0.0))

    def exercise():
        with module._quiesce_writer_process_group(1234, 10):
            events.append(('archive', None))
            if raise_inside:
                raise RuntimeError('archive failed')

    if raise_inside:
        with pytest.raises(RuntimeError, match='archive failed'):
            exercise()
    else:
        exercise()

    assert events == [
        (1234, signal.SIGSTOP),
        ('archive', None),
        (1234, signal.SIGCONT),
    ]


def test_quiesce_resumes_when_stop_confirmation_fails(monkeypatch):
    module = _load_backup_script()
    events = []
    monkeypatch.setattr(module.sys, 'platform', 'linux')
    monkeypatch.setattr(module.os, 'getpgid', lambda pid: pid)
    monkeypatch.setattr(module.os, 'getpgrp', lambda: 9999)
    monkeypatch.setattr(
        module.os,
        'killpg',
        lambda process_group, sent_signal: events.append((process_group, sent_signal)),
    )
    monkeypatch.setattr(
        module,
        '_wait_until_process_group_stopped',
        lambda *_args: (_ for _ in ()).throw(TimeoutError('not stopped')),
    )
    monkeypatch.setattr(module.signal, 'setitimer', lambda *_args: (0.0, 0.0))

    with pytest.raises(TimeoutError, match='not stopped'):
        with module._quiesce_writer_process_group(1234, 10):
            pytest.fail('snapshot must not start before stop confirmation')

    assert events == [
        (1234, signal.SIGSTOP),
        (1234, signal.SIGCONT),
    ]


def test_quiesce_timeout_handler_resumes_before_raising(monkeypatch):
    module = _load_backup_script()
    events = []
    handlers = {}
    monkeypatch.setattr(module.sys, 'platform', 'linux')
    monkeypatch.setattr(module.os, 'getpgid', lambda pid: pid)
    monkeypatch.setattr(module.os, 'getpgrp', lambda: 9999)
    monkeypatch.setattr(
        module.os,
        'killpg',
        lambda process_group, sent_signal: events.append((process_group, sent_signal)),
    )
    monkeypatch.setattr(module, '_wait_until_process_group_stopped', lambda *_args: None)
    monkeypatch.setattr(module.signal, 'getsignal', lambda _sig: 'previous-handler')
    monkeypatch.setattr(module.signal, 'getitimer', lambda _which: (0.0, 0.0))
    monkeypatch.setattr(
        module.signal,
        'signal',
        lambda sent_signal, handler: handlers.__setitem__(sent_signal, handler),
    )

    def fire_immediately(_which, seconds, *_args):
        if seconds:
            handlers[signal.SIGALRM]()
        return (0.0, 0.0)

    monkeypatch.setattr(module.signal, 'setitimer', fire_immediately)

    with pytest.raises(TimeoutError, match='quiesce timeout'):
        with module._quiesce_writer_process_group(1234, 10):
            pytest.fail('timer fires before the snapshot body')

    assert events == [
        (1234, signal.SIGSTOP),
        (1234, signal.SIGCONT),
    ]


class _FakeStopEvent:
    def __init__(self, wait_results):
        self.wait_results = iter(wait_results)
        self.waited = []
        self.stopped = False

    def clear(self):
        self.stopped = False

    def set(self):
        self.stopped = True

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.waited.append(seconds)
        result = next(self.wait_results)
        if result:
            self.stopped = True
        return result


def test_backup_daemon_initial_delay_is_configurable_and_signal_responsive(
    tmp_path, monkeypatch,
):
    module = _load_backup_script()
    stop_event = _FakeStopEvent([True])
    cleanup_calls = []
    monkeypatch.setattr(module, '_STOP', stop_event)
    monkeypatch.setattr(module.signal, 'signal', lambda *_args: None)
    monkeypatch.setattr(
        module,
        'cleanup_stale_backup_artifacts',
        lambda path: cleanup_calls.append(Path(path).resolve()),
    )
    monkeypatch.setattr(
        module,
        '_run_backup_with_retry',
        lambda *_args, **_kwargs: pytest.fail('backup must not start after a stop signal'),
    )

    result = module.main([
        'daemon',
        '--backup-dir', str(tmp_path / 'backups'),
        '--initial-delay-seconds', '123',
        '--writer-pid', '1234',
        '--max-cycles', '1',
    ])

    assert result == 0
    assert cleanup_calls == [(tmp_path / 'backups').resolve()]
    assert stop_event.waited == [123]


def test_backup_daemon_rejects_a_second_instance_for_the_same_directory(tmp_path):
    module = _load_backup_script()
    backup_dir = tmp_path / 'backups'

    with module._single_backup_daemon(str(backup_dir)):
        with pytest.raises(RuntimeError, match='already running'):
            with module._single_backup_daemon(str(backup_dir)):
                pytest.fail('a second daemon must never acquire the lock')


def test_backup_retry_uses_bounded_backoff_then_raises(monkeypatch):
    module = _load_backup_script()
    stop_event = _FakeStopEvent([False, False])
    attempts = []
    monkeypatch.setattr(module, '_STOP', stop_event)

    def fail_backup(*_args, **_kwargs):
        attempts.append('failed')
        raise OSError('storage unavailable')

    monkeypatch.setattr(module, '_run_consistent_backup', fail_backup)

    with pytest.raises(RuntimeError, match='failed after 3 attempts'):
        module._run_backup_with_retry(
            'data',
            'backups',
            30,
            writer_pid=1234,
            max_quiesce_seconds=600,
        )

    assert attempts == ['failed', 'failed', 'failed']
    assert stop_event.waited == [5, 10]


def test_backup_daemon_exits_nonzero_after_terminal_failure(
    tmp_path, monkeypatch, capsys,
):
    module = _load_backup_script()
    stop_event = _FakeStopEvent([False])
    monkeypatch.setattr(module, '_STOP', stop_event)
    monkeypatch.setattr(module.signal, 'signal', lambda *_args: None)
    monkeypatch.setattr(
        module,
        '_run_backup_with_retry',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError('backup failed after 3 attempts')
        ),
    )

    result = module.main([
        'daemon',
        '--backup-dir', str(tmp_path / 'backups'),
        '--initial-delay-seconds', '30',
        '--writer-pid', '1234',
        '--max-cycles', '1',
    ])

    assert result == module.DAEMON_FATAL_EXIT_CODE
    assert result != 0
    assert 'for supervisor detection' in capsys.readouterr().err


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='SIGSTOP snapshot is Linux-only')
def test_app_data_backup_daemon_runs_real_startup_backup(tmp_path):
    source = tmp_path / 'data'
    backup_dir = tmp_path / 'backups'
    source.mkdir()
    (source / 'sample.txt').write_text('sample', encoding='utf-8')

    writer = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(60)'],
        start_new_session=True,
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / 'scripts' / 'backup_app_data.py'),
                'daemon',
                '--source', str(source),
                '--backup-dir', str(backup_dir),
                '--interval-hours', '1',
                '--max-backups', '2',
                '--writer-pid', str(writer.pid),
                '--initial-delay-seconds', '1',
                '--max-cycles', '1',
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert writer.poll() is None
    finally:
        if writer.poll() is None:
            os.killpg(writer.pid, signal.SIGTERM)
            writer.wait(timeout=5)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['file_count'] == 1
    assert payload['verification']['ok'] is True
    assert Path(payload['archive_path']).is_file()
