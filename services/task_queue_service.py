"""
비동기 작업 큐 서비스 (F9-02)
인메모리 큐 + 스레드 워커 기반 비동기 태스크 처리
Celery/Redis 없이도 동작하는 경량 구현
"""
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Task:
    """작업 태스크 데이터 클래스"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: int = 0  # 높을수록 우선 처리

    def to_dict(self) -> Dict[str, Any]:
        """태스크 정보를 딕셔너리로 변환"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_s': (
                round(self.completed_at - self.started_at, 2)
                if self.started_at and self.completed_at else None
            ),
        }


class TaskQueueService:
    """
    인메모리 작업 큐 서비스

    특징:
    - 우선순위 큐 (priority 값 높을수록 먼저 처리)
    - 워커 스레드 수 설정 가능
    - 태스크 결과 조회 (task_id)
    - 그레이스풀 셧다운
    """

    def __init__(self, num_workers: int = 3, max_queue_size: int = 100):
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._tasks: Dict[str, Task] = {}
        self._tasks_lock = threading.Lock()
        self._workers: list = []
        self._shutdown_event = threading.Event()
        self._num_workers = num_workers
        self._started = False

    def start(self) -> None:
        """워커 스레드 시작"""
        if self._started:
            return
        self._started = True
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            t.start()
            self._workers.append(t)
        logger.info("TaskQueueService 시작 (워커 %d개)", self._num_workers)

    def stop(self, timeout: float = 10.0) -> None:
        """그레이스풀 셧다운"""
        logger.info("TaskQueueService 종료 중...")
        self._shutdown_event.set()
        # 워커 깨우기 위한 더미 아이템
        for _ in self._workers:
            try:
                self._queue.put_nowait((0, '', None))
            except queue.Full:
                pass
        for w in self._workers:
            w.join(timeout=timeout)
        logger.info("TaskQueueService 종료 완료")

    def enqueue(
        self,
        func: Callable,
        *args,
        priority: int = 0,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        태스크 큐에 추가

        Args:
            func: 실행할 함수
            *args: 함수 인자
            priority: 우선순위 (높을수록 먼저 처리)
            task_id: 태스크 ID (없으면 자동 생성)
            **kwargs: 함수 키워드 인자

        Returns:
            task_id
        """
        if not self._started:
            self.start()

        tid = task_id or str(uuid.uuid4())
        task = Task(
            task_id=tid,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )

        with self._tasks_lock:
            self._tasks[tid] = task

        # PriorityQueue: (우선순위 역순, 시간, task_id)
        self._queue.put((-priority, time.time(), tid))
        logger.debug("태스크 큐 등록: %s (priority=%d)", tid, priority)
        return tid

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """태스크 상태 및 결과 조회"""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def cancel_task(self, task_id: str) -> bool:
        """PENDING 상태 태스크 취소"""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """큐 통계 반환"""
        with self._tasks_lock:
            by_status = {}
            for task in self._tasks.values():
                key = task.status.value
                by_status[key] = by_status.get(key, 0) + 1
        return {
            'queue_size': self._queue.qsize(),
            'total_tasks': len(self._tasks),
            'by_status': by_status,
            'num_workers': self._num_workers,
        }

    def _worker_loop(self):
        """워커 스레드 메인 루프"""
        while not self._shutdown_event.is_set():
            try:
                # 1초 타임아웃으로 블로킹 대기
                _priority, _time, task_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if task_id is None:
                # 셧다운 신호
                break

            with self._tasks_lock:
                task = self._tasks.get(task_id)

            if not task or task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            logger.debug("태스크 실행 시작: %s", task_id)

            try:
                result = task.func(*task.args, **task.kwargs)
                task.result = result
                task.status = TaskStatus.SUCCESS
                logger.debug("태스크 완료: %s", task_id)
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                logger.error("태스크 실패: %s — %s", task_id, e)
            finally:
                task.completed_at = time.time()
                self._queue.task_done()


# 전역 싱글톤
_task_queue: Optional[TaskQueueService] = None


def get_task_queue() -> TaskQueueService:
    """TaskQueueService 싱글톤 인스턴스 반환 (최초 호출 시 워커 시작)"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueueService(num_workers=3)
        _task_queue.start()
    return _task_queue
