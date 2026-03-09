"""
포스팅 추천 서비스

콘텐츠 발행 이력을 분석하여 최적의 포스팅 시간대를 추천합니다.
요일별·시간별 패턴을 통계적으로 분석하여 예상 참여도(engagement)가
높은 시간 슬롯을 반환합니다.
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PostingSlot:
    """추천 포스팅 시간 슬롯"""
    day_of_week: str          # 요일 (예: 'Monday', 'Tuesday')
    hour: int                 # 시간 (0~23)
    estimated_engagement: float  # 예상 참여도 (0.0~1.0)
    reason: str               # 추천 이유


# 요일 정규화 매핑
_DAY_ALIASES = {
    'mon': 'Monday', 'monday': 'Monday',
    'tue': 'Tuesday', 'tuesday': 'Tuesday',
    'wed': 'Wednesday', 'wednesday': 'Wednesday',
    'thu': 'Thursday', 'thursday': 'Thursday',
    'fri': 'Friday', 'friday': 'Friday',
    'sat': 'Saturday', 'saturday': 'Saturday',
    'sun': 'Sunday', 'sunday': 'Sunday',
}

_ORDERED_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# 일반적으로 참여도가 높은 시간대 가중치 (기본 프라이어)
_DEFAULT_HOUR_WEIGHT = {
    8: 0.6, 9: 0.7, 10: 0.65,
    12: 0.7, 13: 0.65,
    18: 0.75, 19: 0.8, 20: 0.85, 21: 0.8, 22: 0.7,
}


def _normalize_day(day: str) -> Optional[str]:
    """요일 문자열을 정규화합니다."""
    return _DAY_ALIASES.get(day.strip().lower())


def _extract_engagement(entry: dict) -> float:
    """이력 항목에서 참여도 점수를 추출합니다."""
    # engagement, likes, views 등 다양한 키 지원
    if 'engagement' in entry:
        return float(entry['engagement'])
    score = 0.0
    score += float(entry.get('likes', 0)) * 0.4
    score += float(entry.get('comments', 0)) * 0.6
    if entry.get('views', 0) > 0:
        score = score / float(entry['views'])
    return min(score, 1.0)


def _build_slot_stats(history: list) -> dict:
    """이력에서 (요일, 시간) → 참여도 리스트 맵을 구축합니다."""
    stats = defaultdict(list)
    for entry in history:
        day = entry.get('day_of_week') or entry.get('day', '')
        hour = entry.get('hour')
        if not day or hour is None:
            continue
        normalized = _normalize_day(str(day))
        if not normalized:
            continue
        try:
            h = int(hour)
        except (ValueError, TypeError):
            continue
        if not (0 <= h <= 23):
            continue
        eng = _extract_engagement(entry)
        stats[(normalized, h)].append(eng)
    return stats


def recommend_posting(history: list, top_n: int = 5) -> list:
    """콘텐츠 발행 이력을 분석하여 최적 포스팅 시간대를 추천합니다.

    Args:
        history: 발행 이력 딕셔너리 리스트.
                 각 항목에 day_of_week(또는 day), hour, engagement(또는 likes/comments/views) 포함.
        top_n: 반환할 추천 슬롯 수 (기본 5)

    Returns:
        PostingSlot 리스트 (참여도 내림차순 정렬)
    """
    if not history:
        return _generate_default_slots(top_n)

    slot_stats = _build_slot_stats(history)

    if not slot_stats:
        return _generate_default_slots(top_n)

    # 각 슬롯의 평균 참여도 계산
    scored_slots = []
    for (day, hour), engagements in slot_stats.items():
        avg_eng = sum(engagements) / len(engagements)
        count = len(engagements)
        # 표본 수가 많을수록 신뢰도 보너스
        confidence_bonus = min(count / 10, 0.1)
        final_score = min(avg_eng + confidence_bonus, 1.0)

        reason = f"{day} {hour}시 평균 참여도 {avg_eng:.2f} (데이터 {count}건)"
        scored_slots.append(PostingSlot(
            day_of_week=day,
            hour=hour,
            estimated_engagement=round(final_score, 4),
            reason=reason,
        ))

    # 참여도 내림차순 정렬 후 상위 N개
    scored_slots.sort(key=lambda s: s.estimated_engagement, reverse=True)
    return scored_slots[:top_n]


def _generate_default_slots(top_n: int) -> list:
    """이력이 없을 때 기본 추천 슬롯을 반환합니다."""
    defaults = [
        PostingSlot('Tuesday', 20, 0.85, '화요일 저녁은 일반적으로 참여도가 높습니다'),
        PostingSlot('Thursday', 19, 0.80, '목요일 저녁은 주중 피크 시간대입니다'),
        PostingSlot('Wednesday', 21, 0.78, '수요일 밤은 콘텐츠 소비가 활발합니다'),
        PostingSlot('Monday', 9, 0.70, '월요일 오전은 주초 관심도가 높습니다'),
        PostingSlot('Saturday', 10, 0.68, '토요일 오전은 여유롭게 콘텐츠를 소비합니다'),
        PostingSlot('Friday', 18, 0.65, '금요일 저녁은 주말 전 활동 시간입니다'),
        PostingSlot('Sunday', 20, 0.60, '일요일 저녁은 다음 주 준비 시간대입니다'),
    ]
    return defaults[:top_n]
