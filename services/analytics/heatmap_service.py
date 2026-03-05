"""
히트맵 분석 서비스 (F6-09)
콘텐츠 읽기 패턴 (스크롤 깊이 / 클릭 좌표) 집계
"""
from collections import defaultdict
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('HeatmapService')


class HeatmapService:
    """콘텐츠 읽기 패턴 히트맵 집계"""

    def __init__(self):
        # content_id → [{'x': int, 'y': int, 'type': 'click'|'scroll'}]
        self._events: dict[str, list[dict]] = defaultdict(list)

    def record_click(self, content_id: str, x: int, y: int) -> None:
        """클릭 좌표 기록"""
        self._events[content_id].append({'x': x, 'y': y, 'type': 'click'})

    def record_scroll(self, content_id: str, depth_pct: float) -> None:
        """스크롤 깊이(%) 기록 (0~100)"""
        depth = max(0, min(100, int(depth_pct)))
        self._events[content_id].append({'depth_pct': depth, 'type': 'scroll'})

    def get_click_heatmap(self, content_id: str, grid_size: int = 10) -> dict[str, Any]:
        """클릭 히트맵 데이터 반환 (grid_size × grid_size 셀로 집계)"""
        events = [e for e in self._events.get(content_id, []) if e['type'] == 'click']
        if not events:
            return {'content_id': content_id, 'cells': [], 'total_clicks': 0}

        cell_map: dict[tuple, int] = defaultdict(int)
        for e in events:
            cell_x = e['x'] // grid_size
            cell_y = e['y'] // grid_size
            cell_map[(cell_x, cell_y)] += 1

        cells = [
            {'cell_x': cx, 'cell_y': cy, 'count': cnt}
            for (cx, cy), cnt in cell_map.items()
        ]
        cells.sort(key=lambda x: -x['count'])

        return {
            'content_id': content_id,
            'grid_size': grid_size,
            'total_clicks': len(events),
            'cells': cells,
        }

    def get_scroll_distribution(self, content_id: str) -> dict[str, Any]:
        """스크롤 깊이 분포 (10% 구간별 집계)"""
        events = [e for e in self._events.get(content_id, []) if e['type'] == 'scroll']
        if not events:
            return {'content_id': content_id, 'buckets': [], 'avg_depth_pct': 0}

        buckets: dict[str, int] = defaultdict(int)
        for e in events:
            bucket_label = f"{(e['depth_pct'] // 10) * 10}-{(e['depth_pct'] // 10) * 10 + 10}%"
            buckets[bucket_label] += 1

        avg = sum(e['depth_pct'] for e in events) / len(events)

        return {
            'content_id': content_id,
            'total_scroll_events': len(events),
            'avg_depth_pct': round(avg, 1),
            'buckets': [
                {'range': k, 'count': v}
                for k, v in sorted(buckets.items())
            ],
        }

    def get_aggregate_scroll(self) -> dict[str, Any]:
        """전체 콘텐츠 평균 스크롤 깊이"""
        all_scroll = [
            e['depth_pct']
            for events in self._events.values()
            for e in events
            if e['type'] == 'scroll'
        ]
        if not all_scroll:
            return {'avg_depth_pct': 0, 'total_events': 0}
        return {
            'avg_depth_pct': round(sum(all_scroll) / len(all_scroll), 1),
            'total_events': len(all_scroll),
        }
