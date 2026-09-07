"""app_data volume backup and restore helpers."""
from __future__ import annotations

import ctypes
import errno
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    import fcntl
except ImportError:  # pragma: no cover - scheduled backups are Linux-only
    fcntl = None


BACKUP_PREFIX = 'app_data_backup_'
BACKUP_SUFFIX = '.zip'
BACKUP_PENDING_SUFFIX = f'{BACKUP_SUFFIX}.pending'
STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS = 24 * 60 * 60
BACKUP_MANIFEST_MEMBER = '.insight-engine-backup/manifest-v1.json'
BACKUP_MANIFEST_VERSION = 1
RESTORE_TRANSACTION_MARKER = '.insight-engine-restore-transaction-v1.json'
RESTORE_TRANSACTION_VERSION = 2
_MANIFEST_MAX_BYTES = 128 * 1024 * 1024
_AT_FDCWD = -100
_RENAME_EXCHANGE = 2
_RESTORE_PHASES = {
    'extracting',
    'prepared',
    'exchange_pending',
    'exchange_committed',
    'non_exchange_pending',
    'previous_moved',
    'install_pending',
    'committed',
}
_OWNED_INCOMPLETE_BACKUP_RE = re.compile(
    rf'^{re.escape(BACKUP_PREFIX)}\d{{8}}_\d{{6}}_\d{{9}}'
    rf'{re.escape(BACKUP_SUFFIX)}\.(?:tmp|pending)$'
)


@contextmanager
def _locked_existing_artifact(
    path: Path,
    *,
    exclusive: bool,
    nonblocking: bool = False,
):
    """Lock one regular artifact without following a replaced symbolic link."""
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f'backup artifact is not a regular file: {path}')
        if fcntl is not None:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if nonblocking:
                operation |= fcntl.LOCK_NB
            fcntl.flock(descriptor, operation)
        yield metadata
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(descriptor)


@contextmanager
def _locked_new_artifact(path: Path):
    """Create and exclusively lock a new temporary archive until installation."""
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, 'O_CLOEXEC', 0)
        | getattr(os, 'O_NOFOLLOW', 0)
    )
    descriptor = os.open(path, flags, 0o600)
    stream = os.fdopen(descriptor, 'w+b')
    try:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield stream
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
        stream.close()


def cleanup_stale_backup_artifacts(
    backup_dir: str | Path,
    *,
    minimum_age_seconds: int = STALE_BACKUP_ARTIFACT_MIN_AGE_SECONDS,
    now_seconds: float | None = None,
) -> list[str]:
    """Remove only old, inactive, same-UID incomplete archives and fsync removal."""
    if (
        not isinstance(minimum_age_seconds, int)
        or isinstance(minimum_age_seconds, bool)
        or minimum_age_seconds < 1
    ):
        raise ValueError('minimum artifact age must be a positive integer')
    now = time.time() if now_seconds is None else now_seconds
    if not isinstance(now, (int, float)) or isinstance(now, bool) or not math.isfinite(now):
        raise ValueError('artifact cleanup time must be finite')

    backup_path = Path(backup_dir).resolve()
    ensure_durable_directory(backup_path)
    # Without advisory locks it is safer to leave debris than risk deleting a
    # file that another process is still writing or verifying.
    if fcntl is None:  # pragma: no cover - scheduled backups are Linux-only
        return []

    effective_uid = os.geteuid()
    removed: list[str] = []
    for candidate in backup_path.iterdir():
        if _OWNED_INCOMPLETE_BACKUP_RE.fullmatch(candidate.name) is None:
            continue
        try:
            with _locked_existing_artifact(
                candidate,
                exclusive=True,
                nonblocking=True,
            ) as metadata:
                if metadata.st_uid != effective_uid:
                    continue
                # ctime cannot be backdated by the unprivileged runtime. Taking
                # the newer timestamp prevents an active/new file with forged
                # mtime from being classified as stale.
                age = now - max(metadata.st_mtime, metadata.st_ctime)
                if age < minimum_age_seconds:
                    continue
                current = candidate.lstat()
                if (
                    not stat.S_ISREG(current.st_mode)
                    or current.st_dev != metadata.st_dev
                    or current.st_ino != metadata.st_ino
                ):
                    continue
                candidate.unlink()
                removed.append(str(candidate))
        except (BlockingIOError, FileNotFoundError, OSError):
            # An active writer/verifier holds the lock, or the entry changed
            # while being inspected. Both cases must fail safe by preserving it.
            continue

    if removed:
        _fsync_directory(backup_path)
    return removed


def file_manifest(root: str | Path) -> dict[str, str]:
    """Return a stable relative-path -> sha256 manifest for all files under root."""
    root_path = Path(root).resolve()
    manifest: dict[str, str] = {}
    if not root_path.exists():
        return manifest

    for path in sorted(
        p for p in root_path.rglob('*')
        if p.is_file() and not p.is_symlink() and _is_within(p, root_path)
    ):
        relative = path.relative_to(root_path).as_posix()
        hasher = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        manifest[relative] = digest
    return manifest


def _timestamp() -> str:
    return f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}_{time.time_ns() % 1_000_000_000:09d}"


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ensure_durable_directory(
    directory: str | Path,
    *,
    mode: int = 0o777,
) -> Path:
    """Create a directory tree and persist every newly added directory entry."""
    path = Path(directory).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = Path(os.path.abspath(path))

    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        if cursor.parent == cursor:
            raise FileNotFoundError(f'cannot find an existing directory parent: {path}')
        missing.append(cursor)
        cursor = cursor.parent
    if cursor.is_symlink() or not cursor.is_dir():
        raise NotADirectoryError(f'directory parent is unsafe: {cursor}')

    for child in reversed(missing):
        try:
            os.mkdir(child, mode)
        except FileExistsError:
            # A concurrent creator is acceptable only when it created a real directory.
            pass
        if child.is_symlink() or not child.is_dir():
            raise NotADirectoryError(f'created directory is unsafe: {child}')
        _fsync_directory(child)
        _fsync_directory(child.parent)
    return path


def create_app_data_backup(
    source_dir: str | Path,
    backup_dir: str | Path,
    *,
    pending: bool = False,
) -> dict:
    """Create a zip archive of app_data in a separate backup directory."""
    source_path = Path(source_dir).resolve()
    backup_path = Path(backup_dir).resolve()
    if not source_path.is_dir():
        raise FileNotFoundError(f'app_data source directory not found: {source_path}')
    if _is_within(backup_path, source_path):
        raise ValueError('backup directory must be outside the app_data source directory')

    ensure_durable_directory(backup_path)
    cleanup_stale_backup_artifacts(backup_path)
    final_archive_path = backup_path / f'{BACKUP_PREFIX}{_timestamp()}{BACKUP_SUFFIX}'
    archive_path = (
        final_archive_path.with_name(f'{final_archive_path.name}.pending')
        if pending
        else final_archive_path
    )
    temporary_path = final_archive_path.with_name(f'{final_archive_path.name}.tmp')
    source_manifest = file_manifest(source_path)
    if BACKUP_MANIFEST_MEMBER in source_manifest:
        raise ValueError(
            f'app_data contains reserved backup metadata path: {BACKUP_MANIFEST_MEMBER}'
        )
    manifest_payload = json.dumps(
        {
            'algorithm': 'sha256',
            'files': source_manifest,
            'version': BACKUP_MANIFEST_VERSION,
        },
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')

    temporary_owned = False
    try:
        with _locked_new_artifact(temporary_path) as temporary_stream:
            temporary_owned = True
            with zipfile.ZipFile(
                temporary_stream,
                'w',
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                for path in sorted(
                    p for p in source_path.rglob('*')
                    if p.is_file() and not p.is_symlink() and _is_within(p, source_path)
                ):
                    if _is_within(path, backup_path):
                        continue
                    zf.write(path, path.relative_to(source_path).as_posix())
                zf.writestr(BACKUP_MANIFEST_MEMBER, manifest_payload)
            temporary_stream.flush()
            _fsync_file(temporary_path)
            os.replace(temporary_path, archive_path)
            temporary_owned = False
            # Persist both the archive inode and its final directory entry before the
            # caller is allowed to verify it or prune an older known-good backup.
            _fsync_file(archive_path)
            _fsync_directory(backup_path)
    finally:
        if temporary_owned:
            temporary_path.unlink(missing_ok=True)
            _fsync_directory(backup_path)

    return {
        'archive_path': str(archive_path),
        'file_count': len(source_manifest),
        'source_manifest': source_manifest,
        'size_bytes': archive_path.stat().st_size,
    }


def prune_app_data_backups(
    backup_dir: str | Path,
    max_backups: int,
    *,
    preserve_archive: str | Path | None = None,
    candidate_verifier=None,
) -> list[str]:
    """Keep the pinned archive plus the newest restorable retention candidates."""
    if not isinstance(max_backups, int) or isinstance(max_backups, bool) or max_backups < 1:
        raise ValueError('max_backups must be a positive integer')

    backup_path = Path(backup_dir).resolve()
    ensure_durable_directory(backup_path)
    preserved: Path | None = None
    if preserve_archive is not None:
        raw_preserved = Path(preserve_archive).expanduser()
        if raw_preserved.is_symlink():
            raise ValueError('preserved backup archive cannot be a symbolic link')
        preserved = raw_preserved.resolve()
        if (
            preserved.parent != backup_path
            or not preserved.is_file()
            or not preserved.name.startswith(BACKUP_PREFIX)
            or not preserved.name.endswith(BACKUP_SUFFIX)
        ):
            raise ValueError('preserved backup archive must be a finalized owned archive')
    archives = sorted(
        (
            path
            for path in backup_path.glob(f'{BACKUP_PREFIX}*{BACKUP_SUFFIX}')
            if path.is_file() and not path.is_symlink() and path.resolve() != preserved
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    remaining_slots = max_backups - (1 if preserved is not None else 0)
    retained: list[Path] = []
    if candidate_verifier is not None:
        # Verify only archives competing for a retention slot. A forged future
        # mtime on a corrupt archive must not evict an older restorable backup.
        # Operational failures propagate before any deletion is attempted.
        for archive in archives:
            if len(retained) >= remaining_slots:
                break
            try:
                verification = candidate_verifier(archive)
                if not isinstance(verification, dict) or verification.get('ok') is not True:
                    raise ValueError(f'backup verification did not succeed: {archive}')
            except (ValueError, zipfile.BadZipFile):
                continue
            retained.append(archive)
    else:
        retained = archives[:remaining_slots]

    retained_set = set(retained)
    removed: list[str] = []
    for archive in archives:
        if archive in retained_set:
            continue
        archive.unlink()
        removed.append(str(archive))
    if removed:
        _fsync_directory(backup_path)
    return removed


def create_and_prune_app_data_backup(
    source_dir: str | Path,
    backup_dir: str | Path,
    max_backups: int,
) -> dict:
    """Create, restore-verify, and only then enforce bounded retention."""
    payload = create_app_data_backup(source_dir, backup_dir, pending=True)
    return verify_and_prune_app_data_backup(payload, backup_dir, max_backups)


def _safe_zip_member(member_name: str) -> Path:
    if not member_name or '\x00' in member_name or '\\' in member_name:
        raise ValueError(f'unsafe archive member path: {member_name}')
    member_path = PurePosixPath(member_name)
    windows_path = PureWindowsPath(member_name)
    if (
        member_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or '..' in member_path.parts
        or member_path.as_posix() != member_name
    ):
        raise ValueError(f'unsafe archive member path: {member_name}')
    return Path(*member_path.parts)


def _validated_manifest(payload: object, *, source: str) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError(f'{source} manifest must be an object')
    validated: dict[str, str] = {}
    for raw_path, raw_digest in payload.items():
        if not isinstance(raw_path, str) or not isinstance(raw_digest, str):
            raise ValueError(f'{source} manifest entries must map paths to SHA-256 strings')
        relative = _safe_zip_member(raw_path)
        normalized = relative.as_posix()
        if normalized == BACKUP_MANIFEST_MEMBER:
            raise ValueError(f'{source} manifest contains the reserved metadata path')
        digest = raw_digest.lower()
        if len(digest) != 64 or any(character not in '0123456789abcdef' for character in digest):
            raise ValueError(f'{source} manifest contains an invalid SHA-256 digest: {raw_path}')
        if normalized in validated:
            raise ValueError(f'{source} manifest contains a duplicate path: {raw_path}')
        validated[normalized] = digest
    return validated


def _read_embedded_manifest(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, str]:
    if info.file_size > _MANIFEST_MAX_BYTES:
        raise ValueError('backup manifest is unreasonably large')
    try:
        payload = json.loads(zf.read(info).decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('backup manifest is not valid UTF-8 JSON') from exc
    if not isinstance(payload, dict):
        raise ValueError('backup manifest root must be an object')
    if payload.get('version') != BACKUP_MANIFEST_VERSION:
        raise ValueError('unsupported backup manifest version')
    if payload.get('algorithm') != 'sha256':
        raise ValueError('unsupported backup manifest hash algorithm')
    return _validated_manifest(payload.get('files'), source='embedded backup')


def _validated_archive_members(
    zf: zipfile.ZipFile,
) -> tuple[list[tuple[zipfile.ZipInfo, Path]], dict[str, str] | None]:
    """Validate every member path/type and load the optional embedded manifest."""
    files: set[str] = set()
    directories: set[str] = set()
    members: list[tuple[zipfile.ZipInfo, Path]] = []
    manifest_info: zipfile.ZipInfo | None = None

    for info in zf.infolist():
        raw_name = info.filename
        is_directory = info.is_dir()
        canonical_name = raw_name[:-1] if is_directory and raw_name.endswith('/') else raw_name
        relative = _safe_zip_member(canonical_name)
        normalized = relative.as_posix()

        unix_mode = info.external_attr >> 16
        file_type = stat.S_IFMT(unix_mode)
        allowed_type = stat.S_IFDIR if is_directory else stat.S_IFREG
        if file_type not in {0, allowed_type}:
            raise ValueError(f'unsupported archive member type: {raw_name}')

        if normalized == BACKUP_MANIFEST_MEMBER:
            if is_directory or manifest_info is not None:
                raise ValueError('backup archive contains duplicate or invalid manifest metadata')
            manifest_info = info
            continue

        if normalized in files or normalized in directories:
            raise ValueError(f'backup archive contains a duplicate path: {raw_name}')
        parents = [parent.as_posix() for parent in relative.parents if parent.as_posix() != '.']
        if any(parent in files for parent in parents):
            raise ValueError(f'backup archive contains a file/directory collision: {raw_name}')

        if is_directory:
            directories.add(normalized)
            continue
        if normalized in directories:
            raise ValueError(f'backup archive contains a file/directory collision: {raw_name}')
        files.add(normalized)
        directories.update(parents)
        members.append((info, relative))

    embedded_manifest = (
        _read_embedded_manifest(zf, manifest_info) if manifest_info is not None else None
    )
    return members, embedded_manifest


def _extract_and_validate_archive(
    archive: Path,
    staging: Path,
    *,
    expected_manifest: dict[str, str] | None,
) -> tuple[dict[str, str], list[str], str]:
    """Fully validate and extract an archive without touching the live target."""
    streamed_manifest: dict[str, str] = {}
    with zipfile.ZipFile(archive) as zf:
        members, embedded_manifest = _validated_archive_members(zf)
        corrupt_member = zf.testzip()
        if corrupt_member is not None:
            raise ValueError(f'backup archive contains a corrupt member: {corrupt_member}')

        for info, relative in members:
            destination = staging / relative
            if not _is_within(destination, staging):
                raise ValueError(f'archive target escapes the staging root: {info.filename}')
            destination.parent.mkdir(parents=True, exist_ok=True)
            hasher = hashlib.sha256()
            with zf.open(info, 'r') as source, destination.open('xb') as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    output.write(chunk)
                    hasher.update(chunk)
            streamed_manifest[relative.as_posix()] = hasher.hexdigest()

    restored_manifest = file_manifest(staging)
    if restored_manifest != streamed_manifest:
        raise ValueError('restored backup manifest does not match the archive contents')
    if embedded_manifest is not None and restored_manifest != embedded_manifest:
        raise ValueError('restored backup manifest does not match the embedded manifest')
    if expected_manifest is not None:
        validated_expected = _validated_manifest(expected_manifest, source='expected source')
        if restored_manifest != validated_expected:
            raise ValueError('restored backup manifest does not match the source manifest')

    sqlite_databases = _verify_restored_sqlite_databases(staging)
    if file_manifest(staging) != restored_manifest:
        raise ValueError('SQLite verification unexpectedly changed the staged backup')
    if embedded_manifest is None:
        raise ValueError('backup archive is missing the embedded manifest')
    # A rename only makes directory entries atomic; it does not make newly written
    # file contents durable. Flush the entire verified tree before commit.
    _fsync_tree(staging)
    manifest_source = 'embedded' if embedded_manifest is not None else 'derived'
    return restored_manifest, sqlite_databases, manifest_source


def _target_restore_path(target_dir: str | Path) -> Path:
    raw_target = Path(target_dir).expanduser()
    if not raw_target.is_absolute():
        raw_target = Path.cwd() / raw_target
    if not raw_target.name:
        raise ValueError('restore target must not be a filesystem root')
    ensure_durable_directory(raw_target.parent)
    target = raw_target.parent.resolve() / raw_target.name
    if target.is_symlink():
        raise ValueError('restore target must not be a symbolic link')
    if target.exists() and not target.is_dir():
        raise NotADirectoryError(f'restore target is not a directory: {target}')
    return target


def _atomic_exchange_directories(left: Path, right: Path) -> bool:
    """Atomically swap directories on Linux; return False when unsupported."""
    if not sys.platform.startswith('linux'):
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, 'renameat2', None)
    if renameat2 is None:
        return False
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(left),
        _AT_FDCWD,
        os.fsencode(right),
        _RENAME_EXCHANGE,
    )
    if result == 0:
        return True
    error_number = ctypes.get_errno()
    if error_number in {
        errno.ENOSYS,
        errno.EINVAL,
        errno.EOPNOTSUPP,
    }:
        return False
    raise OSError(error_number, os.strerror(error_number), str(right))


def _fsync_file(path: Path) -> None:
    """Persist a regular file without following a substituted symbolic link."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f'expected a regular file while syncing: {path}')
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    """Persist directory entry changes without following a symbolic link."""
    flags = (
        os.O_RDONLY
        | getattr(os, 'O_DIRECTORY', 0)
        | getattr(os, 'O_NOFOLLOW', 0)
    )
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError(f'expected a directory while syncing: {path}')
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    """Flush every regular file and directory in a tree, leaves before parents."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f'cannot sync an unsafe restore tree: {root}')

    files: list[Path] = []
    directories: list[Path] = [root]
    for raw_directory, names, filenames in os.walk(root, followlinks=False):
        directory = Path(raw_directory)
        for name in names:
            child = directory / name
            if child.is_symlink() or not child.is_dir():
                raise ValueError(f'cannot sync an unsafe restore directory: {child}')
            directories.append(child)
        for filename in filenames:
            child = directory / filename
            if child.is_symlink() or not child.is_file():
                raise ValueError(f'cannot sync an unsafe restore file: {child}')
            files.append(child)

    for path in files:
        _fsync_file(path)
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        _fsync_directory(directory)


def _manifest_fingerprint(manifest: dict[str, str]) -> str:
    serialized = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()


def _write_marker_payload(transaction_root: Path, payload: dict) -> None:
    """Atomically replace and durably persist a restore transaction marker."""
    marker = transaction_root / RESTORE_TRANSACTION_MARKER
    temporary = transaction_root / (
        f'{RESTORE_TRANSACTION_MARKER}.tmp-{os.getpid()}-{time.time_ns()}'
    )
    serialized = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    try:
        with temporary.open('x', encoding='utf-8') as output:
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, marker)
        _fsync_directory(transaction_root)
        _fsync_directory(transaction_root.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _write_restore_transaction_marker(transaction_root: Path, target: Path) -> None:
    """Write the legacy v1 marker used by already-deployed interrupted restores."""
    marker = transaction_root / RESTORE_TRANSACTION_MARKER
    if marker.exists() or marker.is_symlink():
        raise FileExistsError(f'restore transaction marker already exists: {marker}')
    _write_marker_payload(
        transaction_root,
        {'target_name': target.name, 'version': 1},
    )


def _set_restore_transaction_phase(
    transaction_root: Path,
    target: Path,
    phase: str,
    *,
    staged_manifest: dict[str, str] | None = None,
    strategy: str | None = None,
) -> None:
    if phase not in _RESTORE_PHASES:
        raise ValueError(f'unknown restore transaction phase: {phase}')
    if strategy not in {None, 'install', 'non_exchange', 'exchange'}:
        raise ValueError(f'unknown restore transaction strategy: {strategy}')
    _write_marker_payload(
        transaction_root,
        {
            'phase': phase,
            'staged_manifest_sha256': (
                _manifest_fingerprint(staged_manifest)
                if staged_manifest is not None
                else None
            ),
            'strategy': strategy,
            'target_name': target.name,
            'version': RESTORE_TRANSACTION_VERSION,
        },
    )


def _read_restore_transaction_marker(marker: Path, target: Path) -> dict:
    if marker.is_symlink() or not marker.is_file():
        raise RuntimeError(f'invalid restore transaction marker: {marker}')
    try:
        payload = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f'invalid restore transaction marker: {marker}') from exc
    if payload == {'target_name': target.name, 'version': 1}:
        return payload
    if not isinstance(payload, dict) or set(payload) != {
        'phase',
        'staged_manifest_sha256',
        'strategy',
        'target_name',
        'version',
    }:
        raise RuntimeError(f'restore transaction marker does not match target: {marker}')
    fingerprint = payload.get('staged_manifest_sha256')
    if (
        payload.get('version') != RESTORE_TRANSACTION_VERSION
        or payload.get('target_name') != target.name
        or payload.get('phase') not in _RESTORE_PHASES
        or payload.get('strategy') not in {None, 'install', 'non_exchange', 'exchange'}
        or (
            fingerprint is not None
            and (
                not isinstance(fingerprint, str)
                or len(fingerprint) != 64
                or any(character not in '0123456789abcdef' for character in fingerprint)
            )
        )
    ):
        raise RuntimeError(f'restore transaction marker does not match target: {marker}')

    phase = payload['phase']
    strategy = payload['strategy']
    valid_phase_strategy = (
        (phase in {'extracting', 'prepared'} and strategy is None)
        or (phase in {'exchange_pending', 'exchange_committed'} and strategy == 'exchange')
        or (phase in {'non_exchange_pending', 'previous_moved'} and strategy == 'non_exchange')
        or (phase == 'install_pending' and strategy == 'install')
        or (phase == 'committed' and strategy in {'install', 'non_exchange'})
    )
    if not valid_phase_strategy:
        raise RuntimeError(f'invalid restore transaction phase transition: {marker}')
    if phase != 'extracting' and fingerprint is None:
        raise RuntimeError(f'restore transaction marker has no staged fingerprint: {marker}')
    return payload


def _safe_tree_fingerprint(path: Path) -> str | None:
    """Return a tree fingerprint, or None for an absent/unsafe candidate tree."""
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_dir():
        return None
    for candidate in path.rglob('*'):
        if candidate.is_symlink() or not (candidate.is_dir() or candidate.is_file()):
            return None
    return _manifest_fingerprint(file_manifest(path))


def _remove_restore_transaction(transaction_root: Path) -> None:
    """Remove owned transaction data while keeping its durable marker until last."""
    if transaction_root.is_symlink() or not transaction_root.is_dir():
        raise RuntimeError(f'unsafe restore transaction directory: {transaction_root}')

    for owned_name in ('staged', 'previous'):
        owned_path = transaction_root / owned_name
        if not owned_path.exists() and not owned_path.is_symlink():
            continue
        if owned_path.is_symlink() or not owned_path.is_dir():
            raise RuntimeError(f'unsafe restore transaction entry: {owned_path}')
        shutil.rmtree(owned_path)
        _fsync_directory(transaction_root)

    marker_prefix = f'{RESTORE_TRANSACTION_MARKER}.tmp-'
    for entry in list(transaction_root.iterdir()):
        if entry.name != RESTORE_TRANSACTION_MARKER and not entry.name.startswith(marker_prefix):
            raise RuntimeError(f'unexpected restore transaction entry: {entry}')
        if entry.is_symlink() or not entry.is_file():
            raise RuntimeError(f'unsafe restore transaction marker entry: {entry}')
        entry.unlink()
    _fsync_directory(transaction_root)
    parent = transaction_root.parent
    transaction_root.rmdir()
    _fsync_directory(parent)


def _remove_unmarked_empty_transaction(transaction_root: Path) -> bool:
    """Clean only a provably pre-marker transaction; never trust non-empty orphans."""
    if transaction_root.is_symlink() or not transaction_root.is_dir():
        return False
    marker_prefix = f'{RESTORE_TRANSACTION_MARKER}.tmp-'
    entries = list(transaction_root.iterdir())
    if any(
        not entry.name.startswith(marker_prefix)
        or entry.is_symlink()
        or not entry.is_file()
        for entry in entries
    ):
        return False
    for entry in entries:
        entry.unlink()
    _fsync_directory(transaction_root)
    parent = transaction_root.parent
    transaction_root.rmdir()
    _fsync_directory(parent)
    return True


def _finalize_recovered_commit(
    transaction_root: Path,
    target: Path,
    payload: dict,
) -> None:
    expected = payload['staged_manifest_sha256']
    if _safe_tree_fingerprint(target) != expected:
        raise RuntimeError(
            f'interrupted restore committed target cannot be verified: {transaction_root}'
        )
    # Re-establish directory-entry durability even if the previous process died in
    # the narrow interval between rename/exchange and its fsync calls.
    _fsync_directory(target.parent)
    if transaction_root.is_dir():
        _fsync_directory(transaction_root)
    _remove_restore_transaction(transaction_root)


def _recover_v2_restore(
    transaction_root: Path,
    target: Path,
    payload: dict,
) -> bool:
    """Recover one v2 transaction; return True when a target was installed/recovered."""
    phase = payload['phase']
    strategy = payload['strategy']
    expected = payload['staged_manifest_sha256']
    staging = transaction_root / 'staged'
    previous = transaction_root / 'previous'

    if phase in {'extracting', 'prepared'}:
        # No target mutation can occur before a later phase marker is durable.
        _remove_restore_transaction(transaction_root)
        return False

    target_matches = _safe_tree_fingerprint(target) == expected
    staging_matches = _safe_tree_fingerprint(staging) == expected

    if phase in {'exchange_pending', 'exchange_committed'}:
        if target_matches:
            _finalize_recovered_commit(transaction_root, target, payload)
            return True
        if phase == 'exchange_pending' and staging_matches and target.is_dir():
            # The exchange had not occurred. The original live tree is untouched.
            _remove_restore_transaction(transaction_root)
            return False
        raise RuntimeError(f'cannot determine interrupted exchange state: {transaction_root}')

    if phase == 'committed':
        _finalize_recovered_commit(transaction_root, target, payload)
        return True

    if strategy == 'install':
        if target_matches:
            _finalize_recovered_commit(transaction_root, target, payload)
            return True
        if not target.exists() and staging_matches:
            os.replace(staging, target)
            _fsync_directory(target.parent)
            _set_restore_transaction_phase(
                transaction_root,
                target,
                'committed',
                staged_manifest={path: digest for path, digest in file_manifest(target).items()},
                strategy='install',
            )
            _remove_restore_transaction(transaction_root)
            return True
        raise RuntimeError(f'cannot determine interrupted install state: {transaction_root}')

    if strategy != 'non_exchange':
        raise RuntimeError(f'invalid interrupted restore strategy: {transaction_root}')

    if target_matches:
        _finalize_recovered_commit(transaction_root, target, payload)
        return True
    if previous.exists() or previous.is_symlink():
        if previous.is_symlink() or not previous.is_dir():
            raise RuntimeError(f'unsafe previous restore target: {previous}')
        if target.exists():
            raise RuntimeError(f'interrupted restore has two unverified targets: {transaction_root}')
        os.replace(previous, target)
        _fsync_directory(transaction_root)
        _fsync_directory(target.parent)
        _remove_restore_transaction(transaction_root)
        return True
    if target.is_dir() and staging_matches:
        # The live target was never moved; discard the verified staging copy.
        _remove_restore_transaction(transaction_root)
        return False
    raise RuntimeError(f'interrupted restore has no safe recovery state: {transaction_root}')


def recover_interrupted_restore(target_dir: str | Path) -> list[str]:
    """Recover or safely discard durable restore transactions for one target."""
    raw_target = Path(target_dir).expanduser()
    if not raw_target.is_absolute():
        raw_target = Path.cwd() / raw_target
    if not raw_target.name:
        raise ValueError('restore target must not be a filesystem root')
    parent = raw_target.parent.resolve()
    target = parent / raw_target.name
    if not parent.is_dir():
        return []
    if target.is_symlink():
        raise ValueError('restore target must not be a symbolic link')
    if target.exists() and not target.is_dir():
        raise NotADirectoryError(f'restore target is not a directory: {target}')

    recovered: list[str] = []
    for transaction_root in sorted(parent.glob(f'.{target.name}.restore-*')):
        if transaction_root.is_symlink() or not transaction_root.is_dir():
            raise RuntimeError(f'unsafe restore transaction directory: {transaction_root}')
        marker = transaction_root / RESTORE_TRANSACTION_MARKER
        if not marker.exists() and not marker.is_symlink():
            _remove_unmarked_empty_transaction(transaction_root)
            continue
        payload = _read_restore_transaction_marker(marker, target)
        if payload.get('version') == 1:
            previous = transaction_root / 'previous'
            if not target.exists():
                if not previous.is_dir() or previous.is_symlink():
                    raise RuntimeError(
                        'interrupted restore has no recoverable previous target: '
                        f'{transaction_root}'
                    )
                os.replace(previous, target)
                _fsync_directory(transaction_root)
                _fsync_directory(parent)
                recovered.append(str(target))
            _remove_restore_transaction(transaction_root)
            continue
        if _recover_v2_restore(transaction_root, target, payload):
            recovered.append(str(target))
    return recovered


def _replace_restore_target(
    staging: Path,
    target: Path,
    transaction_root: Path,
    staged_manifest: dict[str, str],
    *,
    overwrite: bool,
) -> str | None:
    """Commit a durable staged directory with a recoverable phase marker."""
    previous = transaction_root / 'previous'
    moved_previous = False
    strategy = 'install'

    if target.exists():
        if not overwrite:
            raise FileExistsError(f'restore target already exists: {target}')
        strategy = 'exchange'
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'exchange_pending',
            staged_manifest=staged_manifest,
            strategy=strategy,
        )
        exchange_committed = _atomic_exchange_directories(staging, target)
        if exchange_committed:
            # RENAME_EXCHANGE changes entries in two directories. Both must be
            # durable before the old tree under `staging` may be removed.
            _fsync_directory(transaction_root)
            _fsync_directory(target.parent)
            _set_restore_transaction_phase(
                transaction_root,
                target,
                'exchange_committed',
                staged_manifest=staged_manifest,
                strategy='exchange',
            )
            try:
                _remove_restore_transaction(transaction_root)
            except OSError:
                return str(transaction_root)
            return None

        strategy = 'non_exchange'
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'non_exchange_pending',
            staged_manifest=staged_manifest,
            strategy=strategy,
        )
        os.replace(target, previous)
        _fsync_directory(transaction_root)
        _fsync_directory(target.parent)
        moved_previous = True
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'previous_moved',
            staged_manifest=staged_manifest,
            strategy=strategy,
        )
    else:
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'install_pending',
            staged_manifest=staged_manifest,
            strategy=strategy,
        )

    try:
        os.replace(staging, target)
        _fsync_directory(target.parent)
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'committed',
            staged_manifest=staged_manifest,
            strategy=strategy,
        )
    except BaseException as commit_error:
        # Roll back only when the staged rename provably did not happen. If the
        # target now contains the new tree, leave both target and previous in the
        # durable transaction for startup recovery to disambiguate by fingerprint.
        if moved_previous and staging.exists() and not target.exists():
            try:
                os.replace(previous, target)
                _fsync_directory(transaction_root)
                _fsync_directory(target.parent)
                _remove_restore_transaction(transaction_root)
            except BaseException as rollback_error:
                raise RuntimeError(
                    'restore commit and rollback both failed; '
                    f'previous data remains at {previous}'
                ) from rollback_error
        raise commit_error

    try:
        _remove_restore_transaction(transaction_root)
    except OSError:
        # The new target is durable. Keep a marker until cleanup can be retried.
        return str(transaction_root)
    return None


def restore_app_data_backup(
    archive_path: str | Path,
    target_dir: str | Path,
    *,
    overwrite: bool = False,
    expected_manifest: dict[str, str] | None = None,
) -> dict:
    """Validate in a sibling directory, then atomically replace target_dir."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f'app_data backup archive not found: {archive}')

    target = _target_restore_path(target_dir)
    if target.exists() and _is_within(archive, target):
        raise ValueError('backup archive must be outside the restore target')
    recover_interrupted_restore(target)

    transaction_root = Path(tempfile.mkdtemp(
        prefix=f'.{target.name}.restore-',
        dir=target.parent,
    ))
    staging = transaction_root / 'staged'
    try:
        _fsync_directory(target.parent)
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'extracting',
        )
        staging.mkdir()
        _fsync_directory(transaction_root)
        restored_manifest, sqlite_databases, manifest_source = _extract_and_validate_archive(
            archive,
            staging,
            expected_manifest=expected_manifest,
        )
        _set_restore_transaction_phase(
            transaction_root,
            target,
            'prepared',
            staged_manifest=restored_manifest,
        )
        cleanup_pending = _replace_restore_target(
            staging,
            target,
            transaction_root,
            restored_manifest,
            overwrite=overwrite,
        )
    except BaseException:
        # Validation failures are safe to discard. Once a commit phase is durable,
        # retain the transaction so startup recovery can distinguish old/new trees.
        if transaction_root.is_dir() and not transaction_root.is_symlink():
            marker = transaction_root / RESTORE_TRANSACTION_MARKER
            if marker.is_file() and not marker.is_symlink():
                try:
                    payload = _read_restore_transaction_marker(marker, target)
                except RuntimeError:
                    payload = None
                if (
                    payload is not None
                    and payload.get('version') == RESTORE_TRANSACTION_VERSION
                    and payload.get('phase') in {'extracting', 'prepared'}
                ):
                    try:
                        _remove_restore_transaction(transaction_root)
                    except OSError:
                        pass
            elif not marker.exists() and not marker.is_symlink():
                try:
                    _remove_unmarked_empty_transaction(transaction_root)
                except OSError:
                    pass
        raise

    return {
        'archive_path': str(archive),
        'target_dir': str(target),
        'restored_file_count': len(restored_manifest),
        'restored_manifest': restored_manifest,
        'sqlite_databases_checked': sqlite_databases,
        'manifest_source': manifest_source,
        'previous_target_cleanup_pending': cleanup_pending,
    }


def _sqlite_database_paths(root: Path) -> list[Path]:
    """Find SQLite main databases by their file header, not their extension."""
    databases: list[Path] = []
    for path in sorted(
        candidate for candidate in root.rglob('*')
        if candidate.is_file()
        and not candidate.is_symlink()
        and _is_within(candidate, root)
    ):
        try:
            with path.open('rb') as source:
                if source.read(16) == b'SQLite format 3\x00':
                    databases.append(path)
        except OSError as exc:
            raise RuntimeError(f'cannot inspect restored file: {path}') from exc
    return databases


def _verify_restored_sqlite_databases(root: Path) -> list[str]:
    """Run SQLite quick_check on isolated copies so staging stays byte-identical."""
    checked: list[str] = []
    for database in _sqlite_database_paths(root):
        with tempfile.TemporaryDirectory(
            prefix='.sqlite-backup-check-',
            dir=root.parent,
        ) as tmp:
            check_root = Path(tmp)
            check_database = check_root / database.name
            shutil.copy2(database, check_database)
            for suffix in ('-wal', '-shm', '-journal'):
                sidecar = database.with_name(f'{database.name}{suffix}')
                if sidecar.is_file() and not sidecar.is_symlink():
                    shutil.copy2(sidecar, check_root / sidecar.name)
            try:
                connection = sqlite3.connect(
                    f'{check_database.resolve().as_uri()}?mode=ro',
                    timeout=5,
                    uri=True,
                )
                try:
                    rows = connection.execute('PRAGMA quick_check').fetchall()
                finally:
                    connection.close()
            except sqlite3.DatabaseError as exc:
                raise ValueError(f'SQLite integrity check failed: {database.name}') from exc
        if rows != [('ok',)]:
            raise ValueError(
                f'SQLite integrity check failed: {database.name}: {rows!r}'
            )
        checked.append(database.relative_to(root).as_posix())
    return checked


def verify_app_data_backup(
    archive_path: str | Path,
    *,
    expected_manifest: dict[str, str] | None = None,
) -> dict:
    """Extract an archive and prove file hashes and SQLite state are restorable."""
    archive = Path(archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f'app_data backup archive not found: {archive}')

    with tempfile.TemporaryDirectory(prefix='app-data-backup-verify-') as tmp:
        restore_root = Path(tmp) / 'restore'
        restore = restore_app_data_backup(
            archive,
            restore_root,
            expected_manifest=expected_manifest,
        )
        restored_manifest = restore['restored_manifest']

    return {
        'ok': True,
        'restored_file_count': len(restored_manifest),
        'restored_manifest': restored_manifest,
        'sqlite_databases_checked': restore['sqlite_databases_checked'],
        'manifest_source': restore['manifest_source'],
    }


def verify_and_finalize_app_data_backup(
    payload: dict,
    backup_dir: str | Path,
    *,
    verifier=None,
) -> dict:
    """Restore-verify a pending archive and only then expose its final .zip name."""
    raw_archive = Path(payload['archive_path']).expanduser()
    if raw_archive.is_symlink():
        raise ValueError('new backup archive cannot be a symbolic link')
    archive = raw_archive.resolve()
    backup_path = Path(backup_dir).resolve()
    if (
        archive.parent != backup_path
        or not archive.name.startswith(BACKUP_PREFIX)
        or not archive.name.endswith((BACKUP_SUFFIX, BACKUP_PENDING_SUFFIX))
    ):
        raise ValueError('new backup archive must belong to the configured backup directory')
    with _locked_existing_artifact(archive, exclusive=False):
        try:
            verify = verifier or verify_app_data_backup
            verification = verify(
                archive,
                expected_manifest=payload['source_manifest'],
            )
        except BaseException:
            # An unverified archive must not count as a backup or trigger retention.
            archive.unlink(missing_ok=True)
            _fsync_directory(backup_path)
            raise

        if archive.name.endswith(BACKUP_PENDING_SUFFIX):
            final_archive = archive.with_name(archive.name[:-len('.pending')])
            if final_archive.exists() or final_archive.is_symlink():
                raise FileExistsError(f'final backup archive already exists: {final_archive}')
            os.replace(archive, final_archive)
            _fsync_file(final_archive)
            _fsync_directory(backup_path)
            archive = final_archive

    payload['archive_path'] = str(archive)
    payload['size_bytes'] = archive.stat().st_size
    payload['verification'] = verification
    return payload


def verify_and_prune_app_data_backup(
    payload: dict,
    backup_dir: str | Path,
    max_backups: int,
) -> dict:
    """Finalize the verified archive, pin it, then prune only older candidates."""
    payload = verify_and_finalize_app_data_backup(payload, backup_dir)
    payload['removed_archives'] = prune_app_data_backups(
        backup_dir,
        max_backups,
        preserve_archive=payload['archive_path'],
        candidate_verifier=verify_app_data_backup,
    )
    return payload


def verify_backup_round_trip(source_dir: str | Path, work_dir: str | Path) -> dict:
    """Create and restore an app_data archive, then compare manifests."""
    work_path = Path(work_dir)
    backup = create_app_data_backup(source_dir, work_path / 'backups')
    verification = verify_app_data_backup(
        backup['archive_path'], expected_manifest=backup['source_manifest'],
    )
    return {
        'ok': verification['ok'],
        'archive_path': backup['archive_path'],
        'source_manifest': backup['source_manifest'],
        'restored_manifest': verification['restored_manifest'],
        'sqlite_databases_checked': verification['sqlite_databases_checked'],
    }
