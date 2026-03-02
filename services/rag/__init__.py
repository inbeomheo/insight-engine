"""
RAG (Retrieval-Augmented Generation) 지식 참조 패키지
- vector_store: ChromaDB 기반 벡터 저장소
- chunker: 문서 텍스트 분할
- context_builder: 검색 결과 → 프롬프트 컨텍스트 변환 (GraphRAG + Reranker 지원)
- graph_builder: 텍스트 → 엔티티/관계 추출
- graph_store: networkx 기반 지식 그래프 저장소
- reranker: LLM 기반 청크 재정렬
"""
import os

from .vector_store import vector_store
from .graph_store import graph_store
from .context_builder import RAGContextBuilder

# GraphRAG 활성화 여부 (환경변수 기반)
_graph_rag_enabled = os.environ.get("GRAPH_RAG_ENABLED", "false").lower() == "true"
_reranker_enabled = os.environ.get("RERANKER_ENABLED", "false").lower() == "true"

context_builder = RAGContextBuilder(
    vector_store=vector_store,
    graph_store=graph_store,
    graph_rag_enabled=_graph_rag_enabled,
    reranker_enabled=_reranker_enabled,
)
