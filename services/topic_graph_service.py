"""토픽 그래프 서비스

문서에서 토픽 간 관계를 그래프로 구성합니다.
토픽 추출, 공출현 그래프 생성, 중심 토픽 탐색, 경로 탐색 기능을 제공합니다.
"""
import re
import uuid
from dataclasses import dataclass, field
from collections import Counter, defaultdict


@dataclass
class TopicNode:
    """토픽 노드"""
    node_id: str                        # 노드 고유 ID
    topic: str                          # 토픽명
    weight: float = 0.0                # 가중치 (빈도 기반)
    related_terms: list[str] = field(default_factory=list)  # 관련 용어


@dataclass
class TopicEdge:
    """토픽 간 연결"""
    source_id: str                      # 출발 노드 ID
    target_id: str                      # 도착 노드 ID
    relationship: str = 'co_occurrence'  # 관계 유형
    strength: float = 0.0              # 연결 강도


@dataclass
class TopicGraph:
    """토픽 그래프"""
    nodes: list[TopicNode] = field(default_factory=list)
    edges: list[TopicEdge] = field(default_factory=list)


# ── 한국어 불용어 ────────────────────────────────────────────
_STOPWORDS = {
    '그리고', '또는', '하지만', '그런데', '이것', '그것', '저것',
    '대해', '대한', '에서', '으로', '까지', '부터', '통해',
    '위해', '있는', '하는', '되는', '것이', '수가', '등의',
    '관련', '사용', '경우', '방법', '것을', '수를', '것은',
    'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
    'this', 'that', 'for', 'with', 'from', 'into',
}

# ── 문장 분리 ────────────────────────────────────────────────
_SENTENCE_SPLIT = re.compile(r'[.!?。！？\n]+')


def _tokenize(text: str) -> list[str]:
    """텍스트를 토큰으로 분리 (2자 이상, 불용어 제거)"""
    tokens = re.findall(r'[\w가-힣]+', text.lower())
    return [t for t in tokens if len(t) >= 2 and t not in _STOPWORDS]


def extract_topics(text: str, max_topics: int = 10) -> list[TopicNode]:
    """텍스트에서 토픽 추출

    명사구 빈도 기반으로 토픽을 추출합니다.

    Args:
        text: 원본 텍스트
        max_topics: 최대 토픽 수

    Returns:
        추출된 TopicNode 목록 (빈도 내림차순)
    """
    if not text or not text.strip():
        return []

    tokens = _tokenize(text)
    if not tokens:
        return []

    # 토큰 빈도 계산
    counter = Counter(tokens)
    max_freq = counter.most_common(1)[0][1] if counter else 1

    # 상위 토픽 추출
    topics: list[TopicNode] = []
    for term, freq in counter.most_common(max_topics):
        weight = freq / max_freq  # 정규화 (0~1)

        # 관련 용어: 같은 문장에 자주 등장하는 토큰
        related = _find_related_terms(text, term, limit=5)

        topics.append(TopicNode(
            node_id=uuid.uuid4().hex[:8],
            topic=term,
            weight=round(weight, 3),
            related_terms=related,
        ))

    return topics


def _find_related_terms(text: str, target: str, limit: int = 5) -> list[str]:
    """타겟 토큰과 같은 문장에 등장하는 관련 용어 추출"""
    sentences = _SENTENCE_SPLIT.split(text)
    co_counter: Counter = Counter()

    for sentence in sentences:
        tokens = _tokenize(sentence)
        if target in tokens:
            for t in tokens:
                if t != target:
                    co_counter[t] += 1

    return [term for term, _ in co_counter.most_common(limit)]


def build_graph(text: str, topics: list[TopicNode]) -> TopicGraph:
    """공출현 기반 토픽 그래프 생성

    같은 문장에서 두 토픽이 함께 등장하면 엣지를 생성합니다.

    Args:
        text: 원본 텍스트
        topics: 토픽 노드 목록

    Returns:
        구성된 TopicGraph
    """
    if not topics or not text:
        return TopicGraph(nodes=list(topics), edges=[])

    sentences = _SENTENCE_SPLIT.split(text)
    topic_names = {t.topic for t in topics}
    topic_id_map = {t.topic: t.node_id for t in topics}

    # 공출현 빈도 계산
    co_occur: Counter = Counter()
    for sentence in sentences:
        tokens = set(_tokenize(sentence))
        present = [t for t in topic_names if t in tokens]
        # 모든 쌍의 공출현 카운트
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                pair = tuple(sorted([present[i], present[j]]))
                co_occur[pair] += 1

    # 엣지 생성
    edges: list[TopicEdge] = []
    max_co = max(co_occur.values()) if co_occur else 1

    for (topic_a, topic_b), count in co_occur.items():
        strength = count / max_co  # 정규화
        edges.append(TopicEdge(
            source_id=topic_id_map[topic_a],
            target_id=topic_id_map[topic_b],
            relationship='co_occurrence',
            strength=round(strength, 3),
        ))

    return TopicGraph(nodes=list(topics), edges=edges)


def find_central_topics(graph: TopicGraph, top_k: int = 3) -> list[TopicNode]:
    """중심 토픽 탐색

    연결 수(차수)가 높은 토픽을 반환합니다.

    Args:
        graph: 토픽 그래프
        top_k: 상위 K개

    Returns:
        중심 토픽 목록
    """
    if not graph.nodes:
        return []

    # 노드별 연결 수 계산
    degree: Counter = Counter()
    for edge in graph.edges:
        degree[edge.source_id] += 1
        degree[edge.target_id] += 1

    # 노드 ID → 노드 매핑
    node_map = {n.node_id: n for n in graph.nodes}

    # 연결 수 내림차순 정렬
    sorted_ids = sorted(
        [n.node_id for n in graph.nodes],
        key=lambda nid: degree.get(nid, 0),
        reverse=True,
    )

    return [node_map[nid] for nid in sorted_ids[:top_k]]


def find_path(
    graph: TopicGraph,
    source_id: str,
    target_id: str,
) -> list[str] | None:
    """토픽 간 경로 탐색 (BFS)

    Args:
        graph: 토픽 그래프
        source_id: 출발 노드 ID
        target_id: 도착 노드 ID

    Returns:
        경로 (노드 ID 목록) 또는 None (경로 없음)
    """
    if source_id == target_id:
        return [source_id]

    # 인접 리스트 구성
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adjacency[edge.source_id].append(edge.target_id)
        adjacency[edge.target_id].append(edge.source_id)

    # 노드 존재 확인
    node_ids = {n.node_id for n in graph.nodes}
    if source_id not in node_ids or target_id not in node_ids:
        return None

    # BFS
    visited: set[str] = {source_id}
    queue: list[list[str]] = [[source_id]]

    while queue:
        path = queue.pop(0)
        current = path[-1]

        for neighbor in adjacency.get(current, []):
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == target_id:
                return new_path
            visited.add(neighbor)
            queue.append(new_path)

    return None
