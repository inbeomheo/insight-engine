"""
이상 탐지 알림 서비스 (F6-16)
사용량 / 에러율 이상치 감지 후 알림
"""
import statistics
from datetime import datetime, timezone
from typing import Any, Callable

from services.logging_config import ServiceLogger

logger = ServiceLogger('AnomalyService')


class AnomalyService:
    """통계적 이상 탐지 (Z-score 기반)"""

    def __init__(self, z_threshold: float = 2.5):
        self.z_threshold = z_threshold
        # metric_name → [float] (최근 관측값)
        self._baselines: dict[str, list[float]] = {}
        # 알림 핸들러 목록
        self._handlers: list[Callable[[dict], None]] = []
        # 탐지된 이상 이력
        self._anomalies: list[dict] = []

    def add_handler(self, handler: Callable[[dict], None]) -> None:
        """이상 탐지 시 호출될 핸들러 등록"""
        self._handlers.append(handler)

    def record_metric(self, metric: str, value: float,
                      timestamp: str | None = None) -> dict[str, Any] | None:
        """
        지표 값 기록 후 이상 여부 판단

        Returns:
            이상 탐지 시 anomaly dict, 정상이면 None
        """
        history = self._baselines.setdefault(metric, [])
        is_anomaly = False
        z_score = None

        if len(history) >= 10:
            mean = statistics.mean(history)
            stdev = statistics.stdev(history) if len(history) > 1 else 0.0
            if stdev == 0:
                # 기준값이 모두 같고 새 값이 다르면 이상으로 판단
                is_anomaly = value != mean
                z_score = float('inf') if is_anomaly else 0.0
            else:
                z_score = abs(value - mean) / stdev
                is_anomaly = z_score > self.z_threshold

        history.append(value)
        # 최근 1000개만 유지
        if len(history) > 1000:
            del history[0]

        if is_anomaly and z_score is not None:
            z_display = round(z_score, 2) if z_score != float('inf') else 9999.0
            anomaly = {
                'metric': metric,
                'value': value,
                'z_score': z_display,
                'threshold': self.z_threshold,
                'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
            }
            self._anomalies.append(anomaly)
            self._notify(anomaly)
            logger.warning(f'이상 탐지: {metric}={value} (z={z_score:.2f})')
            return anomaly
        return None

    def get_anomalies(self, limit: int = 50) -> list[dict]:
        """최근 이상 탐지 이력"""
        return self._anomalies[-limit:]

    def get_baseline(self, metric: str) -> dict[str, Any]:
        """특정 지표의 기준선 통계"""
        history = self._baselines.get(metric, [])
        if not history:
            return {'metric': metric, 'count': 0}
        return {
            'metric': metric,
            'count': len(history),
            'mean': round(statistics.mean(history), 4),
            'stdev': round(statistics.stdev(history), 4) if len(history) > 1 else 0.0,
            'min': round(min(history), 4),
            'max': round(max(history), 4),
        }

    def clear_anomalies(self) -> None:
        """이상 이력 초기화"""
        self._anomalies.clear()

    def _notify(self, anomaly: dict) -> None:
        for handler in self._handlers:
            try:
                handler(anomaly)
            except Exception as e:
                logger.error(f'이상 알림 핸들러 오류: {e}')
