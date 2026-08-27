"""Initialize persistent storage, drop privileges, and supervise app services."""
from __future__ import annotations

import os
import pwd
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.app_data_backup import (  # noqa: E402
    ensure_durable_directory,
    recover_interrupted_restore,
)

TEMPLATE_PATH = ROOT / 'nginx.railway.conf'
RENDERED_PATH = Path('/tmp/insight-nginx.conf')
NGINX_TEMP_ROOT = Path('/tmp/insight-nginx')
PERSIST_ROOT = Path('/app/persist')
PROC_MOUNTINFO = Path('/proc/self/mountinfo')
PERSIST_SUBDIRECTORIES = ('data', 'backups', 'cache', 'logs')
PERSIST_NESTED_DIRECTORIES = ('data/home', 'data/chroma_db')
FULL_STACK_FRONTEND_URL = 'http://127.0.0.1:3000/'
RUNTIME_USER = 'appuser'
PERSISTENCE_ROLES = frozenset({'backend', 'full-stack'})
RUNTIME_ROLE = 'full-stack'
PROCESSES: list[subprocess.Popen] = []
OPTIONAL_PROCESSES: set[int] = set()
PROCESS_ROLES: dict[int, str] = {}
STOP_REQUESTED = threading.Event()
PLATFORM_SHUTDOWN_TIMEOUT_SECONDS = 630
FORCE_KILL_TIMEOUT_SECONDS = 5


def _public_port() -> int:
    raw = os.getenv('PORT', '8080')
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError('PORT must be an integer') from exc
    if not 1024 <= port <= 65535:
        raise RuntimeError('PORT must be between 1024 and 65535 for the non-root runtime')
    return port


def _render_nginx_config(port: int) -> Path:
    NGINX_TEMP_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    NGINX_TEMP_ROOT.chmod(0o700)
    for name in ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
        (NGINX_TEMP_ROOT / name).mkdir(mode=0o700, exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('${PORT}') != 1:
        raise RuntimeError('nginx template must contain exactly one ${PORT} placeholder')
    if '${NGINX_TEMP_ROOT}' not in template:
        raise RuntimeError('nginx template must contain ${NGINX_TEMP_ROOT}')
    rendered = template.replace('${PORT}', str(port)).replace(
        '${NGINX_TEMP_ROOT}', str(NGINX_TEMP_ROOT),
    )
    RENDERED_PATH.write_text(rendered, encoding='utf-8')
    return RENDERED_PATH


def _chown_without_following(path: Path, uid: int, gid: int) -> None:
    os.chown(path, uid, gid, follow_symlinks=False)


def _decode_mountinfo_path(raw_path: str) -> str:
    """Decode the octal escapes used by Linux /proc/*/mountinfo paths."""
    return re.sub(
        r'\\([0-7]{3})',
        lambda match: chr(int(match.group(1), 8)),
        raw_path,
    )


def _is_exact_mount(path: Path) -> bool:
    """Return True only when path itself is a mount point, including bind mounts."""
    resolved = str(path.resolve(strict=False))
    try:
        lines = PROC_MOUNTINFO.read_text(encoding='utf-8').splitlines()
    except OSError:
        return path.exists() and path.is_mount()

    for line in lines:
        fields = line.split()
        if len(fields) >= 5 and _decode_mountinfo_path(fields[4]) == resolved:
            return True
    return False


def _require_production_persistent_mount(root: Path = PERSIST_ROOT) -> None:
    """Fail before creating directories when production storage is not mounted."""
    if (os.getenv('FLASK_ENV') or '').strip().lower() != 'production':
        return
    if not _is_exact_mount(root):
        raise RuntimeError(
            f'production persistent storage must be an exact mounted volume: {root}'
        )
    if (os.getenv('RAILWAY_ENVIRONMENT_ID') or '').strip():
        railway_mount = (os.getenv('RAILWAY_VOLUME_MOUNT_PATH') or '').strip()
        if not railway_mount or Path(railway_mount).resolve(strict=False) != root:
            raise RuntimeError(
                'RAILWAY_VOLUME_MOUNT_PATH must be /app/persist in production'
            )


def _initialize_persistent_storage(
    root: Path = PERSIST_ROOT,
    *,
    uid: int,
    gid: int,
) -> None:
    """Create and own the one mounted tree without traversing symlink targets."""
    if not root.is_absolute():
        raise RuntimeError('persistent storage root must be absolute')
    ensure_durable_directory(root, mode=0o750)
    if stat.S_ISLNK(root.lstat().st_mode):
        raise RuntimeError('persistent storage root cannot be a symlink')

    for name in PERSIST_SUBDIRECTORIES:
        child = root / name
        ensure_durable_directory(child, mode=0o750)
        if stat.S_ISLNK(child.lstat().st_mode):
            raise RuntimeError(f'persistent storage directory cannot be a symlink: {child}')
    for name in PERSIST_NESTED_DIRECTORIES:
        child = root / name
        ensure_durable_directory(child, mode=0o750)
        if stat.S_ISLNK(child.lstat().st_mode):
            raise RuntimeError(f'persistent storage directory cannot be a symlink: {child}')

    for current_root, directories, files in os.walk(root, topdown=False, followlinks=False):
        current = Path(current_root)
        for name in (*directories, *files):
            _chown_without_following(current / name, uid, gid)
        _chown_without_following(current, uid, gid)


def _prepare_and_drop_privileges() -> None:
    """Prepare role-owned storage as needed, then permanently become appuser."""
    requires_persistence = RUNTIME_ROLE in PERSISTENCE_ROLES
    if requires_persistence:
        if PERSIST_ROOT.resolve(strict=False) != PERSIST_ROOT:
            raise RuntimeError('app persistent storage must be mounted at /app/persist')
        _require_production_persistent_mount(PERSIST_ROOT)

    try:
        account = pwd.getpwnam(RUNTIME_USER)
    except KeyError as exc:
        if os.geteuid() == 0:
            raise RuntimeError(f'runtime user does not exist: {RUNTIME_USER}') from exc
        # Local developer execution is already non-root; Docker always has appuser.
        account = None

    if requires_persistence:
        # Recovery must run before either privilege branch can create a new empty
        # data directory over an interrupted non-exchange restore.
        recover_interrupted_restore(PERSIST_ROOT / 'data')

    if os.geteuid() == 0:
        assert account is not None
        if requires_persistence:
            _initialize_persistent_storage(
                PERSIST_ROOT,
                uid=account.pw_uid,
                gid=account.pw_gid,
            )
        os.initgroups(account.pw_name, account.pw_gid)
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
        os.environ['HOME'] = account.pw_dir or '/app'
    elif requires_persistence:
        for name in PERSIST_SUBDIRECTORIES:
            directory = PERSIST_ROOT / name
            directory.mkdir(mode=0o750, parents=True, exist_ok=True)
            if not os.access(directory, os.W_OK | os.X_OK):
                raise PermissionError(f'persistent storage is not writable: {directory}')

    if os.geteuid() == 0:
        raise RuntimeError('refusing to start application services as root')
    os.umask(0o027)


def _backup_enabled() -> bool:
    raw = os.getenv('AUTO_BACKUP_ENABLED', 'false').strip().lower()
    if raw not in {'true', 'false'}:
        raise RuntimeError('AUTO_BACKUP_ENABLED must be true or false')
    return raw == 'true'


def _request_stop(*_: object) -> None:
    """Signal handlers only set state; child waits happen in normal control flow."""
    STOP_REQUESTED.set()


def _signal_process_group(process: subprocess.Popen, signal_number: int) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        return


def _resume_backend_writer_groups() -> None:
    """Recover a backend stranded by an interrupted SIGSTOP backup snapshot."""
    for process in PROCESSES:
        if PROCESS_ROLES.get(process.pid) == 'backend':
            _signal_process_group(process, signal.SIGCONT)


def _bounded_int_environment(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f'{name} must be an integer') from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f'{name} must be between {minimum} and {maximum}')
    return value


def _validate_shutdown_timeout_environment() -> None:
    """Reject every shutdown-related timeout before any child can launch."""
    _bounded_int_environment(
        'BACKUP_SHUTDOWN_TIMEOUT_SECONDS',
        10,
        minimum=1,
        maximum=30,
    )
    _bounded_int_environment(
        'BACKEND_GRACEFUL_TIMEOUT_SECONDS',
        600,
        minimum=10,
        maximum=600,
    )
    _bounded_int_environment(
        'NGINX_DRAIN_TIMEOUT_SECONDS',
        605,
        minimum=5,
        maximum=605,
    )
    _bounded_int_environment(
        'PROCESS_SHUTDOWN_TIMEOUT_SECONDS',
        605,
        minimum=5,
        maximum=605,
    )


def _wait_for_processes(
    processes: list[subprocess.Popen],
    timeout_seconds: float,
) -> list[subprocess.Popen]:
    """Wait against one shared deadline and return processes still running."""
    deadline = time.monotonic() + timeout_seconds
    for process in processes:
        if process.poll() is not None:
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            break
    return [process for process in processes if process.poll() is None]


def _stop_all() -> None:
    shutdown_started = time.monotonic()
    graceful_deadline = (
        shutdown_started
        + PLATFORM_SHUTDOWN_TIMEOUT_SECONDS
        - FORCE_KILL_TIMEOUT_SECONDS
    )
    # Let the backup daemon unwind its SIGSTOP snapshot context before anything
    # else resumes or terminates the backend. A bounded kill remains as a failsafe.
    backup_processes = [
        process
        for process in PROCESSES
        if PROCESS_ROLES.get(process.pid) == 'backup'
    ]
    for process in backup_processes:
        _signal_process_group(process, signal.SIGTERM)
    remaining_backup = _wait_for_processes(
        backup_processes,
        _bounded_int_environment(
            'BACKUP_SHUTDOWN_TIMEOUT_SECONDS',
            10,
            minimum=1,
            maximum=30,
        ),
    )
    for process in remaining_backup:
        _signal_process_group(process, signal.SIGKILL)
    _wait_for_processes(remaining_backup, 5)

    # If the daemon needed the kill fallback, ensure writers cannot remain stopped.
    _resume_backend_writer_groups()

    # Stop accepting public traffic first. Signal application processes only
    # after nginx receives SIGQUIT, then drain both groups against one shared
    # deadline. Waiting for nginx before signalling the applications would make
    # the two grace periods additive and could exceed the platform's 630-second
    # shutdown window.
    nginx_processes = [
        process
        for process in PROCESSES
        if PROCESS_ROLES.get(process.pid) == 'nginx'
    ]
    for process in nginx_processes:
        _signal_process_group(process, signal.SIGQUIT)

    application_processes = [
        process
        for process in reversed(PROCESSES)
        if PROCESS_ROLES.get(process.pid) not in {'nginx', 'backup'}
    ]
    for process in application_processes:
        _signal_process_group(process, signal.SIGTERM)

    nginx_timeout = _bounded_int_environment(
        'NGINX_DRAIN_TIMEOUT_SECONDS',
        605,
        minimum=5,
        maximum=605,
    )
    application_timeout = _bounded_int_environment(
        'PROCESS_SHUTDOWN_TIMEOUT_SECONDS',
        605,
        minimum=5,
        maximum=605,
    )
    shared_timeout = min(
        max(nginx_timeout, application_timeout),
        max(0.0, graceful_deadline - time.monotonic()),
    )
    remaining = _wait_for_processes(
        [*nginx_processes, *application_processes],
        shared_timeout,
    )
    for process in remaining:
        _signal_process_group(process, signal.SIGKILL)
    final_wait = min(
        FORCE_KILL_TIMEOUT_SECONDS,
        max(
            0.0,
            shutdown_started
            + PLATFORM_SHUTDOWN_TIMEOUT_SECONDS
            - time.monotonic(),
        ),
    )
    _wait_for_processes(remaining, final_wait)


def _spawn(
    command: list[str],
    cwd: Path,
    *,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.Popen:
    environment = os.environ.copy()
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        start_new_session=True,
    )


def _backend_command() -> list[str]:
    bind_host = os.getenv('BACKEND_BIND_HOST', '127.0.0.1')
    if bind_host not in {'127.0.0.1', '0.0.0.0'}:
        raise RuntimeError('BACKEND_BIND_HOST must be 127.0.0.1 or 0.0.0.0')
    graceful_timeout = _bounded_int_environment(
        'BACKEND_GRACEFUL_TIMEOUT_SECONDS',
        600,
        minimum=10,
        maximum=600,
    )
    return [
        'gunicorn', '--workers=2', '--threads=4', '--timeout=600',
        f'--graceful-timeout={graceful_timeout}',
        f'--bind={bind_host}:5001', 'app:app',
    ]


def _register_process(role: str, process: subprocess.Popen) -> None:
    PROCESSES.append(process)
    PROCESS_ROLES[process.pid] = role


def _start_backend_with_optional_backup(
    *,
    frontend_readiness_url: str | None = None,
) -> None:
    backend_environment = None
    if frontend_readiness_url:
        backend_environment = {
            'FULL_STACK_FRONTEND_READINESS_URL': frontend_readiness_url,
        }
    backend = _spawn(
        _backend_command(),
        ROOT,
        extra_environment=backend_environment,
    )
    _register_process('backend', backend)
    if _backup_enabled():
        backup = _spawn(
            ['python', 'scripts/backup_app_data.py', 'daemon'],
            ROOT,
            extra_environment={'APP_BACKEND_PID': str(backend.pid)},
        )
        _register_process('backup', backup)
        OPTIONAL_PROCESSES.add(backup.pid)


def _start_services(role: str) -> None:
    if role in {'backend', 'full-stack'}:
        _start_backend_with_optional_backup(
            frontend_readiness_url=(
                FULL_STACK_FRONTEND_URL if role == 'full-stack' else None
            ),
        )
    if role in {'frontend', 'full-stack'}:
        frontend_host = os.getenv('FRONTEND_BIND_HOST', '127.0.0.1')
        if frontend_host not in {'127.0.0.1', '0.0.0.0'}:
            raise RuntimeError('FRONTEND_BIND_HOST must be 127.0.0.1 or 0.0.0.0')
        _register_process('frontend', _spawn([
            'node', 'node_modules/next/dist/bin/next', 'start',
            '--hostname', frontend_host, '--port', '3000',
        ], ROOT / 'frontend'))
    if role == 'full-stack':
        nginx_config = _render_nginx_config(_public_port())
        _register_process('nginx', _spawn(
            ['nginx', '-c', str(nginx_config), '-g', 'daemon off;'], ROOT,
        ))


def _probe_frontend_ready(url: str = FULL_STACK_FRONTEND_URL) -> bool:
    """Bounded internal probe used to turn a hung Next.js child into a restart."""
    request = urllib.request.Request(url, method='GET')
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            response.read(1)
            return 200 <= response.status < 400
    except (OSError, urllib.error.URLError, ValueError):
        return False


def main(argv: list[str] | None = None) -> int:
    global RUNTIME_ROLE
    args = list(sys.argv[1:] if argv is None else argv)
    role = args[0] if args else 'full-stack'
    if len(args) > 1 or role not in {'backend', 'frontend', 'full-stack'}:
        raise ValueError('role must be one of: backend, frontend, full-stack')

    STOP_REQUESTED.clear()
    PROCESSES.clear()
    OPTIONAL_PROCESSES.clear()
    PROCESS_ROLES.clear()
    RUNTIME_ROLE = role
    _validate_shutdown_timeout_environment()
    _prepare_and_drop_privileges()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    try:
        _start_services(role)
        watchdog_enabled = role in {'frontend', 'full-stack'}
        watchdog_failures = 0
        watchdog_next_probe = time.monotonic() + _bounded_int_environment(
            'FRONTEND_WATCHDOG_STARTUP_SECONDS',
            120,
            minimum=1,
            maximum=600,
        )
        watchdog_interval = _bounded_int_environment(
            'FRONTEND_WATCHDOG_INTERVAL_SECONDS',
            10,
            minimum=1,
            maximum=60,
        )
        watchdog_failure_threshold = _bounded_int_environment(
            'FRONTEND_WATCHDOG_FAILURE_THRESHOLD',
            3,
            minimum=1,
            maximum=12,
        )
        while not STOP_REQUESTED.is_set():
            for process in list(PROCESSES):
                return_code = process.poll()
                if return_code is None:
                    continue
                if process.pid in OPTIONAL_PROCESSES:
                    _resume_backend_writer_groups()
                    print(
                        f'optional backup daemon exited: pid={process.pid} code={return_code}',
                        file=sys.stderr,
                        flush=True,
                    )
                    OPTIONAL_PROCESSES.discard(process.pid)
                    PROCESS_ROLES.pop(process.pid, None)
                    PROCESSES.remove(process)
                    continue
                print(
                    f'app child exited unexpectedly: pid={process.pid} code={return_code}',
                    file=sys.stderr,
                    flush=True,
                )
                return return_code or 1

            now = time.monotonic()
            if watchdog_enabled and now >= watchdog_next_probe:
                if _probe_frontend_ready():
                    watchdog_failures = 0
                else:
                    watchdog_failures += 1
                    print(
                        'frontend watchdog probe failed: '
                        f'{watchdog_failures}/{watchdog_failure_threshold}',
                        file=sys.stderr,
                        flush=True,
                    )
                    if watchdog_failures >= watchdog_failure_threshold:
                        return 1
                watchdog_next_probe = now + watchdog_interval
            time.sleep(0.5)
        return 0
    finally:
        _stop_all()


if __name__ == '__main__':
    raise SystemExit(main())
