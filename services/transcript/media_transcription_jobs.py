"""Redis/RQ 미디어 전사 작업과 파일 기반 상태 저장소."""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from config import (
    MEDIA_FFMPEG_TIMEOUT_SECONDS,
    MEDIA_JOB_TTL_SECONDS,
    MEDIA_MAX_DURATION_SECONDS,
    MEDIA_TRANSCRIPTION_DIR,
)
from services.transcript.media_normalizer import MediaValidationError, normalize_media

QUEUE_NAME = 'media-transcription'


def _root() -> Path:
    path = Path(MEDIA_TRANSCRIPTION_DIR)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _record_path(job_id: str) -> Path:
    safe_id = str(uuid.UUID(job_id))
    return _root() / f'{safe_id}.json'


def _input_path(job_id: str, suffix: str) -> Path:
    safe_id = str(uuid.UUID(job_id))
    uploads = _root() / 'uploads'
    uploads.mkdir(parents=True, exist_ok=True, mode=0o700)
    return uploads / f'{safe_id}{suffix}'


def cleanup_expired_jobs(*, now: float | None = None) -> None:
    """TTL이 지난 상태 파일과 고아 업로드를 best-effort로 제거한다."""
    cutoff = (now if now is not None else time.time()) - MEDIA_JOB_TTL_SECONDS
    root = _root()
    uploads = root / 'uploads'
    candidates = list(root.glob('*.json'))
    if uploads.exists():
        candidates.extend(uploads.glob('*'))
    for path in candidates:
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def _write_record(record: dict[str, Any]) -> None:
    path = _record_path(record['job_id'])
    fd, temp_path = tempfile.mkstemp(prefix=f'.{path.stem}-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(record, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def read_job(job_id: str, owner_id: str) -> dict[str, Any] | None:
    try:
        with _record_path(job_id).open('r', encoding='utf-8') as handle:
            record = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if record.get('owner_id') != owner_id:
        return None
    return record


def discard_job(job_id: str, input_path: str | os.PathLike[str] | None = None) -> None:
    """큐 등록 전 실패한 작업의 상태 파일과 업로드를 함께 제거한다."""
    paths = [_record_path(job_id)]
    if input_path is not None:
        paths.append(Path(input_path))
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue


def create_job(*, owner_id: str, source_title: str, source_type: str, suffix: str) -> tuple[dict[str, Any], Path]:
    cleanup_expired_jobs()
    job_id = str(uuid.uuid4())
    now = time.time()
    record = {
        'job_id': job_id,
        'owner_id': owner_id,
        'status': 'queued',
        'stage': 'uploaded',
        'progress': 0,
        'message': '업로드를 완료했습니다.',
        'source_title': source_title,
        'source_type': source_type,
        'created_at': now,
        'updated_at': now,
    }
    _write_record(record)
    return record, _input_path(job_id, suffix)


def _update(job_id: str, **changes: Any) -> dict[str, Any]:
    path = _record_path(job_id)
    with path.open('r', encoding='utf-8') as handle:
        record = json.load(handle)
    record.update(changes)
    record['updated_at'] = time.time()
    _write_record(record)
    return record


def enqueue_job(job_id: str, input_path: str) -> None:
    from redis import Redis
    from rq import Queue

    redis_url = os.getenv('MEDIA_REDIS_URL', '')
    if not redis_url:
        raise RuntimeError('미디어 작업 큐 Redis가 설정되어 있지 않습니다.')
    queue = Queue(QUEUE_NAME, connection=Redis.from_url(redis_url))
    queue.enqueue(
        'services.transcript.media_transcription_jobs.run_job',
        job_id,
        input_path,
        job_id=job_id,
        job_timeout=max(MEDIA_FFMPEG_TIMEOUT_SECONDS + 1800, 2400),
        result_ttl=MEDIA_JOB_TTL_SECONDS,
        failure_ttl=MEDIA_JOB_TTL_SECONDS,
    )


def run_job(job_id: str, input_path: str) -> dict[str, Any]:
    """RQ worker 진입점. 성공·실패 모두 업로드/정규화 임시 파일을 삭제한다."""
    normalized_path: str | None = None
    try:
        _update(
            job_id,
            status='running', stage='normalizing', progress=10,
            message='미디어와 오디오 트랙을 검사하고 있습니다.',
        )
        normalized_path, probe = normalize_media(
            input_path,
            max_duration_seconds=MEDIA_MAX_DURATION_SECONDS,
            timeout_seconds=MEDIA_FFMPEG_TIMEOUT_SECONDS,
        )
        _update(
            job_id,
            stage='transcribing', progress=30,
            message='음성을 텍스트로 변환하고 있습니다.',
            duration_seconds=probe.duration_seconds,
        )

        from services.transcript.whisper_service import transcribe_audio_detailed
        result = transcribe_audio_detailed(
            normalized_path,
            os.getenv('WHISPER_MODEL_SIZE', 'base'),
        )
        if not result or not str(result.get('text') or '').strip():
            raise MediaValidationError('음성을 인식하지 못했습니다.')

        record = _update(
            job_id,
            status='succeeded', stage='ready', progress=100,
            message='미디어 전사를 완료했습니다.',
            result={
                'text': str(result['text']).strip(),
                'transcript_source': 'whisper',
                'transcript_segments': result.get('segments') or [],
                'detected_language': result.get('language'),
                'language_probability': result.get('language_probability'),
                'duration_seconds': probe.duration_seconds,
            },
        )
        return {'job_id': job_id, 'status': record['status']}
    except MediaValidationError as exc:
        _update(
            job_id,
            status='failed', progress=100,
            message='미디어 전사에 실패했습니다.',
            error={'code': 'MEDIA_INVALID', 'message': str(exc), 'retryable': False},
        )
        raise
    except Exception:
        _update(
            job_id,
            status='failed', progress=100,
            message='미디어 전사에 실패했습니다.',
            error={
                'code': 'TRANSCRIPTION_FAILED',
                'message': '미디어를 전사하지 못했습니다. 잠시 후 다시 시도해 주세요.',
                'retryable': True,
            },
        )
        raise
    finally:
        for path in (normalized_path, input_path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
