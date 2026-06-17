"""app_data volume backup and restore helpers."""
from __future__ import annotations

import hashlib
import time
import zipfile
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
    return time.strftime('%Y%m%d_%H%M%S', time.gmtime())


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def create_app_data_backup(source_dir: str | Path, backup_dir: str | Path) -> dict:
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

    return {
        'archive_path': str(archive_path),
        'file_count': len(source_manifest),
        'source_manifest': source_manifest,
        'size_bytes': archive_path.stat().st_size,
    }


def _safe_zip_member(member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or '..' in member_path.parts:
        raise ValueError(f'unsafe archive member path: {member_name}')
    return member_path


def restore_app_data_backup(
    archive_path: str | Path,
    target_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict:
    """Restore an app_data zip archive into target_dir with zip-slip protection."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f'app_data backup archive not found: {archive}')

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
    }


def verify_backup_round_trip(source_dir: str | Path, work_dir: str | Path) -> dict:
    """Create and restore an app_data archive, then compare manifests."""
    work_path = Path(work_dir)
    backup = create_app_data_backup(source_dir, work_path / 'backups')
    restore = restore_app_data_backup(backup['archive_path'], work_path / 'restore')
    return {
        'ok': backup['source_manifest'] == restore['restored_manifest'],
        'archive_path': backup['archive_path'],
        'source_manifest': backup['source_manifest'],
        'restored_manifest': restore['restored_manifest'],
    }
