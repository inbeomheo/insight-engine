"""Small in-process background job registry for long HTTP requests."""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

JobCallable = Callable[[], Dict[str, Any]]
SuccessCallback = Callable[[Dict[str, Any]], None]

_MAX_JOBS = int(os.getenv("BACKGROUND_JOB_MAX_ITEMS", "200"))
_JOB_TTL_SECONDS = int(os.getenv("BACKGROUND_JOB_TTL_SECONDS", str(6 * 60 * 60)))
_WORKERS = max(1, int(os.getenv("BACKGROUND_JOB_WORKERS", "2")))

_executor = ThreadPoolExecutor(max_workers=_WORKERS, thread_name_prefix="insight-job")
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_step(step_id: str) -> Dict[str, Any]:
    return {"id": step_id, "status": "queued", "error": None}


def _snapshot(job: Dict[str, Any]) -> Dict[str, Any]:
    snap = deepcopy(job)
    for key in list(snap):
        if key == "owner_user_id" or key.startswith("_"):
            snap.pop(key, None)
    return snap


def _cleanup_locked(now: Optional[float] = None) -> None:
    now = now or time.time()
    removable = [
        job_id
        for job_id, job in _jobs.items()
        if job.get("_finished_monotonic")
        and now - float(job["_finished_monotonic"]) > _JOB_TTL_SECONDS
    ]
    for job_id in removable:
        _jobs.pop(job_id, None)

    if len(_jobs) <= _MAX_JOBS:
        return

    finished = sorted(
        (
            (job.get("_finished_monotonic") or 0.0, job_id)
            for job_id, job in _jobs.items()
            if job.get("status") in {"succeeded", "failed", "cancelled"}
        ),
        key=lambda item: item[0],
    )
    for _, job_id in finished[: max(0, len(_jobs) - _MAX_JOBS)]:
        _jobs.pop(job_id, None)


def _set_step_status(job: Dict[str, Any], status: str, error: Optional[str] = None) -> None:
    if not job["steps"]:
        return
    step = job["steps"][0]
    step["status"] = status
    step["error"] = error
    job["current_step"] = step["id"] if status == "running" else None
    if status == "failed":
        job["failed_step"] = step["id"]


def create_job(
    job_type: str,
    payload: Dict[str, Any],
    func: JobCallable,
    *,
    owner_user_id: Optional[str] = None,
    steps: Optional[Iterable[str]] = None,
    on_success: Optional[SuccessCallback] = None,
) -> Dict[str, Any]:
    """Create and start a background job, returning its public snapshot."""
    job_id = uuid.uuid4().hex
    now = _utc_now()
    step_ids = list(steps or [job_type])
    job = {
        "id": job_id,
        "type": job_type,
        "status": "queued",
        "payload": deepcopy(payload),
        "steps": [_new_step(step_id) for step_id in step_ids],
        "current_step": None,
        "failed_step": None,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "owner_user_id": owner_user_id,
    }

    with _lock:
        _cleanup_locked()
        _jobs[job_id] = job
        snapshot = _snapshot(job)

    _executor.submit(_run_job, job_id, func, on_success)
    return snapshot


def _run_job(
    job_id: str,
    func: JobCallable,
    on_success: Optional[SuccessCallback],
) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        now = _utc_now()
        job["status"] = "running"
        job["started_at"] = now
        job["updated_at"] = now
        _set_step_status(job, "running")

    try:
        result = func()
        if on_success:
            try:
                on_success(result)
            except Exception:
                logger.exception("Background job success callback failed: %s", job_id)

        with _lock:
            job = _jobs.get(job_id)
            if not job:
                return
            now = _utc_now()
            job["status"] = "succeeded"
            job["result"] = result
            job["error"] = None
            job["finished_at"] = now
            job["updated_at"] = now
            job["_finished_monotonic"] = time.time()
            _set_step_status(job, "succeeded")
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        logger.warning("Background job failed: %s: %s", job_id, message, exc_info=True)
        with _lock:
            job = _jobs.get(job_id)
            if not job:
                return
            now = _utc_now()
            job["status"] = "failed"
            job["result"] = None
            job["error"] = message
            job["finished_at"] = now
            job["updated_at"] = now
            job["_finished_monotonic"] = time.time()
            _set_step_status(job, "failed", message)


def get_job(job_id: str, *, owner_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return a job snapshot if it exists and belongs to the requester."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        owner = job.get("owner_user_id")
        if owner and owner != owner_user_id:
            return None
        return _snapshot(job)


def clear_jobs() -> None:
    """Test helper: clear in-memory job state without replacing the executor."""
    with _lock:
        _jobs.clear()
