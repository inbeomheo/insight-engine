"""Run the Playwright smoke test with managed local backend/frontend servers."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = os.name == 'nt'
BACKEND_URL = 'http://127.0.0.1:5001'
FRONTEND_URL = 'http://127.0.0.1:3000'


def _url_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def _wait_for(url: str, timeout: int) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _url_ready(url):
            return
        time.sleep(1)
    raise RuntimeError(f'{url} did not become ready within {timeout}s')


def _popen(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    kwargs = {
        'cwd': str(cwd),
        'env': env,
    }
    if IS_WINDOWS:
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True
    return subprocess.Popen(cmd, **kwargs)


def _stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.run(
            ['taskkill', '/PID', str(proc.pid), '/T', '/F'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> int:
    backend = None
    frontend = None
    env = os.environ.copy()
    env.update({
        'BROWSERSLIST_IGNORE_OLD_DATA': 'true',
        'NEXT_BACKEND_URL': BACKEND_URL,
        'NEXT_TELEMETRY_DISABLED': '1',
        'PLAYWRIGHT_MANAGED_SERVERS': '1',
        'SCHEDULER_ENABLED': 'false',
        'SUPABASE_ANON_KEY': '',
        'SUPABASE_URL': '',
    })

    try:
        if not _url_ready(f'{BACKEND_URL}/health'):
            backend = _popen([sys.executable, 'app.py'], ROOT, env)
        if not _url_ready(f'{FRONTEND_URL}/'):
            npm = 'npm.cmd' if IS_WINDOWS else 'npm'
            frontend = _popen(
                [npm, 'run', 'dev', '--', '--hostname', '127.0.0.1', '--port', '3000'],
                ROOT / 'frontend',
                env,
            )

        _wait_for(f'{BACKEND_URL}/health', 120)
        _wait_for(f'{FRONTEND_URL}/', 120)

        npx = 'npx.cmd' if IS_WINDOWS else 'npx'
        result = subprocess.run(
            [
                npx,
                'playwright',
                'test',
                'main-page/ci-smoke.spec.ts',
                '--project=no-auth-chromium',
            ],
            cwd=ROOT / 'tests' / 'e2e',
            env=env,
            check=False,
            timeout=180,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print('E2E smoke timed out after 180s', file=sys.stderr)
        return 124
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        _stop(frontend)
        _stop(backend)


if __name__ == '__main__':
    raise SystemExit(main())
