"""검색 결과를 프롬프트 삽입용 컨텍스트로 변환

GraphRAG 모드:
  1. 벡터 검색 (ChromaDB)
  2. 지식 그래프 검색 (networkx BFS)
  3. 결합 후 LLM 리랭킹
  4. 상위 K개 컨텍스트 반환

CRAG 모드 (CRAG_ENABLED=true):
  위 1~4 완료 후:
  5. 검색 품질 LLM 평가
  6. correct → 그대로 사용
     ambiguous → 쿼리 재구성 후 재검색
     incorrect → 웹 검색 폴백
"""
import logging
import os
from typing import Callable, Optional

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

# GraphRAG 기능 활성화 여부 (환경변수로 제어)
_GRAPH_RAG_ENABLED = os.environ.get("GRAPH_RAG_ENABLED", "false").lower() == "true"
_RERANKER_ENABLED = os.environ.get("RERANKER_ENABLED", "false").lower() == "true"
_RERANKER_TOP_K = int(os.environ.get("RERANKER_TOP_K", "5"))

# CRAG (Corrective RAG) 설정
_CRAG_ENABLED = os.environ.get("CRAG_ENABLED", "false").lower() == "true"


class RAGContextBuilder:
    def __init__(
        self,
        vector_store,
        graph_store=None,
        graph_rag_enabled: bool = False,
        reranker_enabled: bool = False,
        crag_enabled: bool = False,
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        # 생성자 인자 또는 환경변수 중 하나라도 활성화되면 사용
        self._graph_rag_enabled = graph_rag_enabled or _GRAPH_RAG_ENABLED
        self._reranker_enabled = reranker_enabled or _RERANKER_ENABLED
        self._crag_enabled = crag_enabled or _CRAG_ENABLED

    def build_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> str:
        """쿼리로 관련 문서 검색 후 프롬프트 삽입용 텍스트 반환.

        처리 순서:
          1. 벡터 검색 (+ GraphRAG, 리랭킹)
          2. CRAG 활성화 시 품질 평가 → 재검색 또는 웹 폴백
        """
        if self._graph_rag_enabled and self.graph_store is not None:
            chunks = self._retrieve_graph_rag_chunks(
                user_id,
                query,
                top_k,
                on_cost_start=on_cost_start,
            )
        else:
            chunks = self._retrieve_vector_chunks(
                user_id,
                query,
                top_k,
                on_cost_start=on_cost_start,
            )

        # CRAG: 검색 품질 교정 루프 (활성화 시)
        if self._crag_enabled and chunks:
            chunks = self._apply_crag(
                query,
                chunks,
                user_id,
                top_k,
                on_cost_start=on_cost_start,
            )

        return self._format_context(chunks)

    # ------------------------------------------------------------------
    # 내부 검색 메서드 (청크 리스트 반환)
    # ------------------------------------------------------------------

    def _retrieve_vector_chunks(
        self,
        user_id: str,
        query: str,
        top_k: int,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> list[dict]:
        """벡터 검색 결과를 청크 리스트로 반환합니다."""
        results = self.vector_store.search(user_id, query, top_k)
        if not results:
            return []
        if self._reranker_enabled:
            results = self._apply_reranker(
                query,
                results,
                top_k,
                on_cost_start=on_cost_start,
            )
        return results

    def _retrieve_graph_rag_chunks(
        self,
        user_id: str,
        query: str,
        top_k: int,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> list[dict]:
        """GraphRAG 검색 결과를 청크 리스트로 반환합니다."""
        vector_results = self.vector_store.search(user_id, query, top_k * 2)
        graph_context = self._search_graph(user_id, query)

        combined = list(vector_results)
        if graph_context:
            combined.append({
                "text": graph_context,
                "metadata": {"filename": "지식그래프", "source": "graph"},
                "distance": 0.1,
            })

        if not combined:
            return []

        if self._reranker_enabled:
            combined = self._apply_reranker(
                query,
                combined,
                top_k,
                on_cost_start=on_cost_start,
            )
        else:
            combined = combined[:top_k]

        return combined

    def _apply_crag(
        self,
        query: str,
        chunks: list[dict],
        user_id: str,
        top_k: int,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> list[dict]:
        """CRAG 루프: 품질 평가 → 교정 검색."""
        try:
            from .corrective_rag import corrective_search
            return corrective_search(
                query=query,
                chunks=chunks,
                vector_store=self.vector_store,
                user_id=user_id,
                top_k=top_k,
                max_retries=1,
                on_cost_start=on_cost_start,
            )
        except UsageLockUnavailable:
            raise
        except Exception as e:
            logger.warning(f"CRAG 적용 실패, 원본 청크 사용: {e}")
            return chunks

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

    def _apply_reranker(
        self,
        query: str,
        chunks: list[dict],
        top_k: int,
        *,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> list[dict]:
        """LLM 리랭커를 적용합니다. 실패 시 원본 순서로 폴백."""
        try:
            from .reranker import rerank_with_fallback
            return rerank_with_fallback(
                query,
                chunks,
                top_k,
                on_cost_start=on_cost_start,
            )
        except UsageLockUnavailable:
            raise
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
