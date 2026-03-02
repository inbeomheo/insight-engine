"""검색 결과를 프롬프트 삽입용 컨텍스트로 변환

GraphRAG 모드:
  1. 벡터 검색 (ChromaDB)
  2. 지식 그래프 검색 (networkx BFS)
  3. 결합 후 LLM 리랭킹
  4. 상위 K개 컨텍스트 반환
"""
import logging
import os

logger = logging.getLogger(__name__)

# GraphRAG 기능 활성화 여부 (환경변수로 제어)
_GRAPH_RAG_ENABLED = os.environ.get("GRAPH_RAG_ENABLED", "false").lower() == "true"
_RERANKER_ENABLED = os.environ.get("RERANKER_ENABLED", "false").lower() == "true"
_RERANKER_TOP_K = int(os.environ.get("RERANKER_TOP_K", "5"))


class RAGContextBuilder:
    def __init__(self, vector_store, graph_store=None, graph_rag_enabled: bool = False, reranker_enabled: bool = False):
        self.vector_store = vector_store
        self.graph_store = graph_store
        # 생성자 인자 또는 환경변수 중 하나라도 활성화되면 사용
        self._graph_rag_enabled = graph_rag_enabled or _GRAPH_RAG_ENABLED
        self._reranker_enabled = reranker_enabled or _RERANKER_ENABLED

    def build_context(self, user_id: str, query: str, top_k: int = 5) -> str:
        """쿼리로 관련 문서 검색 후 프롬프트 삽입용 텍스트 반환.

        GraphRAG가 활성화된 경우:
          - 벡터 검색 + 그래프 검색 결합
          - LLM 리랭킹 적용
        """
        if self._graph_rag_enabled and self.graph_store is not None:
            return self._build_graph_rag_context(user_id, query, top_k)
        return self._build_vector_context(user_id, query, top_k)

    def _build_vector_context(self, user_id: str, query: str, top_k: int) -> str:
        """기존 벡터 검색 기반 컨텍스트 빌드."""
        results = self.vector_store.search(user_id, query, top_k)
        if not results:
            return ""

        if self._reranker_enabled:
            results = self._apply_reranker(query, results, top_k)

        return self._format_context(results)

    def _build_graph_rag_context(self, user_id: str, query: str, top_k: int) -> str:
        """GraphRAG: 벡터 검색 + 그래프 검색 결합 후 리랭킹."""
        # 1. 벡터 검색 (top_k * 2개 후보 확보)
        vector_results = self.vector_store.search(user_id, query, top_k * 2)

        # 2. 그래프 검색: 쿼리에서 키워드 추출 후 BFS
        graph_context = self._search_graph(user_id, query)

        # 3. 그래프 컨텍스트를 청크 형태로 변환하여 결합
        combined = list(vector_results)
        if graph_context:
            combined.append({
                "text": graph_context,
                "metadata": {"filename": "지식그래프", "source": "graph"},
                "distance": 0.1,  # 그래프 결과는 관련도 높게 설정
            })

        if not combined:
            return ""

        # 4. 리랭킹 적용
        if self._reranker_enabled:
            combined = self._apply_reranker(query, combined, top_k)
        else:
            combined = combined[:top_k]

        return self._format_context(combined)

    def _search_graph(self, user_id: str, query: str) -> str:
        """지식 그래프에서 쿼리 관련 엔티티를 탐색하고 텍스트로 변환합니다."""
        if self.graph_store is None:
            return ""

        stats = self.graph_store.get_stats(user_id)
        if stats["node_count"] == 0:
            return ""

        # 쿼리에서 잠재적 엔티티명 추출 (공백/특수문자 분리)
        import re
        words = re.split(r'[\s,./()]+', query)
        keywords = [w.strip() for w in words if len(w.strip()) >= 2]

        if not keywords:
            return ""

        related = self.graph_store.search_related(user_id, keywords, max_depth=2, max_results=10)
        if not related:
            return ""

        # 그래프 결과를 텍스트로 직렬화
        parts = []
        for node in related:
            desc = node.get("description", "")
            rels = node.get("relations", [])
            rel_texts = []
            for r in rels[:3]:  # 관계는 최대 3개만
                if r.get("direction") == "outgoing":
                    rel_texts.append(f"→ {r['target']} ({r['relation']})")
                else:
                    rel_texts.append(f"← {r.get('source', '?')} ({r['relation']})")

            node_text = f"[{node['type']}] {node['name']}"
            if desc:
                node_text += f": {desc}"
            if rel_texts:
                node_text += " | " + ", ".join(rel_texts)
            parts.append(node_text)

        if parts:
            logger.info(f"그래프 검색 결과: {len(parts)}개 노드")
            return "지식 그래프 참조:\n" + "\n".join(parts)
        return ""

    def _apply_reranker(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        """LLM 리랭커를 적용합니다. 실패 시 원본 순서로 폴백."""
        try:
            from .reranker import rerank_with_fallback
            return rerank_with_fallback(query, chunks, top_k)
        except Exception as e:
            logger.warning(f"리랭커 import 실패, 폴백: {e}")
            return chunks[:top_k]

    def _format_context(self, results: list[dict]) -> str:
        """검색 결과를 프롬프트 삽입용 텍스트로 포맷팅합니다."""
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            source = r['metadata'].get('filename', '문서')
            context_parts.append(f"[참고자료 {i} - {source}]\n{r['text']}")

        return "\n\n".join(context_parts)
