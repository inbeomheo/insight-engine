"""
콘텐츠 계보 서비스 — 콘텐츠 변환 이력 추적 및 의미 단위 Diff
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineageNode:
    """계보 노드 — 원본→파생 변환 하나를 표현"""
    node_id: str
    original_id: str
    derived_id: str
    transform_type: str  # "translation", "summary", "rewrite", "merge" 등
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class LineageTree:
    """계보 트리 — 특정 콘텐츠의 전체 변환 이력"""
    root_id: str
    nodes: list[LineageNode] = field(default_factory=list)
    depth: int = 0


@dataclass
class DiffChunk:
    """변경된 문장 청크"""
    original: str
    modified: str
    similarity: float  # 0.0 ~ 1.0


@dataclass
class SemanticDiff:
    """의미 단위 비교 결과"""
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[DiffChunk] = field(default_factory=list)
    similarity_score: float = 0.0


# 허용되는 변환 타입
VALID_TRANSFORM_TYPES = {
    "translation", "summary", "rewrite", "merge",
    "split", "expand", "compress", "format",
}


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리 (간단한 규칙 기반)"""
    if not text or not text.strip():
        return []

    # 문장 종결 부호 기준 분리
    sentences = []
    current = []
    for char in text:
        current.append(char)
        if char in ".!?\n":
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []
    # 마지막 잔여 텍스트
    remainder = "".join(current).strip()
    if remainder:
        sentences.append(remainder)

    return sentences


def _jaccard_similarity(a: str, b: str) -> float:
    """두 문자열의 Jaccard 유사도 (단어 집합 기반)"""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


class ContentLineageService:
    """인메모리 콘텐츠 계보 관리"""

    # 두 문장이 "수정됨"으로 판정되는 유사도 임계값
    MODIFICATION_THRESHOLD = 0.3

    def __init__(self):
        # content_id -> 해당 콘텐츠가 original인 노드 목록
        self._lineage_store: dict[str, list[LineageNode]] = {}
        # 모든 노드를 node_id로 조회
        self._nodes_by_id: dict[str, LineageNode] = {}

    def track_lineage(
        self,
        original_id: str,
        derived_id: str,
        transform_type: str,
        metadata: Optional[dict] = None,
    ) -> LineageNode:
        """
        계보 추적 — 원본에서 파생된 콘텐츠 관계 기록.

        Args:
            original_id: 원본 콘텐츠 ID
            derived_id: 파생 콘텐츠 ID
            transform_type: 변환 유형

        Raises:
            ValueError: ID가 비어있거나 동일하거나, 변환 타입이 유효하지 않을 때
        """
        if not original_id or not original_id.strip():
            raise ValueError("original_id는 비어 있을 수 없습니다")
        if not derived_id or not derived_id.strip():
            raise ValueError("derived_id는 비어 있을 수 없습니다")
        if original_id == derived_id:
            raise ValueError("original_id와 derived_id는 서로 달라야 합니다")
        if transform_type not in VALID_TRANSFORM_TYPES:
            raise ValueError(
                f"유효하지 않은 transform_type: {transform_type}. "
                f"허용: {VALID_TRANSFORM_TYPES}"
            )

        node = LineageNode(
            node_id=f"lineage_{uuid.uuid4().hex[:12]}",
            original_id=original_id,
            derived_id=derived_id,
            transform_type=transform_type,
            metadata=dict(metadata) if metadata else {},
        )

        if original_id not in self._lineage_store:
            self._lineage_store[original_id] = []
        self._lineage_store[original_id].append(node)
        self._nodes_by_id[node.node_id] = node

        return node

    def get_lineage_tree(self, content_id: str) -> LineageTree:
        """
        계보 트리 조회 — content_id를 루트로 하는 모든 파생 관계를 탐색.
        BFS로 트리를 구성하며 depth를 계산한다.
        """
        nodes: list[LineageNode] = []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(content_id, 0)]  # (id, depth)
        max_depth = 0

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            children = self._lineage_store.get(current_id, [])
            for node in children:
                nodes.append(node)
                child_depth = depth + 1
                if child_depth > max_depth:
                    max_depth = child_depth
                queue.append((node.derived_id, child_depth))

        return LineageTree(
            root_id=content_id,
            nodes=nodes,
            depth=max_depth,
        )

    def get_node_by_id(self, node_id: str) -> Optional[LineageNode]:
        """특정 계보 노드 조회"""
        return self._nodes_by_id.get(node_id)

    def get_direct_children(self, content_id: str) -> list[LineageNode]:
        """특정 콘텐츠의 직계 파생 노드 목록"""
        return list(self._lineage_store.get(content_id, []))

    def get_ancestors(self, content_id: str) -> list[LineageNode]:
        """특정 콘텐츠의 조상 노드 목록 (역추적)"""
        ancestors: list[LineageNode] = []
        visited: set[str] = set()

        def _find_parents(cid: str) -> None:
            if cid in visited:
                return
            visited.add(cid)
            for nodes in self._lineage_store.values():
                for node in nodes:
                    if node.derived_id == cid:
                        ancestors.append(node)
                        _find_parents(node.original_id)

        _find_parents(content_id)
        return ancestors

    def compute_semantic_diff(self, version_a: str, version_b: str) -> SemanticDiff:
        """
        두 텍스트 버전의 의미 단위 비교.
        문장 단위로 분리한 뒤 Jaccard 유사도로 추가/삭제/변경을 판별한다.
        """
        sentences_a = _split_sentences(version_a)
        sentences_b = _split_sentences(version_b)

        # 빈 입력 처리
        if not sentences_a and not sentences_b:
            return SemanticDiff(similarity_score=1.0)
        if not sentences_a:
            return SemanticDiff(added=list(sentences_b), similarity_score=0.0)
        if not sentences_b:
            return SemanticDiff(removed=list(sentences_a), similarity_score=0.0)

        # 매칭: B의 각 문장에 대해 A에서 가장 유사한 문장 찾기
        used_a: set[int] = set()
        used_b: set[int] = set()
        modified: list[DiffChunk] = []

        # A의 각 문장과 B의 각 문장 간 유사도 행렬 (greedy matching)
        pairs: list[tuple[float, int, int]] = []
        for i, sa in enumerate(sentences_a):
            for j, sb in enumerate(sentences_b):
                sim = _jaccard_similarity(sa, sb)
                pairs.append((sim, i, j))

        # 유사도 높은 순으로 매칭
        pairs.sort(key=lambda x: x[0], reverse=True)

        for sim, i, j in pairs:
            if i in used_a or j in used_b:
                continue
            if sim >= 1.0:
                # 동일 문장 — 변경 없음
                used_a.add(i)
                used_b.add(j)
            elif sim >= self.MODIFICATION_THRESHOLD:
                # 유사하지만 변경됨
                modified.append(DiffChunk(
                    original=sentences_a[i],
                    modified=sentences_b[j],
                    similarity=sim,
                ))
                used_a.add(i)
                used_b.add(j)

        # 매칭되지 않은 A 문장 → 삭제됨
        removed = [sentences_a[i] for i in range(len(sentences_a)) if i not in used_a]
        # 매칭되지 않은 B 문장 → 추가됨
        added = [sentences_b[j] for j in range(len(sentences_b)) if j not in used_b]

        # 전체 유사도 계산
        total = len(sentences_a) + len(sentences_b)
        matched_count = len(used_a) + len(used_b)  # 매칭된 문장 수 (양쪽 합산)
        similarity_score = matched_count / total if total > 0 else 1.0

        return SemanticDiff(
            added=added,
            removed=removed,
            modified=modified,
            similarity_score=round(similarity_score, 4),
        )
