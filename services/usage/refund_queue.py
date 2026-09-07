"""Durable, process-safe retry ledger for failed quota reservation refunds.

The ledger intentionally stays file-backed so deployments do not need a second
database just to recover a Supabase outage. Every read and write is bounded and
schema-validated: a corrupt or oversized ledger fails closed instead of
silently dropping unpaid refunds or consuming unbounded memory during a JSON
rewrite.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows development fallback
    fcntl = None


_THREAD_LOCK = threading.RLock()

# JSON is rewritten atomically under an inter-process lock. These hard limits
# keep that operation bounded without ever evicting an unresolved refund.
_MAX_QUEUE_BYTES = 8 * 1024 * 1024
_MAX_JOB_BYTES = 4096
_MAX_JOBS = 10_000
_MAX_ATTEMPTS = 1_000_000
_MAX_QUOTA_VALUE = 1_000_000
_SAFE_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_IDEMPOTENCY_KEY_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$')
_HASH_RE = re.compile(r'^[0-9a-f]{64}$')
_AMBIGUOUS_RESERVATION_RE = re.compile(r'^ambiguous:[0-9a-f]{64}$')
_JOB_KINDS = frozenset({'reservation', 'ambiguous_reservation'})
_REQUIRED_FIELDS = frozenset({
    'user_id',
    'reservation_id',
    'idempotency_key',
    'request_fingerprint',
    'owner_token_hash',
    'amount',
    'remaining',
    'max_usage',
})
_OPTIONAL_FIELDS = frozenset({
    'kind',
    'created_at',
    'updated_at',
    'attempts',
    'last_error',
})


class RefundQueueCorrupt(RuntimeError):
    """The durable ledger cannot be trusted and must not be rewritten."""


class RefundQueueCapacityExceeded(RuntimeError):
    """A bounded ledger is full; unresolved entries are retained unchanged."""


def _queue_path() -> Path:
    configured = (os.getenv('USAGE_REFUND_QUEUE_PATH') or '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    app_data = Path((os.getenv('APP_DATA_DIR') or 'data').strip()).expanduser().resolve()
    return app_data / 'usage_refund_queue.json'


def _valid_text(value: object, pattern: re.Pattern[str]) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _valid_int(value: object, *, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def _valid_timestamp(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _validate_job(job: object, *, storage_key: str | None = None) -> dict:
    """Validate and normalize one refund job without mutating the input."""
    if not isinstance(job, dict):
        raise RefundQueueCorrupt('사용량 환불 작업 형식이 올바르지 않습니다.')

    fields = frozenset(job)
    if not _REQUIRED_FIELDS.issubset(fields) or not fields.issubset(
        _REQUIRED_FIELDS | _OPTIONAL_FIELDS
    ):
        raise RefundQueueCorrupt('사용량 환불 작업 필드가 올바르지 않습니다.')

    user_id = job.get('user_id')
    reservation_id = job.get('reservation_id')
    idempotency_key = job.get('idempotency_key')
    request_fingerprint = job.get('request_fingerprint')
    owner_token_hash = job.get('owner_token_hash')
    amount = job.get('amount')
    remaining = job.get('remaining')
    max_usage = job.get('max_usage')

    if not _valid_text(user_id, _SAFE_ID_RE):
        raise RefundQueueCorrupt('사용량 환불 작업의 user_id가 올바르지 않습니다.')
    if not _valid_text(reservation_id, _SAFE_ID_RE):
        raise RefundQueueCorrupt('사용량 환불 작업의 reservation_id가 올바르지 않습니다.')
    if storage_key is not None and storage_key != reservation_id:
        raise RefundQueueCorrupt('사용량 환불 작업 키와 reservation_id가 다릅니다.')
    if not _valid_text(idempotency_key, _IDEMPOTENCY_KEY_RE):
        raise RefundQueueCorrupt('사용량 환불 작업의 멱등 키가 올바르지 않습니다.')
    if not _valid_text(request_fingerprint, _HASH_RE):
        raise RefundQueueCorrupt('사용량 환불 작업의 요청 해시가 올바르지 않습니다.')
    if not _valid_text(owner_token_hash, _HASH_RE):
        raise RefundQueueCorrupt('사용량 환불 작업의 소유 토큰 해시가 올바르지 않습니다.')
    if not _valid_int(amount, minimum=1, maximum=_MAX_QUOTA_VALUE):
        raise RefundQueueCorrupt('사용량 환불 작업의 amount가 올바르지 않습니다.')
    if not _valid_int(max_usage, minimum=1, maximum=_MAX_QUOTA_VALUE):
        raise RefundQueueCorrupt('사용량 환불 작업의 max_usage가 올바르지 않습니다.')
    if not _valid_int(remaining, minimum=0, maximum=max_usage):
        raise RefundQueueCorrupt('사용량 환불 작업의 remaining이 올바르지 않습니다.')

    inferred_kind = (
        'ambiguous_reservation'
        if _AMBIGUOUS_RESERVATION_RE.fullmatch(reservation_id)
        else 'reservation'
    )
    kind = job.get('kind', inferred_kind)
    if kind not in _JOB_KINDS or kind != inferred_kind:
        raise RefundQueueCorrupt('사용량 환불 작업의 예약 종류가 올바르지 않습니다.')

    normalized = {
        'user_id': user_id,
        'reservation_id': reservation_id,
        'idempotency_key': idempotency_key,
        'request_fingerprint': request_fingerprint,
        'owner_token_hash': owner_token_hash,
        'amount': amount,
        'remaining': remaining,
        'max_usage': max_usage,
        'kind': kind,
    }

    metadata_present = fields & (_OPTIONAL_FIELDS - {'kind'})
    if storage_key is not None and not {
        'created_at', 'updated_at', 'attempts', 'last_error'
    }.issubset(fields):
        raise RefundQueueCorrupt('저장된 사용량 환불 작업 메타데이터가 불완전합니다.')
    if metadata_present:
        if not {'created_at', 'updated_at', 'attempts', 'last_error'}.issubset(fields):
            raise RefundQueueCorrupt('사용량 환불 작업 메타데이터가 불완전합니다.')
        created_at = job.get('created_at')
        updated_at = job.get('updated_at')
        attempts = job.get('attempts')
        last_error = job.get('last_error')
        if not _valid_timestamp(created_at) or not _valid_timestamp(updated_at):
            raise RefundQueueCorrupt('사용량 환불 작업 시간이 올바르지 않습니다.')
        if float(updated_at) < float(created_at):
            raise RefundQueueCorrupt('사용량 환불 작업 시간 순서가 올바르지 않습니다.')
        if not _valid_int(attempts, minimum=1, maximum=_MAX_ATTEMPTS):
            raise RefundQueueCorrupt('사용량 환불 작업 시도 횟수가 올바르지 않습니다.')
        if not isinstance(last_error, str) or len(last_error) > 500:
            raise RefundQueueCorrupt('사용량 환불 작업 오류 정보가 올바르지 않습니다.')
        normalized.update({
            'created_at': float(created_at),
            'updated_at': float(updated_at),
            'attempts': attempts,
            'last_error': last_error,
        })

    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    if len(encoded) > _MAX_JOB_BYTES:
        raise RefundQueueCapacityExceeded(
            '사용량 환불 작업 하나가 허용 크기를 초과했습니다.'
        )
    return normalized


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    """Reject duplicate keys so parsing can never hide an unresolved entry."""
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise RefundQueueCorrupt(
                '사용량 환불 재시도 원장에 중복 JSON 키가 있습니다.'
            )
        result[key] = value
    return result


def _read_jobs(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        size = path.stat().st_size
        if size > _MAX_QUEUE_BYTES:
            raise RefundQueueCapacityExceeded(
                '사용량 환불 재시도 원장이 허용 크기를 초과했습니다.'
            )
        # ``read_bytes`` would allocate the whole file if another process outside
        # our lock replaced it between stat and read. Read at most limit + 1.
        with open(path, 'rb') as handle:
            raw_bytes = handle.read(_MAX_QUEUE_BYTES + 1)
        if len(raw_bytes) > _MAX_QUEUE_BYTES:
            raise RefundQueueCapacityExceeded(
                '사용량 환불 재시도 원장이 허용 크기를 초과했습니다.'
            )
        raw = json.loads(
            raw_bytes.decode('utf-8'),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (RefundQueueCapacityExceeded, RefundQueueCorrupt):
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RefundQueueCorrupt(
            '사용량 환불 재시도 원장을 읽을 수 없습니다.'
        ) from exc

    if not isinstance(raw, dict):
        raise RefundQueueCorrupt('사용량 환불 재시도 원장 형식이 올바르지 않습니다.')
    if len(raw) > _MAX_JOBS:
        raise RefundQueueCapacityExceeded(
            '사용량 환불 재시도 원장 항목 수가 한도를 초과했습니다.'
        )

    jobs: dict[str, dict] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise RefundQueueCorrupt('사용량 환불 재시도 원장 키가 올바르지 않습니다.')
        jobs[key] = _validate_job(value, storage_key=key)
    return jobs


def _encode_jobs(jobs: dict[str, dict]) -> bytes:
    if len(jobs) > _MAX_JOBS:
        raise RefundQueueCapacityExceeded(
            '사용량 환불 재시도 원장 항목 수가 한도를 초과했습니다.'
        )
    normalized = {
        key: _validate_job(value, storage_key=key)
        for key, value in jobs.items()
    }
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    if len(payload) > _MAX_QUEUE_BYTES:
        raise RefundQueueCapacityExceeded(
            '사용량 환불 재시도 원장이 허용 크기를 초과했습니다.'
        )
    return payload


def _write_jobs(path: Path, jobs: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'.{path.name}.{os.getpid()}.{threading.get_ident()}.tmp')
    payload = _encode_jobs(jobs)
    try:
        with open(tmp_path, 'wb') as handle:
            os.chmod(tmp_path, 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            # The authoritative ledger was either atomically replaced or left
            # untouched. A stale temp file must not mask that result.
            pass


@contextmanager
def _locked_jobs() -> Iterator[tuple[Path, dict[str, dict]]]:
    """Serialize bounded read-modify-write cycles across gunicorn workers."""
    path = _queue_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock')
    with _THREAD_LOCK:
        with open(lock_path, 'a+', encoding='utf-8') as lock_file:
            os.chmod(lock_path, 0o600)
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield path, _read_jobs(path)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def enqueue_refund(job: dict, error: str) -> None:
    validated = _validate_job(job)
    reservation_id = validated['reservation_id']

    with _locked_jobs() as (path, jobs):
        previous = jobs.get(reservation_id)
        if previous is None and len(jobs) >= _MAX_JOBS:
            raise RefundQueueCapacityExceeded(
                '사용량 환불 재시도 원장이 가득 찼습니다.'
            )
        created_at = float(previous['created_at']) if previous else time.time()
        previous_attempts = int(previous['attempts']) if previous else 0
        if previous_attempts >= _MAX_ATTEMPTS:
            raise RefundQueueCapacityExceeded(
                '사용량 환불 작업의 시도 횟수가 한도를 초과했습니다.'
            )
        jobs[reservation_id] = _validate_job({
            **validated,
            'created_at': created_at,
            'updated_at': max(time.time(), created_at),
            'attempts': previous_attempts + 1,
            'last_error': str(error)[:500],
        }, storage_key=reservation_id)
        _write_jobs(path, jobs)


def pending_refunds_for_user(user_id: str, limit: int = 20) -> list[dict]:
    if not _valid_text(user_id, _SAFE_ID_RE):
        raise ValueError('user_id가 올바르지 않습니다.')
    if not _valid_int(limit, minimum=1, maximum=100):
        raise ValueError('limit은 1~100 사이의 정수여야 합니다.')
    if not _queue_path().exists():
        return []
    with _locked_jobs() as (_path, jobs):
        pending = [
            dict(job)
            for job in jobs.values()
            if job['user_id'] == user_id
        ]
    pending.sort(key=lambda job: job['created_at'])
    return pending[:limit]


def remove_refund(reservation_id: str) -> None:
    if not _valid_text(reservation_id, _SAFE_ID_RE):
        raise ValueError('reservation_id가 올바르지 않습니다.')
    if not _queue_path().exists():
        return
    with _locked_jobs() as (path, jobs):
        if jobs.pop(reservation_id, None) is not None:
            _write_jobs(path, jobs)


def pending_refund_count(user_id: str | None = None) -> int:
    if user_id is not None and not _valid_text(user_id, _SAFE_ID_RE):
        raise ValueError('user_id가 올바르지 않습니다.')
    if not _queue_path().exists():
        return 0
    with _locked_jobs() as (_path, jobs):
        if user_id is None:
            return len(jobs)
        return sum(1 for job in jobs.values() if job['user_id'] == user_id)


__all__ = [
    'RefundQueueCapacityExceeded',
    'RefundQueueCorrupt',
    'enqueue_refund',
    'pending_refund_count',
    'pending_refunds_for_user',
    'remove_refund',
]
