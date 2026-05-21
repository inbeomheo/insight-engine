"""ChromaVectorStore — `IVectorStore` 어댑터.

`services/rag/vector_store.py`의 기존 `VectorStore`를 lazy import로 wrap한다.
- workspace_id.value를 user_id로 그대로 전달 (기존 컬렉션명 `user_{user_id}` 호환)
- 검색 결과 dict 리스트를 도메인 `RetrievedChunk`로 변환
- chromadb가 미설치된 테스트 환경에서도 모듈 import는 가능해야 함 → lazy import 필수
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.contexts.knowledge.application.ports import IVectorStore, RetrievedChunk
from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.exceptions import (
    IndexingFailed,
    VectorStoreUnavailable,
)
from src.contexts.knowledge.domain.knowledge_document import KnowledgeDocument
from src.contexts.knowledge.domain.value_objects import (
    ChunkId,
    DocumentId,
    Embedding,
    WorkspaceId,
)

logger = logging.getLogger(__name__)

# 검색 결과 dict에서 metadata로 보존하고 싶은 키 (인덱싱 시 동일 키만 보낸다)
_METADATA_KEYS = ("filename", "uploaded_at", "source_type", "title")


class ChromaVectorStore(IVectorStore):
    """ChromaDB 기반 벡터 스토어 어댑터.

    내부적으로 `services.rag.vector_store.vector_store` 싱글턴을 lazy import.
    """

    def _load_backend(self):
        """기존 VectorStore 싱글턴을 lazy import. 실패 시 VectorStoreUnavailable."""
        try:
            from services.rag.vector_store import vector_store as _vs
        except ImportError as e:
            raise VectorStoreUnavailable(
                f"services.rag.vector_store import 실패: {e}"
            ) from e
        return _vs

    def is_available(self) -> bool:
        """chromadb 패키지 + services/rag/vector_store 모듈 모두 import 가능해야 True."""
        try:
            import chromadb  # noqa: F401
            from services.rag.vector_store import vector_store as _vs  # noqa: F401
            return True
        except ImportError:
            return False
        except Exception as e:
            # 디렉토리 권한/초기화 실패 등도 사용 불가 처리
            logger.debug("ChromaVectorStore.is_available unexpected error: %s", e)
            return False

    def index(self, document: KnowledgeDocument) -> None:
        """문서의 모든 청크를 벡터 DB에 인덱싱.

        기존 API: `add_document(user_id, doc_id, chunks: list[str], metadata: dict)`.
        - chunk_index/doc_id는 backend가 metadata에 자동 주입하므로 여기서는 보내지 않음.
        - metadata는 첫 청크의 metadata에서 _METADATA_KEYS만 추출.
        """
        backend = self._load_backend()

        user_id = document.workspace_id.value
        doc_id = document.document_id.value
        chunk_texts = document.chunk_texts()

        # 첫 청크 metadata에서 필요한 키만 추출 (백엔드가 chunk_index, doc_id 자동 주입)
        first_meta: dict[str, Any] = dict(document.chunks[0].metadata) if document.chunks else {}
        metadata: dict[str, Any] = {
            k: first_meta[k] for k in _METADATA_KEYS if k in first_meta
        }
        # uploaded_at이 metadata에 없고 Aggregate에 있다면 ISO 문자열로 보강
        if "uploaded_at" not in metadata and document.uploaded_at is not None:
            try:
                metadata["uploaded_at"] = document.uploaded_at.isoformat()
            except Exception:
                pass
        if "title" not in metadata and document.title:
            metadata["title"] = document.title

        try:
            backend.add_document(user_id, doc_id, chunk_texts, metadata)
        except Exception as e:
            raise IndexingFailed(
                f"ChromaDB 인덱싱 실패 (workspace={user_id}, doc={doc_id}): "
                f"{type(e).__name__}: {e}"
            ) from e

    def search(
        self,
        workspace_id: WorkspaceId,
        query: str,
        top_k: int = 5,
        query_embedding: Optional[Embedding] = None,
    ) -> list[RetrievedChunk]:
        """워크스페이스 범위 유사도 검색.

        결과가 없거나 backend가 빈 결과를 주면 빈 리스트 반환 (예외 없음).
        - chunk_id 복원: metadata의 doc_id + chunk_index로 `{doc_id}_chunk_{idx}` 재구성
        - 누락 시 안전한 폴백 (`unknown_doc_chunk_{seq}`) 적용
        """
        backend = self._load_backend()
        user_id = workspace_id.value

        try:
            raw_results = backend.search(user_id, query, top_k)
        except Exception as e:
            # 검색은 예외 없이 빈 리스트가 명세이지만 로깅은 남긴다
            logger.warning(
                "ChromaVectorStore.search 실패 (workspace=%s): %s: %s",
                user_id, type(e).__name__, e,
            )
            return []

        if not raw_results:
            return []

        retrieved: list[RetrievedChunk] = []
        for seq, row in enumerate(raw_results):
            text = row.get("text") or ""
            meta = dict(row.get("metadata") or {})
            distance = float(row.get("distance", 0.0) or 0.0)

            # text가 비어 있으면 도메인 검증에서 실패 → 스킵
            if not text.strip():
                continue

            doc_id = meta.get("doc_id")
            raw_chunk_index = meta.get("chunk_index")
            try:
                chunk_index = int(raw_chunk_index) if raw_chunk_index is not None else seq
            except (TypeError, ValueError):
                chunk_index = seq
            if chunk_index < 0:
                chunk_index = seq

            if doc_id:
                chunk_id_value = f"{doc_id}_chunk_{chunk_index}"
            else:
                chunk_id_value = f"unknown_doc_chunk_{seq}"

            try:
                chunk = KnowledgeChunk(
                    chunk_id=ChunkId(chunk_id_value),
                    text=text,
                    chunk_index=chunk_index,
                    metadata=meta,
                )
            except ValueError as e:
                # 도메인 검증 실패 시 해당 행만 스킵
                logger.debug("search 결과 KnowledgeChunk 생성 실패 (skip): %s", e)
                continue

            retrieved.append(RetrievedChunk(chunk=chunk, distance=distance))

        return retrieved

    def delete(self, workspace_id: WorkspaceId, document_id: DocumentId) -> None:
        """문서에 속한 모든 청크 삭제."""
        backend = self._load_backend()
        try:
            backend.delete_document(workspace_id.value, document_id.value)
        except Exception as e:
            raise IndexingFailed(
                f"ChromaDB 삭제 실패 (workspace={workspace_id.value}, "
                f"doc={document_id.value}): {type(e).__name__}: {e}"
            ) from e
