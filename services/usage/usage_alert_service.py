"""
사용량 알림 서비스 (F4-09)
80%/100% 임계치 도달 시 알림 생성
"""
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('UsageAlertService')

# 기본 임계치 (%)
DEFAULT_THRESHOLDS = [80, 100]


class UsageAlertService:
    """사용량 임계치 알림 관리"""

    def __init__(self, thresholds: list[int] | None = None):
        self._thresholds = sorted(thresholds or DEFAULT_THRESHOLDS)
        # user_id → set(이미 알림 보낸 임계치)
        self._notified: dict[str, set[int]] = {}
        self._alerts: list[dict] = []

    def check_usage(self, user_id: str, used: int, total: int) -> list[dict]:
        """사용량 체크 후 초과된 임계치에 대해 알림 생성"""
        if total <= 0:
            return []

        percentage = (used / total) * 100
        notified = self._notified.setdefault(user_id, set())
        new_alerts = []

        for threshold in self._thresholds:
            if percentage >= threshold and threshold not in notified:
                alert = {
                    'user_id': user_id,
                    'threshold': threshold,
                    'used': used,
                    'total': total,
                    'percentage': round(percentage, 1),
                    'message': f'사용량이 {threshold}%에 도달했습니다. ({used}/{total})',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                }
                new_alerts.append(alert)
                self._alerts.append(alert)
                notified.add(threshold)
                logger.info(f"사용량 알림: {user_id[:8]}... → {threshold}%")

        return new_alerts

    def get_alerts(self, user_id: str) -> list[dict]:
        """사용자의 알림 목록"""
        return [a for a in self._alerts if a['user_id'] == user_id]

    def reset_alerts(self, user_id: str) -> None:
        """월간 리셋 시 알림 상태 초기화"""
        self._notified.pop(user_id, None)
        self._alerts = [a for a in self._alerts if a['user_id'] != user_id]


usage_alert_service = UsageAlertService()
