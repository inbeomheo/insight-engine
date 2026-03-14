"""
운영 대시보드 고도화 서비스 (F6-01)
30일 / 스타일별 / 모델별 집계 통계 제공
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('DashboardService')


class DashboardService:
    """운영 대시보드 통계 집계"""

    def __init__(self):
        # 생성 이벤트 저장: {timestamp, style, model, tokens, duration_ms, success}
        self._events: list[dict] = []

    def record_generation(self, style: str, model: str, tokens: int,
                          duration_ms: float, success: bool = True,
                          timestamp: str | None = None) -> None:
        """콘텐츠 생성 이벤트 기록"""
        self._events.append({
            'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
            'style': style,
            'model': model,
            'tokens': tokens,
            'duration_ms': duration_ms,
            'success': success,
        })

    def get_summary(self, days: int = 30) -> dict[str, Any]:
        """최근 N일 요약 통계"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in self._events if self._parse_ts(e['timestamp']) >= cutoff]

        total = len(recent)
        success = sum(1 for e in recent if e['success'])
        total_tokens = sum(e['tokens'] for e in recent)
        avg_duration = (
            sum(e['duration_ms'] for e in recent) / total if total else 0.0
        )

        return {
            'period_days': days,
            'total_generations': total,
            'success_count': success,
            'failure_count': total - success,
            'success_rate': round(success / total * 100, 1) if total else 0.0,
            'total_tokens': total_tokens,
            'avg_duration_ms': round(avg_duration, 1),
        }

    def get_style_stats(self, days: int = 30) -> list[dict]:
        """스타일별 생성 통계"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in self._events if self._parse_ts(e['timestamp']) >= cutoff]

        style_map: dict[str, list[dict]] = defaultdict(list)
        for e in recent:
            style_map[e['style']].append(e)

        result = []
        for style, events in sorted(style_map.items()):
            total = len(events)
            success = sum(1 for e in events if e['success'])
            result.append({
                'style': style,
                'count': total,
                'success_rate': round(success / total * 100, 1) if total else 0.0,
                'avg_tokens': round(sum(e['tokens'] for e in events) / total, 0) if total else 0,
            })
        return result

    def get_model_stats(self, days: int = 30) -> list[dict]:
        """모델별 생성 통계"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in self._events if self._parse_ts(e['timestamp']) >= cutoff]

        model_map: dict[str, list[dict]] = defaultdict(list)
        for e in recent:
            model_map[e['model']].append(e)

        result = []
        for model, events in sorted(model_map.items()):
            total = len(events)
            result.append({
                'model': model,
                'count': total,
                'avg_duration_ms': round(
                    sum(e['duration_ms'] for e in events) / total, 1
                ) if total else 0.0,
                'avg_tokens': round(sum(e['tokens'] for e in events) / total, 0) if total else 0,
            })
        return result

    def get_daily_trend(self, days: int = 30) -> list[dict]:
        """일별 생성 수 추세"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [e for e in self._events if self._parse_ts(e['timestamp']) >= cutoff]

        daily: dict[str, int] = defaultdict(int)
        for e in recent:
            day = e['timestamp'][:10]
            daily[day] += 1

        return [{'date': k, 'count': v} for k, v in sorted(daily.items())]

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
