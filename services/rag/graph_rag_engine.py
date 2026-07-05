"""
GraphRAG 엔진 — 엔티티/관계 자동 추출 + 로컬 검색
graph_store(저장소)와 graph_builder(추출기)를 활용하여
텍스트에서 지식 그래프를 자동 구축하고 검색합니다.
"""
import logging
from typing import Any, Dict, List, Optional

from services.rag.graph_store import graph_store, GraphStore
from services.rag.graph_builder import extract_graph

logger = logging.getLogger(__name__)


class GraphRAGEngine:
    """GraphRAG 엔진 — 자동 엔티티 추출 + 로컬 검색.

    - ingest: 텍스트 → LLM으로 엔티티/관계 추출 → 그래프 저장
    - local_search: 특정 엔티티 중심 BFS 탐색
    """

    def __init__(self, store: Optional[GraphStore] = None, model: str = None):
        self.store = store or graph_store
        self.model = model  # LLM 모델 ID (None이면 graph_builder 기본 모델 사용)

    def ingest(self, user_id: str, text: str) -> Dict[str, int]:
        """텍스트에서 엔티티/관계를 자동 추출하여 그래프에 추가합니다.

        Args:
            user_id: 사용자 ID
            text: 분석할 텍스트

        Returns:
            {"entities_added": int, "relations_added": int}
        """
        kwargs = {}
        if self.model:
            kwargs["model"] = self.model

        result = extract_graph(text, **kwargs)
        entities = result.get("entities", [])
        relations = result.get("relations", [])

        if entities:
            self.store.add_entities(user_id, entities)
        if relations:
            self.store.add_relations(user_id, relations)

        logger.info(f"GraphRAG 인제스트: user={user_id}, 엔티티={len(entities)}, 관계={len(relations)}")
        return {"entities_added": len(entities), "relations_added": len(relations)}

    def local_search(
        self,
        user_id: str,
        query_entities: List[str],
        max_depth: int = 2,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """엔티티 중심 로컬 검색 (BFS 탐색).

        Args:
            user_id: 사용자 ID
            query_entities: 탐색 시작 엔티티 이름 목록
            max_depth: BFS 최대 깊이
            max_results: 최대 반환 수

        Returns:
            관련 노드 리스트 (name, type, description, depth, relations)
        """
        return self.store.search_related(
            user_id, query_entities, max_depth=max_depth, max_results=max_results
        )
