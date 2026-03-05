"""
콘텐츠 품질 트렌드 서비스 (F6-12)
시간에 따른 품질 점수 추이 추적
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('QualityTrendService')


class QualityTrendService:
    """콘텐츠 품질 점수 시계열 추적"""

    def __init__(self):
        # [{content_id, score, style, model, timestamp}]
        self._records: list[dict] = []

    def record_score(self, content_id: str, score: float, style: str = '',
                     model: str = '', timestamp: str | None = None) -> None:
        """품질 점수 기록 (0.0 ~ 100.0)"""
        self._records.append({
            'content_id': content_id,
            'score': max(0.0, min(100.0, score)),
            'style': style,
            'model': model,
            'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
        })

    def get_trend(self, days: int = 30, granularity: str = 'day') -> list[dict]:
        """일별 / 주별 평균 품질 점수 추세"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [r for r in self._records if self._parse_ts(r['timestamp']) >= cutoff]

        bucket_map: dict[str, list[float]] = defaultdict(list)
        for r in recent:
            key = self._bucket_key(r['timestamp'], granularity)
            bucket_map[key].append(r['score'])

        return [
            {
                'period': k,
                'avg_score': round(sum(v) / len(v), 2),
                'count': len(v),
                'min_score': round(min(v), 2),
                'max_score': round(max(v), 2),
            }
            for k, v in sorted(bucket_map.items())
        ]

    def get_style_quality(self, days: int = 30) -> list[dict]:
        """스타일별 평균 품질 점수"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [r for r in self._records if self._parse_ts(r['timestamp']) >= cutoff]

        style_map: dict[str, list[float]] = defaultdict(list)
        for r in recent:
            if r['style']:
                style_map[r['style']].append(r['score'])

        result = [
            {
                'style': style,
                'avg_score': round(sum(scores) / len(scores), 2),
                'count': len(scores),
            }
            for style, scores in style_map.items()
        ]
        result.sort(key=lambda x: -x['avg_score'])
        return result

    def get_model_quality(self, days: int = 30) -> list[dict]:
        """모델별 평균 품질 점수"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [r for r in self._records if self._parse_ts(r['timestamp']) >= cutoff]

        model_map: dict[str, list[float]] = defaultdict(list)
        for r in recent:
            if r['model']:
                model_map[r['model']].append(r['score'])

        result = [
            {
                'model': model,
                'avg_score': round(sum(scores) / len(scores), 2),
                'count': len(scores),
            }
            for model, scores in model_map.items()
        ]
        result.sort(key=lambda x: -x['avg_score'])
        return result

    def get_overall_stats(self) -> dict[str, Any]:
        """전체 품질 통계"""
        if not self._records:
            return {'total': 0, 'avg_score': 0}
        scores = [r['score'] for r in self._records]
        return {
            'total': len(scores),
            'avg_score': round(sum(scores) / len(scores), 2),
            'min_score': round(min(scores), 2),
            'max_score': round(max(scores), 2),
        }

    @staticmethod
    def _bucket_key(ts: str, granularity: str) -> str:
        date_part = ts[:10]
        if granularity == 'week':
            dt = datetime.fromisoformat(date_part)
            return dt.strftime('%Y-W%W')
        return date_part

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
