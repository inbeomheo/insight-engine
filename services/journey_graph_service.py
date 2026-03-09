"""
여정 그래프 서비스 — 사용자/고객 여정을 그래프로 시각화
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class JourneyNode:
    """여정 노드"""
    node_id: str
    stage: str
    description: str
    touchpoint: str
    emotion: str  # positive / neutral / negative
    pain_points: list[str] = field(default_factory=list)


@dataclass
class JourneyEdge:
    """여정 엣지"""
    source_id: str
    target_id: str
    transition: str
    drop_off_rate: float


@dataclass
class JourneyGraph:
    """여정 그래프"""
    journey_id: str
    title: str
    nodes: list[JourneyNode] = field(default_factory=list)
    edges: list[JourneyEdge] = field(default_factory=list)


def create_journey(title: str) -> JourneyGraph:
    """여정 그래프 생성"""
    return JourneyGraph(
        journey_id=str(uuid.uuid4())[:8],
        title=title
    )


def add_stage(journey: JourneyGraph, stage: str, description: str,
              touchpoint: str, emotion: str, pain_points: list[str] = None) -> JourneyGraph:
    """단계 추가"""
    node = JourneyNode(
        node_id=str(uuid.uuid4())[:8],
        stage=stage,
        description=description,
        touchpoint=touchpoint,
        emotion=emotion,
        pain_points=pain_points or []
    )
    new_nodes = journey.nodes + [node]
    return JourneyGraph(
        journey_id=journey.journey_id,
        title=journey.title,
        nodes=new_nodes,
        edges=journey.edges
    )


def connect_stages(journey: JourneyGraph, from_id: str, to_id: str,
                   transition: str, drop_off: float) -> JourneyGraph:
    """단계 연결"""
    node_ids = {n.node_id for n in journey.nodes}
    if from_id not in node_ids:
        raise ValueError(f"존재하지 않는 노드: {from_id}")
    if to_id not in node_ids:
        raise ValueError(f"존재하지 않는 노드: {to_id}")

    edge = JourneyEdge(
        source_id=from_id,
        target_id=to_id,
        transition=transition,
        drop_off_rate=max(0.0, min(1.0, drop_off))
    )
    new_edges = journey.edges + [edge]
    return JourneyGraph(
        journey_id=journey.journey_id,
        title=journey.title,
        nodes=journey.nodes,
        edges=new_edges
    )


def find_pain_points(journey: JourneyGraph) -> list[dict]:
    """페인 포인트 요약"""
    results = []
    for node in journey.nodes:
        if node.pain_points:
            results.append({
                'stage': node.stage,
                'pain_points': node.pain_points,
                'emotion': node.emotion
            })
    return results


def calculate_conversion(journey: JourneyGraph) -> float:
    """전체 전환율 — 1 - 누적 이탈"""
    if not journey.edges:
        return 1.0

    remaining = 1.0
    for edge in journey.edges:
        remaining *= (1.0 - edge.drop_off_rate)

    return round(remaining, 4)
