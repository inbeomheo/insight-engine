"""Run the Insight Engine background scheduler as a dedicated worker process."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import sys
import time


TRUTHY = {'1', 'true', 'yes', 'on'}


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in TRUTHY


def _heartbeat_path() -> Path:
    return Path(os.getenv('SCHEDULER_HEARTBEAT_FILE', '/tmp/insight-engine-scheduler.heartbeat'))


def _write_heartbeat(path: Path | None = None) -> None:
    target = path or _heartbeat_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), encoding='utf-8')


def _scheduler_running() -> bool:
    from services.data import scheduler_worker

    scheduler = scheduler_worker._scheduler
    return bool(scheduler is not None and scheduler.running)


def main() -> int:
    if not _truthy(os.getenv('SCHEDULER_ENABLED') or 'true'):
        print('SCHEDULER_ENABLED must be true for the scheduler worker process', file=sys.stderr)
        return 1

    # Importing app creates the Flask application and starts scheduler_worker.start_scheduler(app).
    import app as _app_module  # noqa: F401

    if not _scheduler_running():
        print('scheduler did not start; refusing to run a no-op worker', file=sys.stderr)
        return 1

    stop_requested = False

    def _request_stop(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    heartbeat = _heartbeat_path()
    try:
        while not stop_requested:
            if not _scheduler_running():
                print('scheduler stopped unexpectedly', file=sys.stderr)
                return 1
            _write_heartbeat(heartbeat)
            time.sleep(30)
        return 0
    finally:
        from services.data.scheduler_worker import stop_scheduler

        stop_scheduler()


if __name__ == '__main__':
    raise SystemExit(main())
