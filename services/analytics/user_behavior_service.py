"""
사용자 행동 분석 서비스 (F6-11)
기능별 사용 빈도, 세션 길이, 클릭 경로 추적
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('UserBehaviorService')


class UserBehaviorService:
    """사용자 행동 이벤트 수집 및 분석"""

    def __init__(self):
        # [{user_id, session_id, feature, action, timestamp}]
        self._events: list[dict] = []
        # session_id → {start, end, user_id}
        self._sessions: dict[str, dict] = {}

    def record(self, feature: str, action: str,
               user_id: str = 'anonymous',
               session_id: str = '',
               timestamp: str | None = None) -> None:
        """기능 사용 이벤트 기록"""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        self._events.append({
            'user_id': user_id,
            'session_id': session_id,
            'feature': feature,
            'action': action,
            'timestamp': ts,
        })
        # 세션 갱신
        if session_id:
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'start': ts,
                    'end': ts,
                    'event_count': 0,
                }
            self._sessions[session_id]['end'] = ts
            self._sessions[session_id]['event_count'] += 1

    def get_feature_frequency(self, days: int = 30) -> list[dict]:
        """기능별 사용 빈도 (내림차순)"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in self._events if self._parse_ts(e['timestamp']) >= cutoff]

        freq: dict[str, int] = defaultdict(int)
        for e in recent:
            freq[e['feature']] += 1

        return [
            {'feature': f, 'count': c}
            for f, c in sorted(freq.items(), key=lambda x: -x[1])
        ]

    def get_action_breakdown(self, feature: str, days: int = 30) -> dict[str, Any]:
        """특정 기능의 액션별 분포"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = [
            e for e in self._events
            if e['feature'] == feature and self._parse_ts(e['timestamp']) >= cutoff
        ]
        action_map: dict[str, int] = defaultdict(int)
        for e in events:
            action_map[e['action']] += 1
        return {
            'feature': feature,
            'total': len(events),
            'actions': dict(action_map),
        }

    def get_session_stats(self) -> dict[str, Any]:
        """세션 통계 (평균 길이, 평균 이벤트 수)"""
        sessions = list(self._sessions.values())
        if not sessions:
            return {'total_sessions': 0, 'avg_duration_sec': 0, 'avg_events': 0}

        durations = []
        for s in sessions:
            try:
                start = datetime.fromisoformat(s['start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(s['end'].replace('Z', '+00:00'))
                durations.append((end - start).total_seconds())
            except Exception:
                pass

        avg_duration = sum(durations) / len(durations) if durations else 0
        avg_events = sum(s['event_count'] for s in sessions) / len(sessions)

        return {
            'total_sessions': len(sessions),
            'avg_duration_sec': round(avg_duration, 1),
            'avg_events': round(avg_events, 1),
        }

    def get_user_activity(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """특정 사용자의 활동 요약"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = [
            e for e in self._events
            if e['user_id'] == user_id and self._parse_ts(e['timestamp']) >= cutoff
        ]
        feature_counts: dict[str, int] = defaultdict(int)
        for e in events:
            feature_counts[e['feature']] += 1
        return {
            'user_id': user_id,
            'total_events': len(events),
            'features_used': dict(feature_counts),
        }

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
