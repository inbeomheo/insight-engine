"""
발행 큐 서비스 — 상태 머신 + 재시도 정책

상태 흐름: queued → publishing → success | failed → retry (back to queued)
개발 모드(Supabase 비활성)에서는 인메모리 리스트로 동작합니다.
"""
import json
import os
import time
import uuid
from threading import Lock

from services.core.logging_config import get_logger
import logging

logger = get_logger('publish_queue')

QUEUE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'publish_queue.json')


class PublishQueueService:
    """발행 큐 관리 — 상태 머신 + 재시도 정책"""

    STATES = ['queued', 'publishing', 'success', 'failed']
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 1800]  # 1분, 5분, 30분 (초)

    def __init__(self):
        self._queue: list[dict] = []
        self._lock = Lock()
        self._load_queue()

    def _save_queue(self):
        """큐 상태를 파일로 저장."""
        try:
            os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._queue, f, ensure_ascii=False, default=str)
        except Exception:
            pass  # 파일 저장 실패는 무시 (인메모리가 primary)

    def _load_queue(self):
        """시작 시 파일에서 큐 복원."""
        try:
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                    self._queue = json.load(f)
        except Exception:
            self._queue = []

    def enqueue(self, content_id: str, title: str, content: str,
                plugin_id: str, user_id: str) -> dict:
        """발행 큐에 항목 추가"""
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
            with self._lock:
                self._queue.append(item)
                self._save_queue()
            logger.info(f"큐 추가: {item['id']} (plugin={plugin_id}, title={title[:30]})")
            return self._sanitize(item)
        except Exception as e:
            logger.error("enqueue 실패: %s", e, exc_info=True)
            return {}

    def process_queue(self) -> list:
        """큐에서 대기 항목 처리 — 스케줄러에서 호출"""
        try:
            from services.mcp import plugin_registry

            now = time.time()
            results = []

            with self._lock:
                # 처리 대상: status=queued, next_retry_at이 None이거나 현재 시간 이전
                pending = [
                    item for item in self._queue
                    if item['status'] == 'queued'
                    and (item['next_retry_at'] is None or item['next_retry_at'] <= now)
                ]

            for item in pending:
                item_id = item['id']
                # 상태를 publishing으로 전환
                with self._lock:
                    item['status'] = 'publishing'
                    item['updated_at'] = time.time()

                try:
                    result = plugin_registry.execute(
                        item['plugin_id'],
                        item['content'],
                        item['title'],
                    )
                    with self._lock:
                        if result.get('success'):
                            item['status'] = 'success'
                            item['published_url'] = result.get('url')
                            item['error_message'] = None
                            logger.info(f"발행 성공: {item_id}")
                        else:
                            self._handle_failure(
                                item, result.get('message', '발행 실패')
                            )
                        item['updated_at'] = time.time()
                        self._save_queue()
                except Exception as e:
                    with self._lock:
                        self._handle_failure(item, str(e))
                        item['updated_at'] = time.time()
                        self._save_queue()
                    logger.error(f"발행 예외: {item_id} - {e}")

                results.append(self._sanitize(item))

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
                f"재시도 예약: {item['id']} "
                f"(시도 {item['retry_count']}/{self.MAX_RETRIES}, "
                f"대기 {delay}초)"
            )
        else:
            item['status'] = 'failed'
            logger.warning(
                f"최종 실패: {item['id']} "
                f"(최대 재시도 {self.MAX_RETRIES}회 초과)"
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
        """큐 항목 취소 — queued 상태만 취소 가능"""
        try:
            with self._lock:
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
            logger.info(f"큐 항목 취소: {item_id}")
            return {'success': True}
        except Exception as e:
            logger.error("cancel_item 실패: %s", e, exc_info=True)
            return {}

    def retry_item(self, item_id: str) -> dict:
        """실패 항목 수동 재시도 — failed 상태만 재시도 가능"""
        try:
            with self._lock:
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
            logger.info(f"수동 재시도: {item_id}")
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
        return {
            'id': item['id'],
            'content_id': item['content_id'],
            'title': item['title'],
            'plugin_id': item['plugin_id'],
            'user_id': item['user_id'],
            'status': item['status'],
            'retry_count': item['retry_count'],
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
