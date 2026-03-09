"""
행동 기반 세그먼트 서비스

사용자 행동 로그를 분석하여 행동 패턴별 세그먼트를 생성합니다.
액션 빈도, 참여도, 이탈 위험도를 기반으로 그룹을 분류합니다.
규칙 기반 (AI API 호출 없음).
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class BehaviorSegment:
    """행동 기반 사용자 세그먼트"""
    segment_name: str
    users: int
    avg_engagement: float
    top_actions: List[str] = field(default_factory=list)
    retention_risk: str = "low"


# ── 액션 카테고리 매핑 ──
_ACTION_CATEGORIES: Dict[str, str] = {
    # 생성 행동
    "generate": "creator",
    "create": "creator",
    "publish": "creator",
    "write": "creator",
    "upload": "creator",
    # 소비 행동
    "view": "consumer",
    "read": "consumer",
    "download": "consumer",
    "watch": "consumer",
    # 참여 행동
    "like": "engager",
    "comment": "engager",
    "share": "engager",
    "bookmark": "engager",
    "follow": "engager",
    # 탐색 행동
    "search": "explorer",
    "browse": "explorer",
    "filter": "explorer",
    "navigate": "explorer",
    # 설정/관리
    "settings": "configurator",
    "configure": "configurator",
    "customize": "configurator",
    "export": "configurator",
}

# ── 세그먼트 레이블 ──
_SEGMENT_LABELS: Dict[str, str] = {
    "creator": "콘텐츠 생산자",
    "consumer": "콘텐츠 소비자",
    "engager": "적극 참여자",
    "explorer": "탐색형 사용자",
    "configurator": "설정 관리자",
    "unknown": "미분류",
}


def _classify_action(action: str) -> str:
    """액션 문자열을 카테고리로 분류합니다."""
    action_lower = action.lower().strip()
    for keyword, category in _ACTION_CATEGORIES.items():
        if keyword in action_lower:
            return category
    return "unknown"


def _calculate_engagement(actions: List[dict]) -> float:
    """사용자의 참여도 점수를 계산합니다 (0~100)."""
    if not actions:
        return 0.0

    # 액션 수 기반 (최대 50점)
    count_score = min(len(actions) * 5, 50)

    # 액션 다양성 기반 (최대 30점)
    unique_actions = len(set(a.get("action", "") for a in actions))
    diversity_score = min(unique_actions * 10, 30)

    # 최근성 기반 (최대 20점) — timestamp 필드가 있으면 활용
    recency_score = 10  # 기본값

    return min(100.0, float(count_score + diversity_score + recency_score))


def _assess_retention_risk(engagement: float, action_count: int) -> str:
    """이탈 위험도를 평가합니다."""
    if engagement < 20 or action_count <= 1:
        return "high"
    if engagement < 50 or action_count <= 3:
        return "medium"
    return "low"


def segment_by_behavior(user_actions: list) -> List[BehaviorSegment]:
    """사용자 행동 로그를 분석하여 행동 기반 세그먼트를 생성합니다.

    Args:
        user_actions: 행동 로그 리스트. 각 항목은 최소 {"user_id": str, "action": str} 포함.
                      선택: {"timestamp": str, "metadata": dict}

    Returns:
        BehaviorSegment 리스트 (사용자 수 내림차순)
    """
    if not user_actions:
        return []

    # 1) 사용자별 액션 그룹핑
    user_data: Dict[str, List[dict]] = defaultdict(list)
    for entry in user_actions:
        user_id = entry.get("user_id", "")
        if not user_id:
            continue
        user_data[user_id].append(entry)

    if not user_data:
        return []

    # 2) 사용자별 주요 카테고리 판별
    segment_users: Dict[str, List[str]] = defaultdict(list)  # category → [user_ids]
    user_engagements: Dict[str, float] = {}
    user_top_actions: Dict[str, List[str]] = {}

    for user_id, actions in user_data.items():
        # 카테고리별 액션 수 계산
        categories = [_classify_action(a.get("action", "")) for a in actions]
        cat_counts = Counter(categories)
        primary_category = cat_counts.most_common(1)[0][0]

        segment_users[primary_category].append(user_id)
        user_engagements[user_id] = _calculate_engagement(actions)

        # 상위 액션 추출
        action_counts = Counter(a.get("action", "") for a in actions)
        user_top_actions[user_id] = [act for act, _ in action_counts.most_common(5)]

    # 3) 세그먼트 집계
    segments: List[BehaviorSegment] = []
    for category, user_ids in segment_users.items():
        # 평균 참여도
        engagements = [user_engagements[uid] for uid in user_ids]
        avg_eng = round(sum(engagements) / len(engagements), 1) if engagements else 0.0

        # 세그먼트 전체의 상위 액션
        all_actions: List[str] = []
        for uid in user_ids:
            all_actions.extend(user_top_actions.get(uid, []))
        top = [act for act, _ in Counter(all_actions).most_common(5)]

        # 이탈 위험도 (평균 참여도 + 평균 액션 수 기반)
        avg_action_count = sum(len(user_data[uid]) for uid in user_ids) / len(user_ids)
        risk = _assess_retention_risk(avg_eng, int(avg_action_count))

        segments.append(BehaviorSegment(
            segment_name=_SEGMENT_LABELS.get(category, category),
            users=len(user_ids),
            avg_engagement=avg_eng,
            top_actions=top,
            retention_risk=risk,
        ))

    # 사용자 수 내림차순 정렬
    segments.sort(key=lambda s: s.users, reverse=True)
    return segments
