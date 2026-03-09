"""
의도 충돌 라우터 서비스.

여러 이해관계자의 상충하는 의도를 탐지하고 해결(우선순위/절충/에스컬레이션)한다.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Intent:
    """이해관계자 의도."""
    intent_id: str
    stakeholder: str
    goal: str
    priority: int  # 높을수록 우선
    constraints: list  # list[str]


@dataclass
class ConflictResolution:
    """충돌 해결 결과."""
    conflict_id: str
    intents: list  # list[Intent]
    resolution_type: str  # priority_based / compromise / escalate
    resolved_goal: str
    trade_offs: list  # list[str]


# 반대 키워드 쌍 — 상충 탐지용
_OPPOSING_PAIRS = [
    ({"빠르게", "신속", "즉시", "긴급"}, {"신중하게", "충분히", "검토", "천천히"}),
    ({"비용 절감", "저렴", "예산 절약"}, {"품질 우선", "프리미엄", "고급"}),
    ({"공개", "투명", "공유"}, {"비밀", "기밀", "비공개"}),
    ({"확대", "성장", "확장"}, {"축소", "절감", "최소화"}),
    ({"자동화", "효율"}, {"수동", "정밀", "직접"}),
]


def detect_conflicts(intents: list) -> list:
    """상충하는 의도 쌍을 탐지한다.

    Returns:
        list[tuple[Intent, Intent, str]] — (의도A, 의도B, 충돌 이유)
    """
    conflicts = []

    for i in range(len(intents)):
        for j in range(i + 1, len(intents)):
            reason = _check_opposing(intents[i], intents[j])
            if reason:
                conflicts.append((intents[i], intents[j], reason))

    return conflicts


def _check_opposing(a: Intent, b: Intent) -> Optional[str]:
    """두 의도가 상충하는지 확인한다."""
    a_text = f"{a.goal} {' '.join(a.constraints)}".lower()
    b_text = f"{b.goal} {' '.join(b.constraints)}".lower()

    for set_a, set_b in _OPPOSING_PAIRS:
        a_match = any(kw in a_text for kw in set_a)
        b_match = any(kw in b_text for kw in set_b)
        if a_match and b_match:
            return f"상충 탐지: {set_a & _words_in(a_text)} vs {set_b & _words_in(b_text)}"

        # 역방향도 확인
        a_match_rev = any(kw in a_text for kw in set_b)
        b_match_rev = any(kw in b_text for kw in set_a)
        if a_match_rev and b_match_rev:
            return f"상충 탐지: {set_b & _words_in(a_text)} vs {set_a & _words_in(b_text)}"

    return None


def _words_in(text: str) -> set:
    """텍스트에 포함된 단어 집합을 반환한다."""
    return set(text.split())


def resolve_by_priority(intents: list) -> ConflictResolution:
    """우선순위 기반으로 충돌을 해결한다."""
    if not intents:
        return ConflictResolution(
            conflict_id=f"cr_{uuid.uuid4().hex[:8]}",
            intents=[],
            resolution_type="priority_based",
            resolved_goal="의도 없음",
            trade_offs=[],
        )

    sorted_intents = sorted(intents, key=lambda i: i.priority, reverse=True)
    winner = sorted_intents[0]

    trade_offs = []
    for intent in sorted_intents[1:]:
        trade_offs.append(
            f"{intent.stakeholder}의 '{intent.goal}' (우선순위 {intent.priority}) 양보"
        )

    return ConflictResolution(
        conflict_id=f"cr_{uuid.uuid4().hex[:8]}",
        intents=list(intents),
        resolution_type="priority_based",
        resolved_goal=winner.goal,
        trade_offs=trade_offs,
    )


def propose_compromise(intent_a: Intent, intent_b: Intent) -> ConflictResolution:
    """두 의도 간 절충안을 제안한다."""
    # 두 목표를 결합하는 절충안 생성
    resolved = f"{intent_a.goal}과(와) {intent_b.goal}의 균형점 도출"

    # 양측의 핵심 제약 조건을 모두 포함
    combined_constraints = list(set(intent_a.constraints + intent_b.constraints))

    trade_offs = [
        f"{intent_a.stakeholder}: 목표 '{intent_a.goal}' 부분 수정 필요",
        f"{intent_b.stakeholder}: 목표 '{intent_b.goal}' 부분 수정 필요",
    ]

    return ConflictResolution(
        conflict_id=f"cr_{uuid.uuid4().hex[:8]}",
        intents=[intent_a, intent_b],
        resolution_type="compromise",
        resolved_goal=resolved,
        trade_offs=trade_offs,
    )


def route_intent(intents: list, content: dict = None) -> dict:
    """최종 라우팅 결정을 반환한다."""
    content = content or {}

    # 충돌 탐지
    conflicts = detect_conflicts(intents)

    if not conflicts:
        # 충돌 없음 — 최고 우선순위 의도 사용
        if intents:
            top = max(intents, key=lambda i: i.priority)
            return {
                "has_conflict": False,
                "resolved_goal": top.goal,
                "stakeholder": top.stakeholder,
                "resolution_type": "no_conflict",
            }
        return {
            "has_conflict": False,
            "resolved_goal": "기본 처리",
            "resolution_type": "no_intent",
        }

    # 충돌 있음 — 우선순위 기반 해결 시도
    resolution = resolve_by_priority(intents)

    return {
        "has_conflict": True,
        "conflict_count": len(conflicts),
        "resolved_goal": resolution.resolved_goal,
        "resolution_type": resolution.resolution_type,
        "trade_offs": resolution.trade_offs,
    }
