"""
팀 과금 서비스 (F4-08)
팀 크레딧 공유 + 멤버별 사용량 추적
"""
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('TeamBillingService')


class TeamBillingService:
    """팀 단위 크레딧 공유 및 멤버별 사용량 관리"""

    def __init__(self):
        # 인메모리 저장소 (프로덕션에서는 DB 교체)
        self._team_credits: dict[str, dict] = {}
        self._member_usage: dict[str, list] = {}

    def allocate_credits(self, team_id: str, total_credits: int, allocated_by: str) -> dict:
        """팀에 크레딧 할당"""
        if total_credits <= 0:
            return {'error': '크레딧은 1 이상이어야 합니다.'}

        try:
            self._team_credits[team_id] = {
                'total': total_credits,
                'used': 0,
                'allocated_by': allocated_by,
                'allocated_at': datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"팀 크레딧 할당: {team_id} → {total_credits}")
            return self._team_credits[team_id]
        except Exception as e:
            logger.error("allocate_credits 실패: %s", e, exc_info=True)
            return {}

    def consume_credit(self, team_id: str, user_id: str, amount: int = 1) -> dict:
        """팀 크레딧 차감 + 멤버 사용량 기록"""
        try:
            team = self._team_credits.get(team_id)
            if not team:
                return {'error': '팀 크레딧이 할당되지 않았습니다.'}

            remaining = team['total'] - team['used']
            if remaining < amount:
                return {'error': '팀 크레딧이 부족합니다.', 'remaining': remaining}

            team['used'] += amount

            # 멤버별 사용 기록
            if team_id not in self._member_usage:
                self._member_usage[team_id] = []
            self._member_usage[team_id].append({
                'user_id': user_id,
                'amount': amount,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

            return {
                'success': True,
                'remaining': team['total'] - team['used'],
                'used_by': user_id,
            }
        except Exception as e:
            logger.error("consume_credit 실패: %s", e, exc_info=True)
            return {}

    def get_team_usage(self, team_id: str) -> dict:
        """팀 전체 사용량 조회"""
        try:
            team = self._team_credits.get(team_id)
            if not team:
                return {'error': '팀을 찾을 수 없습니다.'}

            return {
                'total': team['total'],
                'used': team['used'],
                'remaining': team['total'] - team['used'],
            }
        except Exception as e:
            logger.error("get_team_usage 실패: %s", e, exc_info=True)
            return {}

    def get_member_usage(self, team_id: str) -> list:
        """멤버별 사용량 집계"""
        try:
            records = self._member_usage.get(team_id, [])
            # 멤버별 합산
            summary: dict[str, int] = {}
            for r in records:
                uid = r['user_id']
                summary[uid] = summary.get(uid, 0) + r['amount']

            return [{'user_id': uid, 'total_used': total} for uid, total in summary.items()]
        except Exception as e:
            logger.error("get_member_usage 실패: %s", e, exc_info=True)
            return []


team_billing_service = TeamBillingService()
