"""
콘텐츠 성과 추적 서비스 (F6-02)
콘텐츠별 조회수 / 공유수 / 클릭률 추적
"""
from datetime import datetime, timezone
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('PerformanceService')


class PerformanceService:
    """콘텐츠 성과 지표 추적 및 집계"""

    def __init__(self):
        # content_id → {views, shares, clicks, impressions, created_at}
        self._metrics: dict[str, dict] = {}

    def init_content(self, content_id: str, style: str = '', model: str = '') -> None:
        """새 콘텐츠 성과 추적 초기화"""
        if content_id not in self._metrics:
            self._metrics[content_id] = {
                'content_id': content_id,
                'style': style,
                'model': model,
                'views': 0,
                'shares': 0,
                'clicks': 0,
                'impressions': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }

    def record_view(self, content_id: str) -> None:
        """조회수 1 증가"""
        self._ensure(content_id)
        self._metrics[content_id]['views'] += 1

    def record_share(self, content_id: str) -> None:
        """공유수 1 증가"""
        self._ensure(content_id)
        self._metrics[content_id]['shares'] += 1

    def record_click(self, content_id: str) -> None:
        """클릭수 1 증가"""
        self._ensure(content_id)
        self._metrics[content_id]['clicks'] += 1

    def record_impression(self, content_id: str) -> None:
        """노출수 1 증가"""
        self._ensure(content_id)
        self._metrics[content_id]['impressions'] += 1

    def get_metrics(self, content_id: str) -> dict[str, Any]:
        """특정 콘텐츠 성과 지표 반환"""
        if content_id not in self._metrics:
            return {}
        m = self._metrics[content_id].copy()
        impressions = m['impressions']
        clicks = m['clicks']
        m['ctr'] = round(clicks / impressions * 100, 2) if impressions > 0 else 0.0
        return m

    def get_top_contents(self, by: str = 'views', limit: int = 10) -> list[dict]:
        """성과 기준 상위 콘텐츠 목록"""
        valid_fields = {'views', 'shares', 'clicks', 'impressions'}
        sort_key = by if by in valid_fields else 'views'

        items = list(self._metrics.values())
        items.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
        return items[:limit]

    def get_aggregate(self) -> dict[str, Any]:
        """전체 성과 집계"""
        total_views = sum(m['views'] for m in self._metrics.values())
        total_shares = sum(m['shares'] for m in self._metrics.values())
        total_clicks = sum(m['clicks'] for m in self._metrics.values())
        total_impressions = sum(m['impressions'] for m in self._metrics.values())
        return {
            'total_contents': len(self._metrics),
            'total_views': total_views,
            'total_shares': total_shares,
            'total_clicks': total_clicks,
            'total_impressions': total_impressions,
            'overall_ctr': round(
                total_clicks / total_impressions * 100, 2
            ) if total_impressions > 0 else 0.0,
        }

    def _ensure(self, content_id: str) -> None:
        if content_id not in self._metrics:
            self.init_content(content_id)
