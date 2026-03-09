"""
분류체계 서비스 — 콘텐츠를 계층적 카테고리로 분류
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class TaxonomyNode:
    """분류체계 노드"""
    node_id: str
    name: str
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    level: int = 0


@dataclass
class Taxonomy:
    """분류체계"""
    taxonomy_id: str
    nodes: list[TaxonomyNode] = field(default_factory=list)
    root_id: str = ""


def _find_node(taxonomy: Taxonomy, node_id: str) -> TaxonomyNode | None:
    """ID로 노드 검색 (내부 유틸)"""
    for node in taxonomy.nodes:
        if node.node_id == node_id:
            return node
    return None


def create_taxonomy(name: str) -> Taxonomy:
    """루트 노드로 분류체계 생성

    Args:
        name: 루트 카테고리 이름

    Returns:
        새 분류체계
    """
    root_id = str(uuid.uuid4())
    root_node = TaxonomyNode(
        node_id=root_id,
        name=name,
        parent_id=None,
        children=[],
        keywords=[],
        level=0,
    )
    return Taxonomy(
        taxonomy_id=str(uuid.uuid4()),
        nodes=[root_node],
        root_id=root_id,
    )


def add_category(
    taxonomy: Taxonomy,
    parent_id: str,
    name: str,
    keywords: list[str] | None = None,
) -> Taxonomy:
    """카테고리 추가

    Args:
        taxonomy: 대상 분류체계
        parent_id: 부모 노드 ID
        name: 카테고리 이름
        keywords: 분류 키워드

    Returns:
        업데이트된 분류체계

    Raises:
        ValueError: 부모 노드를 찾을 수 없을 때
    """
    parent = _find_node(taxonomy, parent_id)
    if parent is None:
        raise ValueError(f"부모 노드를 찾을 수 없습니다: {parent_id}")

    new_id = str(uuid.uuid4())
    new_node = TaxonomyNode(
        node_id=new_id,
        name=name,
        parent_id=parent_id,
        children=[],
        keywords=keywords or [],
        level=parent.level + 1,
    )
    parent.children.append(new_id)
    taxonomy.nodes.append(new_node)
    return taxonomy


def classify_content(taxonomy: Taxonomy, content: str) -> list[TaxonomyNode]:
    """콘텐츠 분류 (키워드 매칭, 가장 구체적인 노드 우선)

    Args:
        taxonomy: 분류체계
        content: 분류할 콘텐츠 텍스트

    Returns:
        매칭된 노드 목록 (깊은 레벨 우선)
    """
    if not content.strip():
        return []

    content_lower = content.lower()
    matched: list[tuple[int, int, TaxonomyNode]] = []

    for node in taxonomy.nodes:
        if not node.keywords:
            continue
        hit_count = 0
        for kw in node.keywords:
            if kw.lower() in content_lower:
                hit_count += 1
        if hit_count > 0:
            # (레벨, 키워드 히트 수) — 깊은 레벨 + 많은 히트 우선
            matched.append((node.level, hit_count, node))

    # 깊은 레벨 우선, 같은 레벨이면 히트 수 많은 순
    matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [node for _, _, node in matched]


def get_path(taxonomy: Taxonomy, node_id: str) -> list[str]:
    """루트부터 노드까지 경로 반환

    Args:
        taxonomy: 분류체계
        node_id: 대상 노드 ID

    Returns:
        루트→노드 순서 이름 목록

    Raises:
        ValueError: 노드를 찾을 수 없을 때
    """
    node = _find_node(taxonomy, node_id)
    if node is None:
        raise ValueError(f"노드를 찾을 수 없습니다: {node_id}")

    path = []
    current: TaxonomyNode | None = node
    while current is not None:
        path.append(current.name)
        if current.parent_id is None:
            break
        current = _find_node(taxonomy, current.parent_id)

    path.reverse()
    return path


def get_depth(taxonomy: Taxonomy) -> int:
    """분류체계 최대 깊이 반환

    Args:
        taxonomy: 분류체계

    Returns:
        최대 레벨 값
    """
    if not taxonomy.nodes:
        return 0
    return max(node.level for node in taxonomy.nodes)


def find_node(taxonomy: Taxonomy, name: str) -> TaxonomyNode | None:
    """이름으로 노드 검색

    Args:
        taxonomy: 분류체계
        name: 검색할 노드 이름

    Returns:
        찾은 노드 또는 None
    """
    name_lower = name.lower()
    for node in taxonomy.nodes:
        if node.name.lower() == name_lower:
            return node
    return None
