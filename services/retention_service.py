"""
이탈 방지 서비스 (F4-22)
비활성 사용자 감지 + 알림 생성
"""
from datetime import datetime, timezone
from services.logging_config import ServiceLogger

logger = ServiceLogger('RetentionService')

# 비활성 임계치 (일)
INACTIVITY_THRESHOLDS = {
    'warning': 7,    # 7일 미접속 → 경고
    'at_risk': 14,   # 14일 → 이탈 위험
    'churned': 30,   # 30일 → 이탈
}


class RetentionService:
    """이탈 방지 알림 관리"""

    def __init__(self):
        # user_id → 마지막 활동일
        self._last_active: dict[str, str] = {}
        self._notifications: list[dict] = []

    def record_activity(self, user_id: str) -> None:
        """사용자 활동 기록"""
        self._last_active[user_id] = datetime.now(timezone.utc).isoformat()

    def check_inactive_users(self) -> list[dict]:
        """비활성 사용자 감지 + 알림 생성"""
        now = datetime.now(timezone.utc)
        alerts = []

        for user_id, last_str in self._last_active.items():
            last_dt = datetime.fromisoformat(last_str)
            days_inactive = (now - last_dt).days

            status = None
            if days_inactive >= INACTIVITY_THRESHOLDS['churned']:
                status = 'churned'
            elif days_inactive >= INACTIVITY_THRESHOLDS['at_risk']:
                status = 'at_risk'
            elif days_inactive >= INACTIVITY_THRESHOLDS['warning']:
                status = 'warning'

            if status:
                alert = {
                    'user_id': user_id,
                    'status': status,
                    'days_inactive': days_inactive,
                    'last_active': last_str,
                    'message': self._get_message(status, days_inactive),
                    'detected_at': now.isoformat(),
                }
                alerts.append(alert)
                self._notifications.append(alert)

        logger.info(f"비활성 사용자 감지: {len(alerts)}명")
        return alerts

    def get_user_status(self, user_id: str) -> dict:
        """개별 사용자 이탈 위험도"""
        last_str = self._last_active.get(user_id)
        if not last_str:
            return {'status': 'unknown', 'days_inactive': None}

        days = (datetime.now(timezone.utc) - datetime.fromisoformat(last_str)).days

        for status in ('churned', 'at_risk', 'warning'):
            if days >= INACTIVITY_THRESHOLDS[status]:
                return {'status': status, 'days_inactive': days}

        return {'status': 'active', 'days_inactive': days}

    def get_notifications(self, user_id: str | None = None) -> list[dict]:
        """알림 조회"""
        if user_id:
            return [n for n in self._notifications if n['user_id'] == user_id]
        return self._notifications

    @staticmethod
    def _get_message(status: str, days: int) -> str:
        messages = {
            'warning': f'{days}일간 접속하지 않았습니다. 돌아오세요!',
            'at_risk': f'{days}일간 비활성 상태입니다. 새로운 기능을 확인해보세요.',
            'churned': f'{days}일간 접속하지 않았습니다. 계정이 곧 비활성화됩니다.',
        }
        return messages.get(status, '')


retention_service = RetentionService()
