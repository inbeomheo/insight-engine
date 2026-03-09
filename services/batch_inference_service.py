"""비동기 배치 추론 서비스 - 대량 요청 큐 처리

여러 콘텐츠 생성 요청을 배치로 묶어 순차 처리하는 서비스.
인메모리 저장소에 배치 작업을 관리하고 진행률을 추적한다.
"""
import uuid
import time
import threading
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """배치 작업 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchRequest:
    """개별 배치 요청 항목"""
    url: str
    style_id: str = "blog_seo"
    provider: str = ""
    model: str = ""


@dataclass
class BatchItemResult:
    """배치 내 개별 항목의 처리 결과"""
    request: BatchRequest
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class BatchJob:
    """배치 작업 전체 정보"""
    batch_id: str
    requests: list
    status: BatchStatus = BatchStatus.PENDING
    created_at: float = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: list = field(default_factory=list)
    progress: int = 0  # 0-100
    total: int = 0
    completed_count: int = 0


# 인메모리 배치 저장소
_batch_store: dict[str, BatchJob] = {}
_store_lock = threading.Lock()


def _process_item(item: BatchItemResult) -> dict:
    """개별 항목 처리 (시뮬레이션).

    실제 AI 호출 없이 결과 dict를 반환한다.
    프로덕션에서는 ai_service.create_content()를 호출하도록 교체.
    """
    return {
        "title": f"[배치 생성] {item.request.url}",
        "content": f"{item.request.style_id} 스타일로 생성된 콘텐츠",
        "html": f"<p>{item.request.style_id} 스타일 콘텐츠</p>",
        "style_id": item.request.style_id,
        "url": item.request.url,
    }


def _run_batch(batch_id: str) -> None:
    """배치 작업을 백그라운드 스레드에서 순차 처리한다."""
    with _store_lock:
        job = _batch_store.get(batch_id)
        if not job:
            return

    job.status = BatchStatus.PROCESSING
    job.started_at = time.time()

    for i, item_result in enumerate(job.results):
        # 취소 확인
        if job.status == BatchStatus.CANCELLED:
            break

        item_result.status = "processing"
        item_result.started_at = time.time()

        try:
            result = _process_item(item_result)
            item_result.result = result
            item_result.status = "completed"
        except Exception as e:
            item_result.error = str(e)
            item_result.status = "failed"
            logger.error("배치 항목 처리 실패: batch_id=%s, index=%d, error=%s",
                         batch_id, i, str(e))
        finally:
            item_result.completed_at = time.time()
            job.completed_count += 1
            job.progress = int((job.completed_count / job.total) * 100)

    # 최종 상태 결정
    if job.status != BatchStatus.CANCELLED:
        failed_count = sum(1 for r in job.results if r.status == "failed")
        if failed_count == job.total:
            job.status = BatchStatus.FAILED
        else:
            job.status = BatchStatus.COMPLETED

    job.completed_at = time.time()


def submit_batch(requests: list[dict], run_sync: bool = False) -> str:
    """배치를 제출하고 batch_id를 반환한다.

    Args:
        requests: [{"url": "...", "style_id": "..."}, ...] 형태의 요청 목록
        run_sync: True면 동기 처리 (테스트용), False면 백그라운드 스레드

    Returns:
        batch_id 문자열

    Raises:
        ValueError: 요청 목록이 비어있을 때
    """
    if not requests:
        raise ValueError("요청 목록이 비어있습니다")

    batch_id = str(uuid.uuid4())
    now = time.time()

    # BatchRequest 및 BatchItemResult 생성
    batch_requests = []
    item_results = []
    for req in requests:
        br = BatchRequest(
            url=req.get("url", ""),
            style_id=req.get("style_id", "blog_seo"),
            provider=req.get("provider", ""),
            model=req.get("model", ""),
        )
        batch_requests.append(br)
        item_results.append(BatchItemResult(request=br))

    job = BatchJob(
        batch_id=batch_id,
        requests=batch_requests,
        status=BatchStatus.PENDING,
        created_at=now,
        results=item_results,
        total=len(requests),
    )

    with _store_lock:
        _batch_store[batch_id] = job

    logger.info("배치 제출: batch_id=%s, total=%d", batch_id, len(requests))

    if run_sync:
        # 테스트용 동기 실행
        _run_batch(batch_id)
    else:
        # 백그라운드 스레드 실행
        thread = threading.Thread(target=_run_batch, args=(batch_id,), daemon=True)
        thread.start()

    return batch_id


def get_batch_status(batch_id: str) -> dict:
    """배치 진행률을 조회한다.

    Returns:
        {"status": "processing", "progress": 30, "completed": 3, "total": 10, ...}

    Raises:
        KeyError: 존재하지 않는 batch_id
    """
    with _store_lock:
        job = _batch_store.get(batch_id)

    if not job:
        raise KeyError(f"배치를 찾을 수 없습니다: {batch_id}")

    return {
        "batch_id": job.batch_id,
        "status": job.status.value,
        "progress": job.progress,
        "completed": job.completed_count,
        "total": job.total,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


def get_batch_results(batch_id: str) -> list[dict]:
    """완료된 배치의 결과를 수집한다.

    Returns:
        [{"url": "...", "status": "completed", "result": {...}}, ...]

    Raises:
        KeyError: 존재하지 않는 batch_id
    """
    with _store_lock:
        job = _batch_store.get(batch_id)

    if not job:
        raise KeyError(f"배치를 찾을 수 없습니다: {batch_id}")

    results = []
    for item in job.results:
        results.append({
            "url": item.request.url,
            "style_id": item.request.style_id,
            "status": item.status,
            "result": item.result,
            "error": item.error,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
        })

    return results


def cancel_batch(batch_id: str) -> bool:
    """배치를 취소한다. 미처리 항목만 취소되고 처리 중/완료 항목은 유지.

    Returns:
        True: 취소 성공, False: 이미 완료/실패/취소된 배치

    Raises:
        KeyError: 존재하지 않는 batch_id
    """
    with _store_lock:
        job = _batch_store.get(batch_id)

    if not job:
        raise KeyError(f"배치를 찾을 수 없습니다: {batch_id}")

    # 이미 종료된 배치는 취소 불가
    if job.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED):
        return False

    job.status = BatchStatus.CANCELLED

    # 아직 처리되지 않은 항목을 cancelled로 표시
    for item in job.results:
        if item.status == "pending":
            item.status = "cancelled"

    logger.info("배치 취소: batch_id=%s", batch_id)
    return True


def list_batches(status: str = None) -> list[dict]:
    """배치 목록을 조회한다.

    Args:
        status: 필터할 상태 문자열 (예: "pending", "completed"). None이면 전체.

    Returns:
        배치 요약 정보 리스트
    """
    with _store_lock:
        jobs = list(_batch_store.values())

    result = []
    for job in jobs:
        if status and job.status.value != status:
            continue
        result.append({
            "batch_id": job.batch_id,
            "status": job.status.value,
            "progress": job.progress,
            "completed": job.completed_count,
            "total": job.total,
            "created_at": job.created_at,
        })

    return result


def cleanup_old_batches(max_age_hours: int = 24) -> int:
    """오래된 배치를 정리한다.

    Args:
        max_age_hours: 이 시간보다 오래된 완료/실패/취소 배치를 삭제

    Returns:
        삭제된 배치 수
    """
    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0

    with _store_lock:
        to_remove = []
        for batch_id, job in _batch_store.items():
            # 종료된 배치만 정리 (진행 중인 배치는 보존)
            if job.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED):
                if job.created_at < cutoff:
                    to_remove.append(batch_id)

        for batch_id in to_remove:
            del _batch_store[batch_id]
            removed += 1

    if removed > 0:
        logger.info("오래된 배치 %d개 정리됨 (기준: %d시간)", removed, max_age_hours)

    return removed


def _clear_store() -> None:
    """테스트용: 저장소 초기화"""
    with _store_lock:
        _batch_store.clear()
