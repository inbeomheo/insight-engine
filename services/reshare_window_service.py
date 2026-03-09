"""
재공유 시점 분석 서비스

과거 콘텐츠의 성능 이력을 분석하여 재공유(reshare)에 최적인
시점과 예상 효과를 추천합니다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReshareWindow:
    """재공유 추천 시점"""
    content_id: str
    optimal_date: str         # ISO 날짜 형식 (YYYY-MM-DD)
    reason: str
    expected_boost: float     # 예상 참여도 향상 (0.0~1.0)


# 재공유 주기 전략
_RESHARE_INTERVALS = [
    {'days': 7, 'boost': 0.7, 'label': '1주 후'},
    {'days': 30, 'boost': 0.5, 'label': '1개월 후'},
    {'days': 90, 'boost': 0.4, 'label': '3개월 후'},
    {'days': 180, 'boost': 0.3, 'label': '6개월 후'},
    {'days': 365, 'boost': 0.2, 'label': '1년 후'},
]

# 에버그린 콘텐츠 키워드 (시간이 지나도 가치 유지)
_EVERGREEN_KEYWORDS = [
    '가이드', 'guide', '튜토리얼', 'tutorial', '방법', 'how to',
    '팁', 'tips', '베스트', 'best', '완벽', '입문', '기초',
    '핵심', '정리', '모음', '추천', '리스트',
]


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_date(date_str: str) -> Optional[datetime]:
    """다양한 날짜 형식을 파싱합니다."""
    formats = ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y/%m/%d', '%Y.%m.%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len('YYYY-MM-DDTHH:MM:SS')], fmt)
        except (ValueError, IndexError):
            continue
    return None


def _is_evergreen(content: dict) -> bool:
    """에버그린 콘텐츠인지 판단합니다."""
    title = str(content.get('title', '')).lower()
    tags = [str(t).lower() for t in content.get('tags', [])]
    content_type = str(content.get('type', content.get('content_type', ''))).lower()

    all_text = title + ' ' + ' '.join(tags) + ' ' + content_type
    return any(kw in all_text for kw in _EVERGREEN_KEYWORDS)


def _calculate_performance_score(content: dict) -> float:
    """콘텐츠의 과거 성능 점수를 계산합니다 (0~1)."""
    engagement = _safe_float(content.get('engagement', content.get('engagement_rate', 0)))
    views = _safe_float(content.get('views', 0))
    shares = _safe_float(content.get('shares', 0))

    # 정규화 (대략적 스케일)
    view_score = min(views / 10000, 1.0) if views > 0 else 0
    share_score = min(shares / 100, 1.0) if shares > 0 else 0
    eng_score = min(engagement, 1.0)

    return (eng_score * 0.5 + view_score * 0.3 + share_score * 0.2)


def _days_since_publish(content: dict, now: datetime) -> Optional[int]:
    """발행일로부터 경과일을 계산합니다."""
    date_str = content.get('published_date', content.get('date', content.get('created_at', '')))
    if not date_str:
        return None
    pub_date = _parse_date(str(date_str))
    if not pub_date:
        return None
    delta = (now - pub_date).days
    return max(delta, 0)


def _find_next_interval(days_elapsed: int) -> Optional[dict]:
    """경과일 기반으로 다음 재공유 시점을 찾습니다."""
    for interval in _RESHARE_INTERVALS:
        if days_elapsed < interval['days']:
            return interval
    return None


def find_reshare_windows(content_history: list) -> list:
    """콘텐츠 이력을 분석하여 재공유 최적 시점을 추천합니다.

    Args:
        content_history: 콘텐츠 딕셔너리 리스트. 각 항목에
                         id(또는 content_id), title, published_date(또는 date),
                         engagement, views, shares, tags 등 포함.

    Returns:
        ReshareWindow 리스트 (예상 부스트 내림차순)
    """
    if not content_history:
        return []

    now = datetime.now()
    windows = []

    for content in content_history:
        cid = str(content.get('id', content.get('content_id', '')))
        if not cid:
            continue

        days_elapsed = _days_since_publish(content, now)
        if days_elapsed is None:
            continue

        # 너무 최근이면 재공유 불필요 (최소 3일)
        if days_elapsed < 3:
            continue

        next_interval = _find_next_interval(days_elapsed)
        if not next_interval:
            # 모든 주기를 지남 → 1년 후 재공유
            optimal = now + timedelta(days=365 - (days_elapsed % 365))
            boost = 0.15
            reason = '오래된 콘텐츠 — 연간 재공유 주기'
        else:
            wait_days = next_interval['days'] - days_elapsed
            optimal = now + timedelta(days=max(wait_days, 1))
            boost = next_interval['boost']
            reason = f"{next_interval['label']} 재공유 추천 시점"

        # 성능 점수로 부스트 조정
        perf_score = _calculate_performance_score(content)
        boost *= (0.5 + perf_score * 0.5)

        # 에버그린 콘텐츠는 부스트 상향
        if _is_evergreen(content):
            boost = min(boost * 1.3, 1.0)
            reason += ' (에버그린 콘텐츠)'

        windows.append(ReshareWindow(
            content_id=cid,
            optimal_date=optimal.strftime('%Y-%m-%d'),
            reason=reason,
            expected_boost=round(boost, 4),
        ))

    # 예상 부스트 내림차순 정렬
    windows.sort(key=lambda w: w.expected_boost, reverse=True)
    return windows
