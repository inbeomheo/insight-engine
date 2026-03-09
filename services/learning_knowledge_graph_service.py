"""
학습 지식그래프 서비스 — 학습 콘텐츠의 개념 관계 그래프
"""

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class Concept:
    """개념 노드"""
    concept_id: str
    name: str
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)  # concept_id 목록
    difficulty: int = 1  # 1~5


@dataclass
class ConceptEdge:
    """개념 관계 엣지"""
    source_id: str
    target_id: str
    relation: str  # prerequisite / related / extends / applies


@dataclass
class LearningGraph:
    """학습 지식그래프"""
    concepts: list[Concept] = field(default_factory=list)
    edges: list[ConceptEdge] = field(default_factory=list)


def _find_concept(graph: LearningGraph, concept_id: str) -> Concept | None:
    """ID로 개념 검색 (내부 유틸)"""
    for c in graph.concepts:
        if c.concept_id == concept_id:
            return c
    return None


def _find_concept_by_name(graph: LearningGraph, name: str) -> Concept | None:
    """이름으로 개념 검색 (내부 유틸)"""
    name_lower = name.lower()
    for c in graph.concepts:
        if c.name.lower() == name_lower:
            return c
    return None


def add_concept(
    graph: LearningGraph,
    name: str,
    description: str = "",
    difficulty: int = 1,
) -> LearningGraph:
    """개념 추가

    Args:
        graph: 대상 그래프
        name: 개념 이름
        description: 설명
        difficulty: 난이도 (1~5)

    Returns:
        업데이트된 그래프

    Raises:
        ValueError: 난이도 범위 초과 또는 중복 이름
    """
    if not (1 <= difficulty <= 5):
        raise ValueError(f"난이도는 1~5 범위여야 합니다: {difficulty}")

    if _find_concept_by_name(graph, name) is not None:
        raise ValueError(f"이미 존재하는 개념입니다: {name}")

    concept = Concept(
        concept_id=str(uuid.uuid4()),
        name=name,
        description=description,
        prerequisites=[],
        difficulty=difficulty,
    )
    graph.concepts.append(concept)
    return graph


def add_relation(
    graph: LearningGraph,
    source: str,
    target: str,
    relation: str,
) -> LearningGraph:
    """관계 추가

    source와 target은 concept_id 또는 name으로 지정 가능.

    Args:
        graph: 대상 그래프
        source: 소스 개념 (ID 또는 이름)
        target: 타겟 개념 (ID 또는 이름)
        relation: 관계 유형 (prerequisite/related/extends/applies)

    Returns:
        업데이트된 그래프

    Raises:
        ValueError: 개념을 찾을 수 없거나 잘못된 관계 유형
    """
    valid_relations = {"prerequisite", "related", "extends", "applies"}
    if relation not in valid_relations:
        raise ValueError(f"잘못된 관계 유형: {relation}. 허용: {', '.join(sorted(valid_relations))}")

    # ID 또는 이름으로 검색
    source_concept = _find_concept(graph, source) or _find_concept_by_name(graph, source)
    target_concept = _find_concept(graph, target) or _find_concept_by_name(graph, target)

    if source_concept is None:
        raise ValueError(f"소스 개념을 찾을 수 없습니다: {source}")
    if target_concept is None:
        raise ValueError(f"타겟 개념을 찾을 수 없습니다: {target}")

    edge = ConceptEdge(
        source_id=source_concept.concept_id,
        target_id=target_concept.concept_id,
        relation=relation,
    )
    graph.edges.append(edge)

    # prerequisite 관계일 때 prerequisites 목록에도 추가
    if relation == "prerequisite":
        if source_concept.concept_id not in target_concept.prerequisites:
            target_concept.prerequisites.append(source_concept.concept_id)

    return graph


def get_learning_path(
    graph: LearningGraph, start: str, goal: str
) -> list[str]:
    """학습 경로 (BFS prerequisite 순회)

    goal 개념에 도달하기 위해 필요한 prerequisite 체인을 역추적.

    Args:
        graph: 대상 그래프
        start: 시작 개념 (ID 또는 이름)
        goal: 목표 개념 (ID 또는 이름)

    Returns:
        학습 순서 (개념 이름 목록)
    """
    start_concept = _find_concept(graph, start) or _find_concept_by_name(graph, start)
    goal_concept = _find_concept(graph, goal) or _find_concept_by_name(graph, goal)

    if start_concept is None or goal_concept is None:
        return []

    if start_concept.concept_id == goal_concept.concept_id:
        return [start_concept.name]

    # prerequisite 관계로 인접 리스트 구성 (source → target 방향)
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.relation == "prerequisite":
            # source가 target의 선수조건 → source → target 순서
            adj[edge.source_id].append(edge.target_id)

    # BFS로 경로 탐색
    queue: deque[list[str]] = deque([[start_concept.concept_id]])
    visited: set[str] = {start_concept.concept_id}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == goal_concept.concept_id:
            return [
                c.name for cid in path
                if (c := _find_concept(graph, cid)) is not None
            ]

        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    # 경로를 찾지 못한 경우, related/extends 관계도 포함
    adj_all: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adj_all[edge.source_id].append(edge.target_id)
        if edge.relation == "related":
            adj_all[edge.target_id].append(edge.source_id)

    queue = deque([[start_concept.concept_id]])
    visited = {start_concept.concept_id}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == goal_concept.concept_id:
            return [
                c.name for cid in path
                if (c := _find_concept(graph, cid)) is not None
            ]

        for neighbor in adj_all.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return []


def find_foundational(graph: LearningGraph) -> list[Concept]:
    """선수조건 없는 기초 개념 찾기

    Args:
        graph: 대상 그래프

    Returns:
        기초 개념 목록
    """
    # prerequisite의 target이 되지 않는 개념
    has_prerequisite: set[str] = set()
    for edge in graph.edges:
        if edge.relation == "prerequisite":
            has_prerequisite.add(edge.target_id)

    foundational = [
        c for c in graph.concepts
        if c.concept_id not in has_prerequisite and not c.prerequisites
    ]
    return foundational


def topological_sort(graph: LearningGraph) -> list[str]:
    """위상 정렬 (학습 순서)

    prerequisite 관계를 기반으로 선수조건이 먼저 오도록 정렬.

    Args:
        graph: 대상 그래프

    Returns:
        정렬된 개념 이름 목록
    """
    if not graph.concepts:
        return []

    # 인접 리스트 + 진입 차수 계산
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {c.concept_id: 0 for c in graph.concepts}

    for edge in graph.edges:
        if edge.relation == "prerequisite":
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

    # 진입 차수 0인 노드부터 시작 (Kahn 알고리즘)
    queue: deque[str] = deque()
    for concept in graph.concepts:
        if in_degree.get(concept.concept_id, 0) == 0:
            queue.append(concept.concept_id)

    result: list[str] = []
    while queue:
        current = queue.popleft()
        concept = _find_concept(graph, current)
        if concept:
            result.append(concept.name)

        for neighbor in adj.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result
