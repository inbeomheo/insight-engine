"""
의미 탐색 서비스 — 키워드 기반 의미 관계 탐색
"""

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class SemanticNode:
    """의미 노드"""
    node_id: str
    term: str
    weight: float = 0.0
    related: list[str] = field(default_factory=list)


@dataclass
class ExplorationPath:
    """탐색 경로"""
    start_term: str
    path: list[str] = field(default_factory=list)
    depth: int = 0


# 불용어 (의미 맵 생성 시 제외)
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "because", "but", "and", "or", "if", "it",
    "its", "this", "that", "these", "those", "i", "me", "my", "we",
    "our", "you", "your", "he", "him", "his", "she", "her", "they",
    "them", "their", "what", "which", "who", "whom",
    # 한국어 불용어
    "이", "그", "저", "것", "수", "등", "및", "를", "을", "에", "의",
    "가", "는", "은", "로", "으로", "와", "과", "도", "만", "에서",
}


def _tokenize(text: str) -> list[str]:
    """텍스트를 단어로 분리 (불용어 제거, 소문자화)"""
    # 알파벳/숫자/한국어 단어 추출
    words = re.findall(r"[a-zA-Z가-힣]{2,}", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def build_semantic_map(text: str) -> list[SemanticNode]:
    """텍스트에서 의미 맵 생성 (공출현 단어 관계)

    같은 문장 내에 함께 출현하는 단어를 관련어로 연결.

    Args:
        text: 입력 텍스트

    Returns:
        의미 노드 목록
    """
    if not text.strip():
        return []

    # 문장 분리
    sentences = re.split(r"[.!?。\n]+", text)

    # 단어 빈도 계산
    word_freq: dict[str, int] = defaultdict(int)
    # 공출현 관계 계산
    co_occurrence: dict[str, set[str]] = defaultdict(set)

    for sentence in sentences:
        words = _tokenize(sentence)
        unique_words = list(set(words))

        for word in words:
            word_freq[word] += 1

        # 같은 문장 내 공출현
        for i, w1 in enumerate(unique_words):
            for w2 in unique_words[i + 1:]:
                co_occurrence[w1].add(w2)
                co_occurrence[w2].add(w1)

    if not word_freq:
        return []

    # 최대 빈도 기준 가중치 정규화
    max_freq = max(word_freq.values())

    nodes: list[SemanticNode] = []
    for term, freq in word_freq.items():
        related = sorted(co_occurrence.get(term, set()))
        nodes.append(SemanticNode(
            node_id=str(uuid.uuid4()),
            term=term,
            weight=round(freq / max_freq, 3),
            related=related,
        ))

    # 가중치 내림차순 정렬
    nodes.sort(key=lambda n: n.weight, reverse=True)
    return nodes


def explore(
    nodes: list[SemanticNode], start_term: str, depth: int = 3
) -> ExplorationPath:
    """의미 탐색 (BFS 너비 우선)

    Args:
        nodes: 의미 노드 목록
        start_term: 시작 용어
        depth: 최대 탐색 깊이

    Returns:
        탐색 경로
    """
    # 노드 맵 구축
    node_map: dict[str, SemanticNode] = {}
    for node in nodes:
        node_map[node.term] = node

    if start_term.lower() not in node_map:
        return ExplorationPath(start_term=start_term, path=[], depth=0)

    # BFS 탐색
    visited: set[str] = set()
    path: list[str] = []
    queue: list[tuple[str, int]] = [(start_term.lower(), 0)]
    visited.add(start_term.lower())

    while queue:
        current, current_depth = queue.pop(0)
        path.append(current)

        if current_depth >= depth:
            continue

        node = node_map.get(current)
        if node is None:
            continue

        for related_term in node.related:
            if related_term not in visited and related_term in node_map:
                visited.add(related_term)
                queue.append((related_term, current_depth + 1))

    return ExplorationPath(
        start_term=start_term,
        path=path,
        depth=min(depth, len(path) - 1) if len(path) > 1 else 0,
    )


def find_clusters(nodes: list[SemanticNode]) -> list[list[str]]:
    """의미 클러스터 탐지 (연결 컴포넌트)

    Args:
        nodes: 의미 노드 목록

    Returns:
        클러스터별 용어 목록
    """
    # 노드 맵 구축
    node_map: dict[str, SemanticNode] = {}
    all_terms: set[str] = set()
    for node in nodes:
        node_map[node.term] = node
        all_terms.add(node.term)

    visited: set[str] = set()
    clusters: list[list[str]] = []

    for term in all_terms:
        if term in visited:
            continue

        # BFS로 연결 컴포넌트 탐색
        cluster: list[str] = []
        queue = [term]
        visited.add(term)

        while queue:
            current = queue.pop(0)
            cluster.append(current)

            node = node_map.get(current)
            if node is None:
                continue

            for related in node.related:
                if related not in visited and related in node_map:
                    visited.add(related)
                    queue.append(related)

        cluster.sort()
        clusters.append(cluster)

    # 크기 내림차순 정렬
    clusters.sort(key=len, reverse=True)
    return clusters


def suggest_expansion(nodes: list[SemanticNode], term: str) -> list[str]:
    """관련 용어 확장 제안

    Args:
        nodes: 의미 노드 목록
        term: 확장할 용어

    Returns:
        관련 용어 목록 (가중치 순)
    """
    node_map: dict[str, SemanticNode] = {n.term: n for n in nodes}

    node = node_map.get(term.lower())
    if node is None:
        return []

    # 직접 관련어 + 관련어의 관련어 (2차)
    suggestions: dict[str, float] = {}

    for related in node.related:
        related_node = node_map.get(related)
        if related_node:
            suggestions[related] = related_node.weight

            # 2차 관련어 (가중치 절반)
            for second_related in related_node.related:
                if second_related != term.lower() and second_related not in node.related:
                    second_node = node_map.get(second_related)
                    if second_node and second_related not in suggestions:
                        suggestions[second_related] = second_node.weight * 0.5

    # 가중치 내림차순 정렬
    sorted_terms = sorted(suggestions.keys(), key=lambda t: suggestions[t], reverse=True)
    return sorted_terms
