"""
코호트 분석 서비스 (F4-13)
가입 주차별 잔존율 / LTV 계산
"""
from collections import defaultdict
from datetime import datetime, timezone
from services.logging_config import ServiceLogger

logger = ServiceLogger('CohortService')


class CohortService:
    """코호트별 잔존율 및 LTV 분석"""

    def __init__(self):
        # 사용자 이벤트 저장: [{user_id, event, timestamp, revenue?}]
        self._events: list[dict] = []

    def record_event(self, user_id: str, event: str, timestamp: str | None = None, revenue: float = 0.0):
        """이벤트 기록 (signup, active, purchase 등)"""
        self._events.append({
            'user_id': user_id,
            'event': event,
            'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
            'revenue': revenue,
        })

    def get_retention(self, cohort_period: str = 'week') -> dict:
        """코호트별 잔존율 계산

        Args:
            cohort_period: 'week' 또는 'month'
        """
        # 사용자별 가입일 추출
        signup_dates: dict[str, str] = {}
        active_periods: dict[str, set[str]] = defaultdict(set)

        for ev in self._events:
            uid = ev['user_id']
            ts = ev['timestamp'][:10]  # YYYY-MM-DD

            if ev['event'] == 'signup':
                signup_dates[uid] = ts

            if ev['event'] == 'active':
                period_key = self._get_period_key(ts, cohort_period)
                active_periods[uid].add(period_key)

        # 코호트별 잔존율 집계
        cohorts: dict[str, dict] = defaultdict(lambda: {'total': 0, 'retained': defaultdict(int)})

        for uid, signup_date in signup_dates.items():
            cohort_key = self._get_period_key(signup_date, cohort_period)
            cohorts[cohort_key]['total'] += 1

            for period in active_periods.get(uid, set()):
                cohorts[cohort_key]['retained'][period] += 1

        return dict(cohorts)

    def get_ltv(self) -> dict:
        """사용자별 LTV(생애 매출) 집계"""
        user_revenue: dict[str, float] = defaultdict(float)

        for ev in self._events:
            if ev.get('revenue', 0) > 0:
                user_revenue[ev['user_id']] += ev['revenue']

        if not user_revenue:
            return {'average_ltv': 0, 'total_users': 0, 'total_revenue': 0}

        total = sum(user_revenue.values())
        return {
            'average_ltv': round(total / len(user_revenue), 2),
            'total_users': len(user_revenue),
            'total_revenue': round(total, 2),
        }

    @staticmethod
    def _get_period_key(date_str: str, period: str) -> str:
        """날짜를 기간 키로 변환"""
        dt = datetime.fromisoformat(date_str)
        if period == 'month':
            return dt.strftime('%Y-%m')
        # week
        iso_year, iso_week, _ = dt.isocalendar()
        return f'{iso_year}-W{iso_week:02d}'


cohort_service = CohortService()
