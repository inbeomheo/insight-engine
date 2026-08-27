"""Create, restore, or rehearse app_data volume backups."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
import signal
import stat
import sys
import threading
import time
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.app_data_backup import (  # noqa: E402
    cleanup_stale_backup_artifacts,
    create_app_data_backup,
    ensure_durable_directory,
    restore_app_data_backup,
    verify_app_data_backup,
    verify_and_finalize_app_data_backup,
    verify_and_prune_app_data_backup,
)


_STOP = threading.Event()
DEFAULT_INITIAL_DELAY_SECONDS = 300
DAEMON_FATAL_EXIT_CODE = 70
DAEMON_LOCK_NAME = '.insight-engine-backup-daemon.lock'


class _DaemonStopRequested(Exception):
    """Internal control flow for a clean signal-driven daemon shutdown."""


@contextmanager
def _single_backup_daemon(backup_dir: str) -> Iterator[None]:
    """Hold one non-inheritable lock for the daemon's entire lifetime."""
    backup_path = Path(backup_dir).resolve()
    ensure_durable_directory(backup_path)
    lock_path = backup_path / DAEMON_LOCK_NAME
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, 'O_CLOEXEC', 0)
        | getattr(os, 'O_NOFOLLOW', 0)
    )
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise PermissionError('backup daemon lock must be a same-UID regular file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('another app-data backup daemon is already running') from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(descriptor)


def _json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _bounded_positive_int(raw: str, name: str, *, maximum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be an integer') from exc
    if not 1 <= value <= maximum:
        raise ValueError(f'{name} must be between 1 and {maximum}')
    return value


def _process_group_states(process_group_id: int) -> list[str]:
    """Return Linux process states for all live members of a process group."""
    states: list[str] = []
    for stat_path in Path('/proc').glob('[0-9]*/stat'):
        try:
            stat = stat_path.read_text(encoding='utf-8')
            fields = stat[stat.rfind(') ') + 2:].split()
            state, process_group = fields[0], int(fields[2])
        except (OSError, ValueError, IndexError):
            continue
        if process_group == process_group_id and state != 'Z':
            states.append(state)
    return states


def _wait_until_process_group_stopped(
    process_group_id: int,
    *,
    timeout_seconds: float = 5,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        states = _process_group_states(process_group_id)
        if states and all(state in {'T', 't'} for state in states):
            return
        time.sleep(0.02)
    raise TimeoutError('backend writer process group did not stop in time')


@contextmanager
def _quiesce_writer_process_group(
    writer_pid: int,
    max_seconds: int,
) -> Iterator[None]:
    """Bound a Linux SIGSTOP snapshot window and always resume the backend."""
    if not sys.platform.startswith('linux'):
        raise RuntimeError('consistent scheduled backups require Linux process groups')
    if writer_pid < 2 or writer_pid == os.getpid():
        raise ValueError('APP_BACKEND_PID must identify the backend group leader')

    process_group_id = os.getpgid(writer_pid)
    if process_group_id != writer_pid:
        raise ValueError('APP_BACKEND_PID must identify the backend process-group leader')
    if process_group_id == os.getpgrp():
        raise ValueError('backup daemon cannot stop its own process group')

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    stopped = False
    resumed = False

    def resume_writer() -> None:
        nonlocal resumed
        if not stopped or resumed:
            return
        try:
            os.killpg(process_group_id, signal.SIGCONT)
        except ProcessLookupError:
            pass
        resumed = True

    def timeout_and_resume(*_: object) -> None:
        # A signal can arrive immediately before the context manager's finally
        # block. Resume from the handler itself so that race cannot strand writers.
        try:
            resume_writer()
        finally:
            raise TimeoutError('app-data backup exceeded the writer quiesce timeout')

    try:
        os.killpg(process_group_id, signal.SIGSTOP)
        stopped = True
        _wait_until_process_group_stopped(process_group_id)
        signal.signal(signal.SIGALRM, timeout_and_resume)
        signal.setitimer(signal.ITIMER_REAL, max_seconds)
        yield
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
        finally:
            try:
                resume_writer()
            finally:
                signal.signal(signal.SIGALRM, previous_handler)
                if previous_timer != (0.0, 0.0):
                    signal.setitimer(signal.ITIMER_REAL, *previous_timer)


def _run_consistent_backup(
    source: str,
    backup_dir: str,
    max_backups: int,
    *,
    writer_pid: int,
    max_quiesce_seconds: int,
) -> dict:
    # Only archive creation runs while writers are stopped. Restore verification and
    # retention operate on the immutable archive after the backend is resumed.
    backup_path = Path(backup_dir).resolve()
    ensure_durable_directory(backup_path)
    previous_archives = set(backup_path.glob('app_data_backup_*.zip'))
    previous_pending = set(backup_path.glob('app_data_backup_*.zip.pending'))
    try:
        with _quiesce_writer_process_group(writer_pid, max_quiesce_seconds):
            payload = create_app_data_backup(source, backup_dir, pending=True)
    except BaseException:
        # SIGALRM can land after the atomic rename but before the helper returns.
        # Never leave that interrupted, unverified archive looking successful.
        for archive in set(backup_path.glob('app_data_backup_*.zip')) - previous_archives:
            archive.unlink(missing_ok=True)
        for archive in (
            set(backup_path.glob('app_data_backup_*.zip.pending')) - previous_pending
        ):
            archive.unlink(missing_ok=True)
        raise
    return verify_and_prune_app_data_backup(payload, backup_dir, max_backups)


def _run_backup_with_retry(
    source: str,
    backup_dir: str,
    max_backups: int,
    *,
    writer_pid: int,
    max_quiesce_seconds: int,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        if _STOP.is_set():
            raise _DaemonStopRequested
        try:
            return _run_consistent_backup(
                source,
                backup_dir,
                max_backups,
                writer_pid=writer_pid,
                max_quiesce_seconds=max_quiesce_seconds,
            )
        except Exception as exc:
            last_error = exc
            print(f'app-data backup attempt {attempt}/3 failed: {exc}', file=sys.stderr, flush=True)
            if attempt < 3 and _STOP.wait(min(5 * attempt, 10)):
                raise _DaemonStopRequested from exc
    raise RuntimeError('app-data backup failed after 3 attempts') from last_error


def _request_stop(*_: object) -> None:
    _STOP.set()


def _create_verified_backup(source: str, backup_dir: str) -> dict:
    """Create and verify the exact persisted archive returned to the operator."""
    payload = create_app_data_backup(source, backup_dir, pending=True)
    return verify_and_finalize_app_data_backup(
        payload,
        backup_dir,
        verifier=verify_app_data_backup,
    )


def _run_daemon_loop(
    args,
    *,
    interval_hours: int,
    initial_delay_seconds: int,
    max_backups: int,
    writer_pid: int,
    max_quiesce_seconds: int,
) -> int:
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    print(
        f'app-data backup daemon waiting {initial_delay_seconds}s before first snapshot',
        file=sys.stderr,
        flush=True,
    )
    if _STOP.wait(initial_delay_seconds):
        return 0
    cycles = 0
    while not _STOP.is_set():
        try:
            payload = _run_backup_with_retry(
                args.source,
                args.backup_dir,
                max_backups,
                writer_pid=writer_pid,
                max_quiesce_seconds=max_quiesce_seconds,
            )
        except _DaemonStopRequested:
            return 0
        except Exception as exc:
            print(
                'app-data backup daemon fatal: '
                f'{exc}; exiting with code {DAEMON_FATAL_EXIT_CODE} for supervisor detection',
                file=sys.stderr,
                flush=True,
            )
            return DAEMON_FATAL_EXIT_CODE
        _json(payload)
        cycles += 1
        if args.max_cycles is not None and cycles >= args.max_cycles:
            break
        _STOP.wait(interval_hours * 60 * 60)
    return 0


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

    daemon = subparsers.add_parser('daemon')
    daemon.add_argument('--source', default=os.getenv('APP_DATA_DIR', '/app/persist/data'))
    daemon.add_argument(
        '--backup-dir', default=os.getenv('APP_DATA_BACKUP_DIR', '/app/persist/backups'),
    )
    daemon.add_argument('--interval-hours', default=os.getenv('AUTO_BACKUP_INTERVAL_HOURS', '24'))
    daemon.add_argument(
        '--initial-delay-seconds',
        default=os.getenv('BACKUP_INITIAL_DELAY_SECONDS', str(DEFAULT_INITIAL_DELAY_SECONDS)),
    )
    daemon.add_argument('--max-backups', default=os.getenv('MAX_BACKUPS', '30'))
    daemon.add_argument('--writer-pid', default=os.getenv('APP_BACKEND_PID'))
    daemon.add_argument(
        '--max-quiesce-seconds',
        default=os.getenv('BACKUP_QUIESCE_TIMEOUT_SECONDS', '600'),
    )
    daemon.add_argument('--max-cycles', type=int, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    if args.command == 'backup':
        _json(_create_verified_backup(args.source, args.backup_dir))
        return 0

    if args.command == 'restore':
        _json(restore_app_data_backup(args.archive, args.target, overwrite=args.overwrite))
        return 0

    if args.command == 'rehearse':
        backup_payload = _create_verified_backup(args.source, args.backup_dir)
        verification = backup_payload['verification']
        payload = {
            'ok': verification['ok'],
            'archive_path': backup_payload['archive_path'],
            'source_manifest': backup_payload['source_manifest'],
            'restored_manifest': verification['restored_manifest'],
            'sqlite_databases_checked': verification['sqlite_databases_checked'],
        }
        _json(payload)
        return 0 if payload['ok'] else 1

    if args.command == 'daemon':
        _STOP.clear()
        interval_hours = _bounded_positive_int(
            args.interval_hours, 'AUTO_BACKUP_INTERVAL_HOURS', maximum=720,
        )
        initial_delay_seconds = _bounded_positive_int(
            args.initial_delay_seconds,
            'BACKUP_INITIAL_DELAY_SECONDS',
            maximum=86_400,
        )
        max_backups = _bounded_positive_int(args.max_backups, 'MAX_BACKUPS', maximum=10_000)
        writer_pid = _bounded_positive_int(
            args.writer_pid, 'APP_BACKEND_PID', maximum=2_147_483_647,
        )
        max_quiesce_seconds = _bounded_positive_int(
            args.max_quiesce_seconds,
            'BACKUP_QUIESCE_TIMEOUT_SECONDS',
            maximum=3_600,
        )
        if args.max_cycles is not None and args.max_cycles < 1:
            raise ValueError('max-cycles must be positive')
        with _single_backup_daemon(args.backup_dir):
            cleanup_stale_backup_artifacts(args.backup_dir)
            return _run_daemon_loop(
                args,
                interval_hours=interval_hours,
                initial_delay_seconds=initial_delay_seconds,
                max_backups=max_backups,
                writer_pid=writer_pid,
                max_quiesce_seconds=max_quiesce_seconds,
            )

    return 2


if __name__ == '__main__':
    raise SystemExit(main())
