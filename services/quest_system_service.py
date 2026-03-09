"""
퀘스트 시스템 서비스

시청 퀘스트 생성, 진행도 추적, 배지 부여를 관리합니다.
순수 파이썬 인메모리 구현, 외부 의존성 없음.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Milestone:
    """퀘스트 마일스톤"""
    milestone_id: str
    name: str
    xp: int  # 경험치
    completed: bool = False


@dataclass
class Quest:
    """퀘스트"""
    quest_id: str
    series_id: str
    title: str
    milestones: list[Milestone]
    xp_total: int  # 총 XP
    badge: str  # 완료 시 배지 타입


@dataclass
class QuestProgress:
    """퀘스트 진행 상태"""
    quest_id: str
    completed: int  # 완료된 마일스톤 수
    total: int  # 전체 마일스톤 수
    progress_pct: float  # 진행률 (0.0 ~ 100.0)
    xp_earned: int  # 획득한 XP


@dataclass
class Badge:
    """배지"""
    badge_id: str
    quest_id: str
    badge_type: str  # "bronze", "silver", "gold", "platinum"
    earned_at: str  # ISO 8601 문자열


# 인메모리 저장소
_quests: dict[str, Quest] = {}
_badges: dict[str, Badge] = {}

# 배지 타입 유효성
VALID_BADGE_TYPES = {"bronze", "silver", "gold", "platinum"}

# 마일스톤 수 기반 기본 배지 매핑
_BADGE_THRESHOLDS = {
    (1, 3): "bronze",
    (4, 7): "silver",
    (8, 12): "gold",
    (13, float('inf')): "platinum",
}


def _determine_badge_type(milestone_count: int) -> str:
    """마일스톤 수에 따라 기본 배지 타입을 결정합니다."""
    for (low, high), badge in _BADGE_THRESHOLDS.items():
        if low <= milestone_count <= high:
            return badge
    return "bronze"


def _calculate_default_xp(index: int) -> int:
    """마일스톤 순서에 따른 기본 XP 계산. 뒤로 갈수록 증가."""
    return 100 + (index * 50)


def create_quest(
    series_id: str,
    milestones: list[dict],
) -> Quest:
    """시청 퀘스트를 생성합니다.

    Args:
        series_id: 시리즈 식별자
        milestones: 마일스톤 리스트. 각 dict에 name(str), xp(int, optional) 포함.
                   예: [{"name": "에피소드 1 시청", "xp": 100}, ...]

    Returns:
        생성된 Quest 객체
    """
    quest_id = str(uuid.uuid4())

    milestone_objects = []
    for idx, m in enumerate(milestones):
        ms = Milestone(
            milestone_id=m.get('milestone_id', str(uuid.uuid4())),
            name=m.get('name', f"마일스톤 {idx + 1}"),
            xp=m.get('xp', _calculate_default_xp(idx)),
            completed=False,
        )
        milestone_objects.append(ms)

    xp_total = sum(ms.xp for ms in milestone_objects)
    badge_type = _determine_badge_type(len(milestone_objects))

    # 시리즈 ID 기반 제목 생성
    title = f"{series_id} 시청 퀘스트"

    quest = Quest(
        quest_id=quest_id,
        series_id=series_id,
        title=title,
        milestones=milestone_objects,
        xp_total=xp_total,
        badge=badge_type,
    )

    _quests[quest_id] = quest
    return quest


def check_progress(
    quest_id: str,
    completed_milestones: list[str],
) -> QuestProgress:
    """퀘스트 진행도를 체크합니다.

    Args:
        quest_id: 퀘스트 ID
        completed_milestones: 완료된 마일스톤 ID 리스트

    Returns:
        QuestProgress — 진행 상태

    Raises:
        KeyError: 퀘스트가 존재하지 않을 때
    """
    if quest_id not in _quests:
        raise KeyError(f"퀘스트를 찾을 수 없습니다: {quest_id}")

    quest = _quests[quest_id]
    completed_set = set(completed_milestones)

    completed_count = 0
    xp_earned = 0

    for ms in quest.milestones:
        if ms.milestone_id in completed_set:
            ms.completed = True
            completed_count += 1
            xp_earned += ms.xp

    total = len(quest.milestones)
    progress_pct = (completed_count / total * 100) if total > 0 else 0.0

    return QuestProgress(
        quest_id=quest_id,
        completed=completed_count,
        total=total,
        progress_pct=round(progress_pct, 1),
        xp_earned=xp_earned,
    )


def award_badge(
    quest_id: str,
    badge_type: str,
) -> Badge:
    """배지를 부여합니다.

    Args:
        quest_id: 퀘스트 ID
        badge_type: 배지 타입 ("bronze", "silver", "gold", "platinum")

    Returns:
        Badge 객체

    Raises:
        KeyError: 퀘스트가 존재하지 않을 때
        ValueError: 잘못된 배지 타입일 때
    """
    if quest_id not in _quests:
        raise KeyError(f"퀘스트를 찾을 수 없습니다: {quest_id}")

    if badge_type not in VALID_BADGE_TYPES:
        raise ValueError(
            f"잘못된 배지 타입: {badge_type}. "
            f"유효한 타입: {', '.join(sorted(VALID_BADGE_TYPES))}"
        )

    badge = Badge(
        badge_id=str(uuid.uuid4()),
        quest_id=quest_id,
        badge_type=badge_type,
        earned_at=datetime.now(timezone.utc).isoformat(),
    )

    _badges[badge.badge_id] = badge
    return badge


def get_quest(quest_id: str) -> Optional[Quest]:
    """퀘스트를 조회합니다."""
    return _quests.get(quest_id)


def get_badges_for_quest(quest_id: str) -> list[Badge]:
    """퀘스트에 연결된 모든 배지를 조회합니다."""
    return [b for b in _badges.values() if b.quest_id == quest_id]


def clear_all() -> None:
    """인메모리 저장소를 초기화합니다. (테스트용)"""
    _quests.clear()
    _badges.clear()
