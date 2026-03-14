"""
실시간 모니터링 서비스 (F6-15)
활성 생성 수 / 큐 깊이 / 에러율 실시간 추적
"""
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('RealtimeMonitorService')

# 최근 에러 보관 개수
MAX_ERROR_HISTORY = 100
# 슬라이딩 윈도우 이벤트 보관 개수 (에러율 계산용)
WINDOW_SIZE = 500


class RealtimeMonitorService:
    """실시간 시스템 상태 모니터링"""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_count: int = 0          # 현재 진행 중인 생성 수
        self._queue_depth: int = 0           # 큐 대기 항목 수
        self._total_requests: int = 0        # 누적 요청 수
        self._total_errors: int = 0          # 누적 에러 수
        self._recent_errors: deque = deque(maxlen=MAX_ERROR_HISTORY)
        self._recent_window: deque = deque(maxlen=WINDOW_SIZE)  # True=성공, False=에러
        self._started_at = datetime.now(timezone.utc).isoformat()

    def on_generation_start(self) -> None:
        """생성 시작 시 호출"""
        with self._lock:
            self._active_count += 1
            self._total_requests += 1

    def on_generation_end(self, success: bool, error_msg: str = '') -> None:
        """생성 완료(성공/실패) 시 호출"""
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
            self._recent_window.append(success)
            if not success:
                self._total_errors += 1
                self._recent_errors.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'message': error_msg,
                })

    def set_queue_depth(self, depth: int) -> None:
        """발행 큐 깊이 업데이트"""
        with self._lock:
            self._queue_depth = max(0, depth)

    def get_status(self) -> dict[str, Any]:
        """현재 시스템 상태 스냅샷"""
        with self._lock:
            window = list(self._recent_window)
            window_size = len(window)
            error_rate = (
                (window.count(False) / window_size * 100) if window_size > 0 else 0.0
            )
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'active_generations': self._active_count,
                'queue_depth': self._queue_depth,
                'total_requests': self._total_requests,
                'total_errors': self._total_errors,
                'error_rate_pct': round(error_rate, 2),
                'window_size': window_size,
                'started_at': self._started_at,
            }

    def get_recent_errors(self, limit: int = 10) -> list[dict]:
        """최근 에러 목록"""
        with self._lock:
            errors = list(self._recent_errors)
        return errors[-limit:]

    def reset_counters(self) -> None:
        """누적 카운터 초기화 (테스트/유지보수용)"""
        with self._lock:
            self._total_requests = 0
            self._total_errors = 0
            self._recent_window.clear()
            self._recent_errors.clear()
            logger.info('리얼타임 모니터 카운터 초기화')
