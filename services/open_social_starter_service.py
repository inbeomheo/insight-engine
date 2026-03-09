"""
오픈소셜 스타터팩 서비스 — 소셜 미디어 시작 키트 생성
"""

import uuid
from dataclasses import dataclass, field


PLATFORM_CONFIGS = {
    'twitter': {'char_limit': 280, 'hashtag_count': 3, 'schedule': ['오전 9시', '오후 1시', '저녁 7시']},
    'instagram': {'char_limit': 2200, 'hashtag_count': 10, 'schedule': ['오전 11시', '오후 6시']},
    'linkedin': {'char_limit': 3000, 'hashtag_count': 5, 'schedule': ['오전 8시', '오후 12시']},
    'threads': {'char_limit': 500, 'hashtag_count': 3, 'schedule': ['오전 10시', '오후 5시']},
    'youtube': {'char_limit': 5000, 'hashtag_count': 5, 'schedule': ['오후 2시', '토요일 오전']},
}


@dataclass
class SocialProfile:
    """소셜 프로필"""
    platform: str
    handle: str
    bio: str
    hashtags: list[str]
    posting_schedule: list[str]


@dataclass
class StarterPack:
    """스타터팩"""
    pack_id: str
    profiles: list[SocialProfile]
    content_calendar: list[dict]
    tips: list[str]


def create_starter_pack(brand_name: str, platforms: list[str]) -> StarterPack:
    """플랫폼별 프로필 템플릿 생성"""
    profiles = []

    for platform in platforms:
        config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['twitter'])
        bio = generate_bio(brand_name, platform)
        hashtags = suggest_hashtags(brand_name, platform)
        profile = SocialProfile(
            platform=platform,
            handle=f"@{brand_name.lower().replace(' ', '_')}",
            bio=bio,
            hashtags=hashtags,
            posting_schedule=config['schedule']
        )
        profiles.append(profile)

    tips = [
        f'{brand_name} 브랜드 일관성을 유지하세요.',
        '정기적인 게시 일정을 지키세요.',
        '팔로워와 적극적으로 소통하세요.',
        '분석 데이터를 주기적으로 확인하세요.',
    ]

    return StarterPack(
        pack_id=str(uuid.uuid4())[:8],
        profiles=profiles,
        content_calendar=[],
        tips=tips
    )


def generate_bio(brand_name: str, platform: str) -> str:
    """플랫폼별 바이오 생성"""
    bios = {
        'twitter': f"{brand_name} | 최신 소식과 인사이트를 공유합니다",
        'instagram': f"{brand_name}\n창의적인 콘텐츠와 비하인드 스토리",
        'linkedin': f"{brand_name} - 전문적인 인사이트와 업계 트렌드를 제공합니다. 함께 성장합시다.",
        'threads': f"{brand_name} - 자유로운 대화와 일상 공유",
        'youtube': f"{brand_name} 공식 채널 | 유익하고 재미있는 영상 콘텐츠",
    }
    return bios.get(platform, f"{brand_name} 공식 계정")


def suggest_hashtags(topic: str, platform: str) -> list[str]:
    """해시태그 추천"""
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['twitter'])
    count = config['hashtag_count']

    base_tags = [
        f"#{topic.replace(' ', '')}",
        '#콘텐츠',
        '#브랜드',
        '#마케팅',
        '#트렌드',
        '#소통',
        '#일상',
        '#팔로우',
        '#좋아요',
        '#공유',
    ]

    return base_tags[:count]


def create_content_calendar(pack: StarterPack, days: int = 7) -> list[dict]:
    """콘텐츠 캘린더 생성"""
    calendar = []
    content_types = ['텍스트', '이미지', '영상', '스토리', '설문']

    for day in range(1, days + 1):
        for profile in pack.profiles:
            calendar.append({
                'day': day,
                'platform': profile.platform,
                'content_type': content_types[(day - 1) % len(content_types)],
                'topic': f"Day {day} 콘텐츠",
                'hashtags': profile.hashtags[:3],
                'time': profile.posting_schedule[0] if profile.posting_schedule else '오전 9시'
            })

    return calendar
