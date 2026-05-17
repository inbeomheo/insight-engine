"""
발행 큐 서비스 — 상태 머신 + 재시도 정책

상태 흐름: queued → publishing → success | failed → retry (back to queued)
개발 모드(Supabase 비활성)에서는 인메모리 리스트로 동작합니다.

멀티 프로세스 안전성:
- backend 워커(enqueue)와 scheduler 컨테이너(process_queue)가 같은 파일에 접근
- file lock(`filelock.FileLock`)으로 inter-process 직렬화
- 매 동작마다 디스크에서 reload → 다른 프로세스의 수정 반영
- 원자적 쓰기(tmp+rename+fsync)로 부분 쓰기 손상 방지

장기적으로는 Supabase 또는 Redis 백엔드로 이전 권장.
"""
import json
import os
import time
import uuid
from threading import Lock

try:
    from filelock import FileLock, Timeout as FileLockTimeout
    _FILELOCK_AVAILABLE = True
except ImportError:  # filelock 미설치 시 in-memory 락만 사용 (개발 환경 폴백)
    _FILELOCK_AVAILABLE = False
    FileLock = None  # type: ignore
    FileLockTimeout = Exception  # type: ignore

from services.core.logging_config import get_logger

logger = get_logger('publish_queue')

QUEUE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'publish_queue.json')
QUEUE_LOCK_FILE = QUEUE_FILE + '.lock'
FILELOCK_TIMEOUT = 5.0  # 초 — 다른 프로세스가 너무 오래 잡고 있으면 포기


def _create_redis_client(redis_url: str):
    """Create a Redis client lazily so file backend/test imports do not require Redis."""
    import redis
    return redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)


class PublishQueueService:
    """발행 큐 관리 — 상태 머신 + 재시도 정책 (멀티 프로세스 안전)"""

    STATES = ['queued', 'publishing', 'success', 'failed']
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 1800]  # 1분, 5분, 30분 (초)

    def __init__(self):
        self._queue: list[dict] = []
        self._lock = Lock()  # process-local thread lock
        self._backend = os.getenv('PUBLISH_QUEUE_BACKEND', 'file').strip().lower()
        self._redis = None
        self._redis_key = os.getenv('PUBLISH_QUEUE_REDIS_KEY', 'insight:publish_queue')

        if self._backend == 'redis':
            redis_url = os.getenv('PUBLISH_QUEUE_REDIS_URL') or os.getenv('REDIS_URL')
            if not redis_url:
                raise RuntimeError('REDIS_URL or PUBLISH_QUEUE_REDIS_URL is required for Redis publish queue')
            self._redis = _create_redis_client(redis_url)
            self._file_lock = None
        elif self._backend == 'file':
            if _FILELOCK_AVAILABLE:
                os.makedirs(os.path.dirname(QUEUE_LOCK_FILE), exist_ok=True)
                self._file_lock = FileLock(QUEUE_LOCK_FILE, timeout=FILELOCK_TIMEOUT)
            else:
                self._file_lock = None
                logger.warning("filelock unavailable; multi-process safety is not guaranteed in file backend")
        else:
            raise RuntimeError(f'Unsupported publish queue backend: {self._backend}')
        self._load_queue()

    def _acquire_file_lock(self):
        """Distributed lock context manager for file or Redis backends."""
        if self._backend == 'redis':
            return self._redis.lock(
                f'{self._redis_key}:lock',
                timeout=30,
                blocking_timeout=FILELOCK_TIMEOUT,
            )
        if self._file_lock is None:
            from contextlib import nullcontext
            return nullcontext()
        return self._file_lock

    def _save_queue(self):
        """큐 상태를 파일로 원자적으로 저장 (file lock 보호).

        호출자는 self._lock 보유 상태여야 함. file lock도 함께 잡아 멀티 프로세스
        쓰기 충돌을 막습니다. 임시 파일 → rename 패턴으로 부분 쓰기 손상 방지.
        """
        try:
            if self._backend == 'redis':
                self._redis.set(self._redis_key, json.dumps(self._queue, ensure_ascii=False, default=str))
                return

            queue_dir = os.path.dirname(QUEUE_FILE)
            os.makedirs(queue_dir, exist_ok=True)
            tmp_path = QUEUE_FILE + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self._queue, f, ensure_ascii=False, default=str)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass  # 일부 파일시스템(예: 일부 클라우드 마운트)에서 fsync 미지원
            os.replace(tmp_path, QUEUE_FILE)
        except Exception as e:
            # 인메모리가 primary 이므로 앱은 계속 동작하지만, 재시작 시 큐 손실 가능
            logger.warning("발행 큐 파일 저장 실패 (인메모리 유지): %s", e)

    def _load_queue(self):
        """파일에서 큐 복원. enqueue/process_queue 등 동작 직전에 호출하여
        다른 프로세스의 최신 변경을 반영합니다 (호출자가 self._lock 보유 필요).
        """
        try:
            if self._backend == 'redis':
                raw = self._redis.get(self._redis_key)
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode('utf-8')
                    self._queue = json.loads(raw)
                else:
                    self._queue = []
                return

            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                    self._queue = json.load(f)
        except Exception as e:
            logger.warning("발행 큐 파일 로드 실패, 빈 큐로 시작: %s", e)
            self._queue = []

    def enqueue(self, content_id: str, title: str, content: str,
                plugin_id: str, user_id: str) -> dict:
        """발행 큐에 항목 추가 (멀티 프로세스 안전)"""
        try:
            now = time.time()
            item = {
                'id': str(uuid.uuid4()),
                'content_id': content_id,
                'title': title,
                'content': content,
                'plugin_id': plugin_id,
                'user_id': user_id,
                'status': 'queued',
                'retry_count': 0,
                'next_retry_at': None,
                'published_url': None,
                'error_message': None,
                'created_at': now,
                'updated_at': now,
            }
            try:
                with self._acquire_file_lock(), self._lock:
                    self._load_queue()  # 다른 프로세스의 최신 변경 반영
                    self._queue.append(item)
                    self._save_queue()
            except FileLockTimeout:
                logger.error("enqueue: 파일 락 획득 실패 (timeout %.1fs)", FILELOCK_TIMEOUT)
                return {}
            logger.info("큐 추가: %s (plugin=%s, title=%s)", item['id'], plugin_id, title[:30])
            return self._sanitize(item)
        except Exception as e:
            logger.error("enqueue 실패: %s", e, exc_info=True)
            return {}

    def process_queue(self) -> list:
        """큐에서 대기 항목 처리 — 스케줄러에서 호출 (멀티 프로세스 안전)"""
        try:
            from services.mcp import plugin_registry

            now = time.time()
            results = []

            # 파일 락을 잡고 처리 대상 선정 + publishing 상태로 클레임
            try:
                with self._acquire_file_lock(), self._lock:
                    self._load_queue()  # 다른 프로세스의 최신 변경 반영
                    pending = [
                        item for item in self._queue
                        if item['status'] == 'queued'
                        and (item['next_retry_at'] is None or item['next_retry_at'] <= now)
                    ]
                    # 다른 프로세스가 동시에 picking하지 못하도록 즉시 publishing으로 마킹
                    for item in pending:
                        item['status'] = 'publishing'
                        item['updated_at'] = time.time()
                    if pending:
                        self._save_queue()
            except FileLockTimeout:
                logger.warning("process_queue: 파일 락 획득 실패 (다른 프로세스 처리 중)")
                return []

            # 실제 발행 (네트워크 IO) — 락 외부에서 수행하여 다른 워커 블로킹 최소화
            for item in pending:
                item_id = item['id']
                try:
                    result = plugin_registry.execute(
                        item['plugin_id'],
                        item['content'],
                        item['title'],
                    )
                    try:
                        with self._acquire_file_lock(), self._lock:
                            self._load_queue()
                            # 현재 큐에서 같은 id 항목을 찾아 업데이트
                            target = self._find_item(item_id) or item
                            if result.get('success'):
                                target['status'] = 'success'
                                target['published_url'] = result.get('url')
                                target['error_message'] = None
                                logger.info("발행 성공: %s", item_id)
                            else:
                                self._handle_failure(
                                    target, result.get('message', '발행 실패')
                                )
                            target['updated_at'] = time.time()
                            self._save_queue()
                            results.append(self._sanitize(target))
                    except FileLockTimeout:
                        logger.error("process_queue 결과 저장: 파일 락 timeout — %s", item_id)
                except Exception as e:
                    try:
                        with self._acquire_file_lock(), self._lock:
                            self._load_queue()
                            target = self._find_item(item_id) or item
                            self._handle_failure(target, str(e))
                            target['updated_at'] = time.time()
                            self._save_queue()
                            results.append(self._sanitize(target))
                    except FileLockTimeout:
                        logger.error("process_queue 예외 저장: 파일 락 timeout — %s", item_id)
                    logger.error("발행 예외: %s - %s", item_id, e)

            return results
        except Exception as e:
            logger.error("process_queue 실패: %s", e, exc_info=True)
            return []

    def _handle_failure(self, item: dict, error_message: str):
        """실패 처리 — 재시도 가능하면 queued로 복귀, 아니면 failed"""
        item['error_message'] = error_message
        item['retry_count'] += 1

        if item['retry_count'] < self.MAX_RETRIES:
            delay = self.RETRY_DELAYS[min(
                item['retry_count'] - 1, len(self.RETRY_DELAYS) - 1
            )]
            item['status'] = 'queued'
            item['next_retry_at'] = time.time() + delay
            logger.warning(
                "재시도 예약: %s (시도 %d/%d, 대기 %d초)",
                item['id'], item['retry_count'], self.MAX_RETRIES, delay
            )
        else:
            item['status'] = 'failed'
            logger.warning(
                "최종 실패: %s (최대 재시도 %d회 초과)",
                item['id'], self.MAX_RETRIES
            )

    def get_queue_status(self, user_id: str = None) -> list:
        """큐 상태 조회 (user_id 있으면 해당 사용자만)"""
        try:
            with self._lock:
                items = self._queue
                if user_id:
                    items = [i for i in items if i['user_id'] == user_id]
                # 최신순 정렬
                return [self._sanitize(i) for i in sorted(
                    items, key=lambda x: x['created_at'], reverse=True
                )]
        except Exception as e:
            logger.error("get_queue_status 실패: %s", e, exc_info=True)
            return []

    def get_status_summary(self, user_id: str = None) -> dict:
        """큐 항목을 상태별로 집계한 요약을 반환합니다.

        Returns:
            {'queued': int, 'publishing': int, 'success': int, 'failed': int, 'total': int}
        """
        try:
            with self._lock:
                items = self._queue
                if user_id:
                    items = [i for i in items if i['user_id'] == user_id]
                summary = {s: 0 for s in self.STATES}
                for item in items:
                    status = item.get('status', 'queued')
                    if status in summary:
                        summary[status] += 1
                summary['total'] = len(items)
                return summary
        except Exception as e:
            logger.error("get_status_summary 실패: %s", e, exc_info=True)
            return {s: 0 for s in self.STATES + ['total']}

    def cancel_item(self, item_id: str) -> dict:
        """큐 항목 취소 — queued 상태만 취소 가능 (멀티 프로세스 안전)"""
        try:
            try:
                with self._acquire_file_lock(), self._lock:
                    self._load_queue()
                    item = self._find_item(item_id)
                    if not item:
                        return {'success': False, 'error': '항목을 찾을 수 없습니다.'}
                    if item['status'] != 'queued':
                        return {
                            'success': False,
                            'error': f"'{item['status']}' 상태에서는 취소할 수 없습니다.",
                        }
                    self._queue.remove(item)
                    self._save_queue()
            except FileLockTimeout:
                logger.error("cancel_item: 파일 락 획득 실패 — %s", item_id)
                return {'success': False, 'error': '서버가 바쁩니다. 잠시 후 다시 시도해주세요.'}
            logger.info("큐 항목 취소: %s", item_id)
            return {'success': True}
        except Exception as e:
            logger.error("cancel_item 실패: %s", e, exc_info=True)
            return {}

    def retry_item(self, item_id: str) -> dict:
        """실패 항목 수동 재시도 — failed 상태만 재시도 가능 (멀티 프로세스 안전)"""
        try:
            try:
                with self._acquire_file_lock(), self._lock:
                    self._load_queue()
                    item = self._find_item(item_id)
                    if not item:
                        return {'success': False, 'error': '항목을 찾을 수 없습니다.'}
                    if item['status'] != 'failed':
                        return {
                            'success': False,
                            'error': f"'{item['status']}' 상태에서는 재시도할 수 없습니다.",
                        }
                    item['status'] = 'queued'
                    item['retry_count'] = 0
                    item['next_retry_at'] = None
                    item['error_message'] = None
                    item['updated_at'] = time.time()
                    self._save_queue()
            except FileLockTimeout:
                logger.error("retry_item: 파일 락 획득 실패 — %s", item_id)
                return {'success': False, 'error': '서버가 바쁩니다. 잠시 후 다시 시도해주세요.'}
            logger.info("수동 재시도: %s", item_id)
            return {'success': True}
        except Exception as e:
            logger.error("retry_item 실패: %s", e, exc_info=True)
            return {}

    def _find_item(self, item_id: str) -> dict | None:
        """ID로 큐 항목 검색 (락 내부에서 호출)"""
        for item in self._queue:
            if item['id'] == item_id:
                return item
        return None

    def _sanitize(self, item: dict) -> dict:
        """API 응답용으로 content 필드 제외한 요약 반환"""
        next_retry = item.get('next_retry_at')
        return {
            'id': item['id'],
            'content_id': item['content_id'],
            'title': item['title'],
            'plugin_id': item['plugin_id'],
            'user_id': item['user_id'],
            'status': item['status'],
            'retry_count': item['retry_count'],
            'next_retry_at': _ts_to_iso(next_retry) if next_retry else None,
            'published_url': item['published_url'],
            'error_message': item['error_message'],
            'created_at': _ts_to_iso(item['created_at']),
            'updated_at': _ts_to_iso(item['updated_at']),
        }


def _ts_to_iso(ts: float) -> str:
    """Unix timestamp → ISO 8601 문자열"""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# 싱글톤 인스턴스
publish_queue_service = PublishQueueService()
