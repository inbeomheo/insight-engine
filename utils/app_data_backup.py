"""app_data volume backup and restore helpers."""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def file_manifest(root: str | Path) -> dict[str, str]:
    """Return a stable relative-path -> sha256 manifest for all files under root."""
    root_path = Path(root).resolve()
    manifest: dict[str, str] = {}
    if not root_path.exists():
        return manifest

    for path in sorted(p for p in root_path.rglob('*') if p.is_file()):
        relative = path.relative_to(root_path).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest[relative] = digest
    return manifest


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def backup_manifest_path(archive_path: str | Path) -> Path:
    """Return the sidecar manifest path for an app_data backup archive."""
    archive = Path(archive_path)
    return archive.with_name(f'{archive.name}.manifest.json')


def load_backup_sidecar_manifest(archive_path: str | Path) -> dict:
    """Load the sidecar manifest for a backup archive."""
    manifest_path = backup_manifest_path(archive_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f'app_data backup manifest not found: {manifest_path}')
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def _write_backup_sidecar_manifest(archive_path: Path, source_manifest: dict[str, str]) -> Path:
    sidecar_path = backup_manifest_path(archive_path)
    metadata = {
        'schema_version': 1,
        'archive': archive_path.name,
        'created_at': _iso_now(),
        'sha256': _sha256_file(archive_path),
        'size_bytes': archive_path.stat().st_size,
        'file_count': len(source_manifest),
        'source_manifest': source_manifest,
    }
    sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    return sidecar_path


def _validate_backup_sidecar(archive_path: Path, *, verify_sha: bool = False) -> dict:
    sidecar_path = backup_manifest_path(archive_path)
    if not sidecar_path.is_file():
        return {'present': False, 'valid': False, 'error': 'missing'}

    try:
        manifest = load_backup_sidecar_manifest(archive_path)
    except Exception as exc:
        return {'present': True, 'valid': False, 'error': f'{exc.__class__.__name__}'}

    if manifest.get('archive') != archive_path.name:
        return {'present': True, 'valid': False, 'error': 'archive mismatch'}
    if manifest.get('size_bytes') != archive_path.stat().st_size:
        return {'present': True, 'valid': False, 'error': 'size mismatch'}
    if not isinstance(manifest.get('source_manifest'), dict):
        return {'present': True, 'valid': False, 'error': 'source manifest missing'}
    if verify_sha and manifest.get('sha256') != _sha256_file(archive_path):
        return {'present': True, 'valid': False, 'error': 'sha256 mismatch'}

    return {'present': True, 'valid': True, 'error': None}


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def prune_app_data_backups(
    backup_dir: str | Path,
    max_backups: int,
) -> list[str]:
    """Delete old app_data backup archives beyond max_backups newest files."""
    if max_backups < 1:
        raise ValueError('max_backups must be at least 1')

    backup_path = Path(backup_dir).resolve()
    archives = sorted(
        backup_path.glob('app_data_backup_*.zip'),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    pruned: list[str] = []
    for archive in archives[max_backups:]:
        archive.unlink(missing_ok=True)
        backup_manifest_path(archive).unlink(missing_ok=True)
        pruned.append(str(archive))
    return pruned


def latest_app_data_backup(backup_dir: str | Path, *, now: datetime | None = None) -> dict | None:
    """Return non-secret metadata for the newest app_data backup archive."""
    backup_path = Path(backup_dir).resolve()
    archives = sorted(
        backup_path.glob('app_data_backup_*.zip'),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    if not archives:
        return None

    latest = archives[0]
    sidecar = _validate_backup_sidecar(latest, verify_sha=False)
    modified_at = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc)
    current_time = now or datetime.now(timezone.utc)
    age_seconds = max(0.0, (current_time - modified_at).total_seconds())
    return {
        'archive': latest.name,
        'age_seconds': round(age_seconds, 1),
        'modified_at': modified_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'size_bytes': latest.stat().st_size,
        'is_zipfile': zipfile.is_zipfile(latest),
        'manifest_present': sidecar['present'],
        'manifest_valid': sidecar['valid'],
        'manifest_error': sidecar['error'],
    }


def create_app_data_backup(
    source_dir: str | Path,
    backup_dir: str | Path,
    *,
    max_backups: int | None = None,
    replica_dir: str | Path | None = None,
    max_replica_backups: int | None = None,
) -> dict:
    """Create a zip archive of app_data in a separate backup directory."""
    source_path = Path(source_dir).resolve()
    backup_path = Path(backup_dir).resolve()
    if not source_path.is_dir():
        raise FileNotFoundError(f'app_data source directory not found: {source_path}')

    backup_path.mkdir(parents=True, exist_ok=True)
    archive_path = backup_path / f'app_data_backup_{_timestamp()}.zip'
    source_manifest = file_manifest(source_path)

    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in source_path.rglob('*') if p.is_file()):
            if _is_within(path, backup_path):
                continue
            zf.write(path, path.relative_to(source_path).as_posix())

    manifest_path = _write_backup_sidecar_manifest(archive_path, source_manifest)

    pruned_archive_paths: list[str] = []
    if max_backups is not None:
        pruned_archive_paths = prune_app_data_backups(backup_path, max_backups)

    replica: dict | None = None
    if replica_dir:
        replica = replicate_app_data_backup(
            archive_path,
            replica_dir,
            max_backups=max_replica_backups,
        )

    return {
        'archive_path': str(archive_path),
        'file_count': len(source_manifest),
        'source_manifest': source_manifest,
        'size_bytes': archive_path.stat().st_size,
        'sha256': _sha256_file(archive_path),
        'manifest_path': str(manifest_path),
        'pruned_archive_paths': pruned_archive_paths,
        'replica': replica,
    }


def replicate_app_data_backup(
    archive_path: str | Path,
    replica_dir: str | Path,
    *,
    max_backups: int | None = None,
) -> dict:
    """Copy a backup archive to a second directory for off-host or external mounts."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f'app_data backup archive not found: {archive}')

    replica_path = Path(replica_dir).resolve()
    replica_path.mkdir(parents=True, exist_ok=True)
    destination = replica_path / archive.name
    shutil.copy2(archive, destination)
    source_manifest_path = backup_manifest_path(archive)
    destination_manifest_path = backup_manifest_path(destination)
    manifest_present = source_manifest_path.is_file()
    if manifest_present:
        shutil.copy2(source_manifest_path, destination_manifest_path)

    pruned_archive_paths: list[str] = []
    if max_backups is not None:
        pruned_archive_paths = prune_app_data_backups(replica_path, max_backups)

    return {
        'replica_path': str(destination),
        'size_bytes': destination.stat().st_size,
        'sha256': _sha256_file(destination),
        'manifest_path': str(destination_manifest_path) if manifest_present else None,
        'manifest_present': manifest_present,
        'pruned_archive_paths': pruned_archive_paths,
    }


def _safe_zip_member(member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or '..' in member_path.parts:
        raise ValueError(f'unsafe archive member path: {member_name}')
    return member_path


def _archive_file_manifest(archive: Path) -> dict[str, str]:
    """Return a safe relative-path -> sha256 manifest for files inside a backup archive."""
    manifest: dict[str, str] = {}
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            relative = _safe_zip_member(info.filename).as_posix()
            if relative in manifest:
                raise ValueError(f'duplicate archive member path: {relative}')
            manifest[relative] = hashlib.sha256(zf.read(info)).hexdigest()
    return manifest


def verify_backup_sidecar_before_restore(archive_path: str | Path) -> dict:
    """Verify sidecar metadata and archive contents before writing restored files."""
    archive = Path(archive_path).resolve()
    sidecar = _validate_backup_sidecar(archive, verify_sha=True)
    if not sidecar['valid']:
        raise ValueError(f'app_data backup sidecar is invalid: {sidecar["error"]}')

    manifest = load_backup_sidecar_manifest(archive)
    expected_manifest = manifest.get('source_manifest') if isinstance(manifest.get('source_manifest'), dict) else {}
    archive_manifest = _archive_file_manifest(archive)
    if archive_manifest != expected_manifest:
        raise ValueError('app_data backup archive contents do not match sidecar manifest')

    return {
        'archive_path': str(archive),
        'manifest_path': str(backup_manifest_path(archive)),
        'file_count': len(expected_manifest),
        'sha256': manifest.get('sha256'),
        'size_bytes': archive.stat().st_size,
    }


def restore_app_data_backup(
    archive_path: str | Path,
    target_dir: str | Path,
    *,
    overwrite: bool = False,
    verify_sidecar: bool = False,
) -> dict:
    """Restore an app_data zip archive into target_dir with zip-slip protection."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f'app_data backup archive not found: {archive}')
    sidecar_verification = verify_backup_sidecar_before_restore(archive) if verify_sidecar else None

    target = Path(target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    restored = 0

    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            relative = _safe_zip_member(info.filename)
            destination = target / relative
            if destination.exists() and not overwrite:
                raise FileExistsError(f'restore target already exists: {destination}')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(zf.read(info))
            restored += 1

    return {
        'archive_path': str(archive),
        'target_dir': str(target),
        'restored_file_count': restored,
        'restored_manifest': file_manifest(target),
        'sidecar_verified': bool(sidecar_verification),
    }


def verify_backup_round_trip(source_dir: str | Path, work_dir: str | Path) -> dict:
    """Create and restore an app_data archive, then compare manifests."""
    work_path = Path(work_dir)
    backup = create_app_data_backup(source_dir, work_path / 'backups')
    return verify_backup_archive(backup['archive_path'], backup['source_manifest'], work_path / 'restore')


def verify_backup_archive(
    archive_path: str | Path,
    source_manifest: dict[str, str],
    restore_dir: str | Path,
) -> dict:
    """Restore an archive and compare it to an expected source manifest."""
    restore = restore_app_data_backup(archive_path, restore_dir)
    return {
        'ok': source_manifest == restore['restored_manifest'],
        'archive_path': str(Path(archive_path).resolve()),
        'source_manifest': source_manifest,
        'restored_manifest': restore['restored_manifest'],
    }


def verify_backup_archive_with_sidecar(archive_path: str | Path, restore_dir: str | Path) -> dict:
    """Verify archive sha256 and restored files against its sidecar manifest."""
    archive = Path(archive_path).resolve()
    manifest = load_backup_sidecar_manifest(archive)
    sha256_ok = manifest.get('sha256') == _sha256_file(archive)
    size_ok = manifest.get('size_bytes') == archive.stat().st_size
    restore = restore_app_data_backup(archive, restore_dir, verify_sidecar=True)
    expected_manifest = manifest.get('source_manifest') if isinstance(manifest.get('source_manifest'), dict) else {}
    restored_ok = expected_manifest == restore['restored_manifest']
    return {
        'ok': sha256_ok and size_ok and restored_ok,
        'archive_path': str(archive),
        'manifest_path': str(backup_manifest_path(archive)),
        'sha256': manifest.get('sha256'),
        'size_bytes': archive.stat().st_size,
        'sha256_ok': sha256_ok,
        'size_ok': size_ok,
        'restored_ok': restored_ok,
        'file_count': len(expected_manifest),
        'restored_file_count': restore['restored_file_count'],
        'source_manifest': expected_manifest,
        'restored_manifest': restore['restored_manifest'],
    }


def verify_latest_app_data_backup(backup_dir: str | Path, restore_dir: str | Path) -> dict:
    """Verify the newest backup archive in a directory using its sidecar manifest."""
    backup_path = Path(backup_dir).resolve()
    archives = sorted(
        backup_path.glob('app_data_backup_*.zip'),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    if not archives:
        return {
            'ok': False,
            'backup_dir': str(backup_path),
            'error': 'no backup archives found',
        }
    try:
        return verify_backup_archive_with_sidecar(archives[0], restore_dir)
    except Exception as exc:
        return {
            'ok': False,
            'backup_dir': str(backup_path),
            'archive_path': str(archives[0]),
            'error': f'{exc.__class__.__name__}: {exc}',
        }
