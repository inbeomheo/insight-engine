"""
전술 오버레이 서비스 — 전략/전술 분석 레이어 (SWOT 기반)
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class TacticalPoint:
    """전술 포인트"""
    point_id: str
    label: str
    category: str  # strength / weakness / opportunity / threat
    position: dict
    notes: str


@dataclass
class TacticalOverlay:
    """전술 오버레이"""
    overlay_id: str
    title: str
    points: list[TacticalPoint] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)


def create_overlay(title: str) -> TacticalOverlay:
    """전술 오버레이 생성"""
    return TacticalOverlay(
        overlay_id=str(uuid.uuid4())[:8],
        title=title
    )


def add_point(overlay: TacticalOverlay, label: str, category: str,
              position: dict, notes: str) -> TacticalOverlay:
    """전술 포인트 추가"""
    valid = ('strength', 'weakness', 'opportunity', 'threat')
    if category not in valid:
        raise ValueError(f"유효하지 않은 카테고리: {category}")

    point = TacticalPoint(
        point_id=str(uuid.uuid4())[:8],
        label=label,
        category=category,
        position=position,
        notes=notes
    )
    new_points = overlay.points + [point]
    return TacticalOverlay(
        overlay_id=overlay.overlay_id,
        title=overlay.title,
        points=new_points,
        analysis=overlay.analysis
    )


def run_swot_analysis(overlay: TacticalOverlay) -> dict:
    """SWOT 분석"""
    result = {
        'strength': [],
        'weakness': [],
        'opportunity': [],
        'threat': []
    }
    for p in overlay.points:
        result[p.category].append(p.label)

    result['summary'] = {
        'strengths_count': len(result['strength']),
        'weaknesses_count': len(result['weakness']),
        'opportunities_count': len(result['opportunity']),
        'threats_count': len(result['threat']),
        'total': len(overlay.points)
    }
    return result


def prioritize_actions(overlay: TacticalOverlay) -> list[dict]:
    """액션 우선순위 — 기회+강점 조합 우선"""
    strengths = [p for p in overlay.points if p.category == 'strength']
    opportunities = [p for p in overlay.points if p.category == 'opportunity']
    weaknesses = [p for p in overlay.points if p.category == 'weakness']
    threats = [p for p in overlay.points if p.category == 'threat']

    actions = []

    # 1순위: 기회 + 강점 조합 (공격적 전략)
    for opp in opportunities:
        for strength in strengths:
            actions.append({
                'priority': 1,
                'strategy': 'offensive',
                'action': f"{strength.label}을(를) 활용하여 {opp.label} 기회 선점",
                'points': [strength.point_id, opp.point_id]
            })

    # 2순위: 약점 보완 (방어적 전략)
    for weakness in weaknesses:
        actions.append({
            'priority': 2,
            'strategy': 'defensive',
            'action': f"{weakness.label} 약점 보완 필요",
            'points': [weakness.point_id]
        })

    # 3순위: 위협 대응 (위기 관리)
    for threat in threats:
        actions.append({
            'priority': 3,
            'strategy': 'contingency',
            'action': f"{threat.label} 위협 대응 계획 수립",
            'points': [threat.point_id]
        })

    actions.sort(key=lambda a: a['priority'])
    return actions
