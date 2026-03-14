"""
스타일별 성과 비교 서비스 (F6-13)
14개 콘텐츠 스타일별 평균 품질 / 성과 지표 비교
"""
from collections import defaultdict
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('StylePerformanceService')


class StylePerformanceService:
    """스타일별 성과 지표 집계 및 비교"""

    def __init__(self):
        # style → [{quality_score, views, shares, tokens, duration_ms}]
        self._data: dict[str, list[dict]] = defaultdict(list)

    def record(self, style: str, quality_score: float = 0.0, views: int = 0,
               shares: int = 0, tokens: int = 0, duration_ms: float = 0.0) -> None:
        """스타일 성과 데이터 기록"""
        self._data[style].append({
            'quality_score': quality_score,
            'views': views,
            'shares': shares,
            'tokens': tokens,
            'duration_ms': duration_ms,
        })

    def get_comparison(self) -> list[dict]:
        """전체 스타일 성과 비교 테이블"""
        result = []
        for style, records in self._data.items():
            n = len(records)
            result.append({
                'style': style,
                'count': n,
                'avg_quality': round(sum(r['quality_score'] for r in records) / n, 2),
                'avg_views': round(sum(r['views'] for r in records) / n, 1),
                'avg_shares': round(sum(r['shares'] for r in records) / n, 1),
                'avg_tokens': round(sum(r['tokens'] for r in records) / n, 0),
                'avg_duration_ms': round(sum(r['duration_ms'] for r in records) / n, 1),
            })
        result.sort(key=lambda x: -x['avg_quality'])
        return result

    def get_top_style(self, by: str = 'avg_quality') -> dict[str, Any] | None:
        """특정 지표 기준 최고 성과 스타일"""
        comparison = self.get_comparison()
        if not comparison:
            return None
        valid_keys = {'avg_quality', 'avg_views', 'avg_shares'}
        key = by if by in valid_keys else 'avg_quality'
        return max(comparison, key=lambda x: x.get(key, 0))

    def get_style_detail(self, style: str) -> dict[str, Any]:
        """특정 스타일 상세 통계"""
        records = self._data.get(style, [])
        if not records:
            return {'style': style, 'count': 0}
        n = len(records)
        quality_scores = [r['quality_score'] for r in records]
        return {
            'style': style,
            'count': n,
            'avg_quality': round(sum(quality_scores) / n, 2),
            'min_quality': round(min(quality_scores), 2),
            'max_quality': round(max(quality_scores), 2),
            'avg_views': round(sum(r['views'] for r in records) / n, 1),
            'avg_tokens': round(sum(r['tokens'] for r in records) / n, 0),
        }
