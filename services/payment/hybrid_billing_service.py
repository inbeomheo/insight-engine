"""
하이브리드 과금 서비스 (F4-11)
기본 크레딧(플랜 포함) + 초과분 종량제
"""
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('HybridBillingService')


class HybridBillingService:
    """기본 크레딧 + 초과 종량제 과금"""

    def __init__(self):
        # user_id → 과금 상태
        self._accounts: dict[str, dict] = {}

    def setup_account(self, user_id: str, base_credits: int, overage_rate: float) -> dict:
        """계정 과금 설정

        Args:
            user_id: 사용자 ID
            base_credits: 플랜 포함 기본 크레딧
            overage_rate: 초과분 단가 (원/건)
        """
        try:
            self._accounts[user_id] = {
                'base_credits': base_credits,
                'used': 0,
                'overage_rate': overage_rate,
                'overage_charges': 0.0,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            return self._accounts[user_id]
        except Exception as e:
            logger.error("setup_account 실패: %s", e, exc_info=True)
            return {}

    def consume(self, user_id: str, amount: int = 1) -> dict:
        """크레딧 사용 (기본 크레딧 우선 차감, 초과 시 종량제)"""
        try:
            account = self._accounts.get(user_id)
            if not account:
                return {'error': '과금 계정이 설정되지 않았습니다.'}

            account['used'] += amount
            overage = max(0, account['used'] - account['base_credits'])
            account['overage_charges'] = overage * account['overage_rate']

            return {
                'used': account['used'],
                'base_remaining': max(0, account['base_credits'] - account['used']),
                'overage_count': overage,
                'overage_charges': account['overage_charges'],
            }
        except Exception as e:
            logger.error("consume 실패: %s", e, exc_info=True)
            return {}

    def get_billing_summary(self, user_id: str) -> dict:
        """과금 요약 조회"""
        try:
            account = self._accounts.get(user_id)
            if not account:
                return {'error': '계정을 찾을 수 없습니다.'}

            overage = max(0, account['used'] - account['base_credits'])
            return {
                'base_credits': account['base_credits'],
                'used': account['used'],
                'base_remaining': max(0, account['base_credits'] - account['used']),
                'overage_count': overage,
                'overage_rate': account['overage_rate'],
                'overage_charges': overage * account['overage_rate'],
            }
        except Exception as e:
            logger.error("get_billing_summary 실패: %s", e, exc_info=True)
            return {}

    def reset_monthly(self, user_id: str) -> dict:
        """월간 초기화 (기본 크레딧 복원)"""
        try:
            account = self._accounts.get(user_id)
            if not account:
                return {'error': '계정을 찾을 수 없습니다.'}

            account['used'] = 0
            account['overage_charges'] = 0.0
            account['updated_at'] = datetime.now(timezone.utc).isoformat()
            return account
        except Exception as e:
            logger.error("reset_monthly 실패: %s", e, exc_info=True)
            return {}


hybrid_billing_service = HybridBillingService()
