"""
개인화 콘텐츠 룸 서비스 — 사용자 프로필 기반 콘텐츠 큐레이션
"""

import uuid
from dataclasses import dataclass, field


VALID_LEVELS = {"beginner", "intermediate", "advanced"}

# 레벨별 난이도 순서 (필터링에 사용)
_LEVEL_ORDER = {"beginner": 1, "intermediate": 2, "advanced": 3}


@dataclass
class UserProfile:
    """사용자 프로필"""
    user_id: str
    interests: list = field(default_factory=list)          # list[str]
    preferred_formats: list = field(default_factory=list)   # list[str]
    reading_level: str = "intermediate"                     # beginner / intermediate / advanced
    language: str = "ko"


@dataclass
class ContentRoom:
    """개인화 콘텐츠 룸"""
    room_id: str
    user_id: str
    recommended: list = field(default_factory=list)   # list[dict]
    filters_applied: list = field(default_factory=list)  # list[str]


def _new_id(prefix: str = "room") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_profile(
    user_id: str,
    interests: list,
    formats: list,
    level: str = "intermediate",
    language: str = "ko",
) -> UserProfile:
    """프로필 생성

    Args:
        user_id: 사용자 ID
        interests: 관심사 목록
        formats: 선호 포맷 목록
        level: 읽기 수준 (beginner/intermediate/advanced)
        language: 선호 언어

    Returns:
        UserProfile: 생성된 프로필
    """
    if level not in VALID_LEVELS:
        raise ValueError(f"유효하지 않은 레벨: {level}. 허용: {VALID_LEVELS}")

    return UserProfile(
        user_id=user_id,
        interests=[i.lower().strip() for i in interests if i.strip()],
        preferred_formats=[f.lower().strip() for f in formats if f.strip()],
        reading_level=level,
        language=language,
    )


def score_relevance(content: dict, profile: UserProfile) -> float:
    """콘텐츠-프로필 관련성 점수 계산 (0~1)

    Args:
        content: 콘텐츠 딕셔너리 (tags, format, level, language 필드)
        profile: 사용자 프로필

    Returns:
        float: 관련성 점수 (0~1)
    """
    score = 0.0
    max_score = 0.0

    # 1. 관심사 매칭 (가중치 0.4)
    max_score += 0.4
    content_tags = [t.lower().strip() for t in content.get("tags", [])]
    if profile.interests and content_tags:
        matched = sum(1 for tag in content_tags if tag in profile.interests)
        score += 0.4 * (matched / max(len(content_tags), 1))

    # 2. 포맷 매칭 (가중치 0.2)
    max_score += 0.2
    content_format = content.get("format", "").lower().strip()
    if content_format and profile.preferred_formats:
        if content_format in profile.preferred_formats:
            score += 0.2

    # 3. 레벨 호환성 (가중치 0.25)
    max_score += 0.25
    content_level = content.get("level", "intermediate")
    if content_level in VALID_LEVELS:
        user_order = _LEVEL_ORDER.get(profile.reading_level, 2)
        content_order = _LEVEL_ORDER.get(content_level, 2)
        diff = abs(user_order - content_order)
        if diff == 0:
            score += 0.25
        elif diff == 1:
            score += 0.15
        # diff == 2이면 0점

    # 4. 언어 매칭 (가중치 0.15)
    max_score += 0.15
    content_lang = content.get("language", "ko")
    if content_lang == profile.language:
        score += 0.15

    # 0~1 범위 보정
    return round(min(score / max_score, 1.0) if max_score > 0 else 0.0, 3)


def curate_room(profile: UserProfile, content_pool: list) -> ContentRoom:
    """콘텐츠 큐레이션 — 관심사 매칭 + 레벨 필터 + 점수 정렬

    Args:
        profile: 사용자 프로필
        content_pool: 콘텐츠 후보 목록

    Returns:
        ContentRoom: 큐레이션된 콘텐츠 룸
    """
    filters_applied = []

    # 점수 계산
    scored = []
    for item in content_pool:
        rel_score = score_relevance(item, profile)
        scored.append((rel_score, item))

    # 레벨 필터: 사용자 레벨에서 1단계 이내만 허용
    user_order = _LEVEL_ORDER.get(profile.reading_level, 2)
    filtered = []
    for rel_score, item in scored:
        content_level = item.get("level", "intermediate")
        content_order = _LEVEL_ORDER.get(content_level, 2)
        if abs(user_order - content_order) <= 1:
            filtered.append((rel_score, item))
    filters_applied.append(f"level_filter:{profile.reading_level}")

    # 언어 필터 (같은 언어 우선, 다른 언어도 포함)
    filters_applied.append(f"language:{profile.language}")

    # 점수 내림차순 정렬
    filtered.sort(key=lambda x: x[0], reverse=True)

    recommended = []
    for rel_score, item in filtered:
        entry = dict(item)
        entry["relevance_score"] = rel_score
        recommended.append(entry)

    return ContentRoom(
        room_id=_new_id(),
        user_id=profile.user_id,
        recommended=recommended,
        filters_applied=filters_applied,
    )


def update_interests(profile: UserProfile, new_interests: list) -> UserProfile:
    """관심사 업데이트 — 기존 관심사에 새 관심사 병합 (중복 제거)

    Args:
        profile: 기존 프로필
        new_interests: 추가할 관심사 목록

    Returns:
        UserProfile: 업데이트된 프로필
    """
    normalized = [i.lower().strip() for i in new_interests if i.strip()]
    merged = list(dict.fromkeys(profile.interests + normalized))  # 순서 유지 + 중복 제거

    return UserProfile(
        user_id=profile.user_id,
        interests=merged,
        preferred_formats=profile.preferred_formats,
        reading_level=profile.reading_level,
        language=profile.language,
    )
