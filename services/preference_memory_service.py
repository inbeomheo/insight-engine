"""
선호 메모리 서비스 — 사용자 선호도를 학습/저장/활용
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Preference:
    """선호도 항목"""
    pref_id: str
    user_id: str
    category: str
    value: str
    weight: float = 1.0
    updated_at: str = ""


@dataclass
class PreferenceProfile:
    """선호도 프로필"""
    user_id: str
    preferences: list[Preference] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


def _now_iso() -> str:
    """현재 시간 ISO 형식 반환"""
    return datetime.now().isoformat()


def _create_profile(user_id: str) -> PreferenceProfile:
    """빈 선호도 프로필 생성"""
    return PreferenceProfile(user_id=user_id, preferences=[], history=[])


def record_preference(
    profile: PreferenceProfile,
    category: str,
    value: str,
    weight: float = 1.0,
) -> PreferenceProfile:
    """선호 기록 (동일 카테고리+값 기존 항목 업데이트)

    Args:
        profile: 대상 프로필
        category: 선호 카테고리 (e.g. style, language, length)
        value: 선호 값
        weight: 가중치 (0.0~1.0)

    Returns:
        업데이트된 프로필
    """
    weight = max(0.0, min(1.0, weight))
    now = _now_iso()

    # 동일 카테고리+값 기존 항목 찾기
    for pref in profile.preferences:
        if pref.category == category and pref.value == value:
            old_weight = pref.weight
            pref.weight = weight
            pref.updated_at = now
            # 히스토리 기록
            profile.history.append({
                "action": "updated",
                "category": category,
                "value": value,
                "old_weight": old_weight,
                "new_weight": weight,
                "timestamp": now,
            })
            return profile

    # 새 선호 추가
    pref = Preference(
        pref_id=str(uuid.uuid4()),
        user_id=profile.user_id,
        category=category,
        value=value,
        weight=weight,
        updated_at=now,
    )
    profile.preferences.append(pref)
    profile.history.append({
        "action": "added",
        "category": category,
        "value": value,
        "weight": weight,
        "timestamp": now,
    })
    return profile


def get_preferences(
    profile: PreferenceProfile, category: str | None = None
) -> list[Preference]:
    """카테고리별 선호 조회

    Args:
        profile: 대상 프로필
        category: 필터할 카테고리 (None이면 전체)

    Returns:
        매칭된 선호 목록 (가중치 내림차순)
    """
    if category is None:
        prefs = list(profile.preferences)
    else:
        prefs = [p for p in profile.preferences if p.category == category]

    prefs.sort(key=lambda p: p.weight, reverse=True)
    return prefs


def apply_preferences(
    profile: PreferenceProfile, options: list[dict]
) -> list[dict]:
    """선호 기반 옵션 정렬

    각 옵션의 키-값이 선호와 매칭되면 가중치 합산 후 정렬.

    Args:
        profile: 대상 프로필
        options: 정렬할 옵션 목록 (dict)

    Returns:
        선호도 점수 내림차순 정렬된 옵션 목록
    """
    if not profile.preferences or not options:
        return list(options)

    # 선호 맵 구축: (category, value) -> weight
    pref_map: dict[tuple[str, str], float] = {}
    for pref in profile.preferences:
        pref_map[(pref.category, pref.value)] = pref.weight

    # 각 옵션 점수 계산
    scored: list[tuple[float, int, dict]] = []
    for idx, option in enumerate(options):
        score = 0.0
        for key, val in option.items():
            val_str = str(val)
            if (key, val_str) in pref_map:
                score += pref_map[(key, val_str)]
        scored.append((score, idx, option))

    # 점수 내림차순, 원래 순서 유지 (안정 정렬)
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [opt for _, _, opt in scored]


def decay_preferences(
    profile: PreferenceProfile, decay_rate: float = 0.1
) -> PreferenceProfile:
    """시간 기반 가중치 감쇠

    모든 선호의 가중치를 decay_rate만큼 감소.

    Args:
        profile: 대상 프로필
        decay_rate: 감쇠율 (0.0~1.0)

    Returns:
        업데이트된 프로필
    """
    decay_rate = max(0.0, min(1.0, decay_rate))

    to_remove: list[str] = []
    for pref in profile.preferences:
        pref.weight = round(pref.weight * (1.0 - decay_rate), 4)
        if pref.weight < 0.01:
            to_remove.append(pref.pref_id)

    # 가중치가 거의 0인 선호 제거
    if to_remove:
        profile.preferences = [
            p for p in profile.preferences if p.pref_id not in to_remove
        ]

    return profile


def export_profile(profile: PreferenceProfile) -> dict:
    """프로필 내보내기

    Args:
        profile: 대상 프로필

    Returns:
        직렬화 가능한 딕셔너리
    """
    return {
        "user_id": profile.user_id,
        "preferences": [asdict(p) for p in profile.preferences],
        "history": list(profile.history),
        "total_preferences": len(profile.preferences),
        "categories": list(set(p.category for p in profile.preferences)),
    }
