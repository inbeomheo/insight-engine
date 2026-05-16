"""
최적 발행 시간 추천 서비스

콘텐츠 유형/카테고리별 최적 발행 시간을 추천합니다.
플랫폼별 트래픽 패턴 데이터 기반 규칙 추천.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

# 플랫폼별 최적 발행 시간 (요일, 시간 기반)
# 데이터 출처: 업계 벤치마크 (HubSpot, Hootsuite 등 집계)
PLATFORM_SCHEDULES = {
    'blog': {
        'label': '블로그',
        'best_days': ['화', '수', '목'],
        'best_hours': [9, 10, 11],
        'avoid_days': ['토', '일'],
        'avoid_hours': [0, 1, 2, 3, 4, 5],
        'reason': '직장인 출근 시간대 트래픽이 가장 높음',
    },
    'newsletter': {
        'label': '뉴스레터',
        'best_days': ['화', '수'],
        'best_hours': [7, 8, 9],
        'avoid_days': ['금', '토', '일'],
        'avoid_hours': [12, 13, 14],
        'reason': '이메일 오픈율이 아침 출근 시간대에 가장 높음',
    },
    'sns': {
        'label': 'SNS',
        'best_days': ['수', '목', '금'],
        'best_hours': [12, 13, 18, 19, 20],
        'avoid_days': ['일'],
        'avoid_hours': [2, 3, 4, 5],
        'reason': '점심시간과 퇴근 후 시간대 참여율이 높음',
    },
    'youtube': {
        'label': 'YouTube',
        'best_days': ['목', '금'],
        'best_hours': [14, 15, 16, 17],
        'avoid_days': ['월'],
        'avoid_hours': [0, 1, 2, 3, 4, 5, 6],
        'reason': '주말 전 오후에 업로드하면 주말 시청 트래픽 확보',
    },
    'technical': {
        'label': '기술 블로그',
        'best_days': ['화', '수'],
        'best_hours': [10, 11, 14, 15],
        'avoid_days': ['토', '일'],
        'avoid_hours': [18, 19, 20, 21, 22, 23],
        'reason': '개발자 업무 시간대 트래픽이 집중됨',
    },
}

_DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']


def suggest_publish_time(content_type: str = 'blog',
                         platforms: List[str] = None,
                         timezone_label: str = 'KST') -> dict:
    """콘텐츠 유형별 최적 발행 시간을 추천합니다.

    Args:
        content_type: 콘텐츠 유형 (blog/newsletter/sns/youtube/technical)
        platforms: 복수 플랫폼 (지정 시 교집합 추천)
        timezone_label: 시간대 라벨

    Returns:
        {
            'recommendations': [{'platform': str, 'best_days': [str], 'best_hours': [str], 'best_slot': str, 'reason': str}],
            'combined_best': {'days': [str], 'hours': [int]},
            'avoid': {'days': [str], 'hours': [int]},
            'timezone': str,
        }
    """
    target_platforms = platforms or [content_type]
    recommendations = []
    all_best_days = []
    all_best_hours = []
    all_avoid_days = []
    all_avoid_hours = []

    for platform in target_platforms:
        schedule = PLATFORM_SCHEDULES.get(platform, PLATFORM_SCHEDULES.get('blog'))
        if not schedule:
            continue

        best_day = schedule['best_days'][0] if schedule['best_days'] else '화'
        best_hour = schedule['best_hours'][0] if schedule['best_hours'] else 10

        recommendations.append({
            'platform': schedule['label'],
            'best_days': schedule['best_days'],
            'best_hours': [f'{h}:00' for h in schedule['best_hours']],
            'best_slot': f'{best_day}요일 {best_hour}:00',
            'reason': schedule['reason'],
        })

        all_best_days.extend(schedule['best_days'])
        all_best_hours.extend(schedule['best_hours'])
        all_avoid_days.extend(schedule.get('avoid_days', []))
        all_avoid_hours.extend(schedule.get('avoid_hours', []))

    # 교집합이 아닌 빈도 기반 추천 (다수 플랫폼에서 겹치는 시간)
    day_freq = {}
    for d in all_best_days:
        day_freq[d] = day_freq.get(d, 0) + 1
    hour_freq = {}
    for h in all_best_hours:
        hour_freq[h] = hour_freq.get(h, 0) + 1

    combined_days = sorted(day_freq.keys(), key=lambda d: day_freq[d], reverse=True)[:3]
    combined_hours = sorted(hour_freq.keys(), key=lambda h: hour_freq[h], reverse=True)[:3]

    return {
        'recommendations': recommendations,
        'combined_best': {
            'days': combined_days,
            'hours': sorted(combined_hours),
        },
        'avoid': {
            'days': list(set(all_avoid_days)),
            'hours': sorted(set(all_avoid_hours)),
        },
        'timezone': timezone_label,
    }


def get_platform_options() -> list:
    """사용 가능한 플랫폼 목록."""
    return [
        {'id': pid, 'label': schedule['label']}
        for pid, schedule in PLATFORM_SCHEDULES.items()
    ]
