"""
사용자 세그먼트 서비스 (F4-21)
행동 기반 사용자 분류
"""
from datetime import datetime, timezone
from services.logging_config import ServiceLogger

logger = ServiceLogger('SegmentService')


# 기본 세그먼트 정의
DEFAULT_SEGMENTS = {
    'power_user': {
        'label': '파워 유저',
        'condition': lambda stats: stats.get('monthly_uses', 0) >= 50,
    },
    'regular': {
        'label': '일반 사용자',
        'condition': lambda stats: 10 <= stats.get('monthly_uses', 0) < 50,
    },
    'casual': {
        'label': '가벼운 사용자',
        'condition': lambda stats: 1 <= stats.get('monthly_uses', 0) < 10,
    },
    'dormant': {
        'label': '휴면 사용자',
        'condition': lambda stats: stats.get('days_since_last', 999) > 30,
    },
    'churned': {
        'label': '이탈 사용자',
        'condition': lambda stats: stats.get('days_since_last', 999) > 90,
    },
}


class SegmentService:
    """사용자 세그먼트 분류"""

    def __init__(self):
        self._user_stats: dict[str, dict] = {}

    def update_stats(self, user_id: str, stats: dict):
        """사용자 통계 업데이트

        Args:
            stats: {monthly_uses: int, days_since_last: int, total_spent: float, ...}
        """
        self._user_stats[user_id] = {
            **stats,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

    def classify_user(self, user_id: str) -> list[str]:
        """사용자를 세그먼트로 분류 (복수 세그먼트 가능)"""
        if user_id not in self._user_stats:
            return ['unknown']

        stats = self._user_stats[user_id]
        segments = []

        for seg_id, seg_def in DEFAULT_SEGMENTS.items():
            if seg_def['condition'](stats):
                segments.append(seg_id)

        return segments or ['unknown']

    def get_segment_counts(self) -> dict[str, int]:
        """세그먼트별 사용자 수 집계"""
        counts: dict[str, int] = {seg_id: 0 for seg_id in DEFAULT_SEGMENTS}
        counts['unknown'] = 0

        for user_id in self._user_stats:
            for seg in self.classify_user(user_id):
                counts[seg] = counts.get(seg, 0) + 1

        return counts

    def get_users_in_segment(self, segment_id: str) -> list[str]:
        """특정 세그먼트에 속한 사용자 목록"""
        return [
            uid for uid in self._user_stats
            if segment_id in self.classify_user(uid)
        ]


segment_service = SegmentService()
