"""
RAG (Retrieval-Augmented Generation) 지식 참조 패키지
- vector_store: ChromaDB 기반 벡터 저장소
- chunker: 문서 텍스트 분할
- context_builder: 검색 결과 → 프롬프트 컨텍스트 변환
"""
from .vector_store import vector_store
from .context_builder import RAGContextBuilder

context_builder = RAGContextBuilder(vector_store)
