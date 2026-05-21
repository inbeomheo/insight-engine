"""Knowledge BC 유스케이스.

- `IndexDocumentUseCase`: 원문 텍스트 → 청킹 → KnowledgeDocument 조립 → 인덱싱 + 메타 저장
- `RetrieveContextUseCase`: 쿼리 → 벡터 검색 → RetrievedChunk 리스트
- `DeleteDocumentUseCase`: 문서 + 모든 청크 삭제 (인덱스 + 메타 양쪽)
- `ListDocumentsUseCase`: 워크스페이스 문서 목록 조회
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from src.contexts.knowledge.application.ports import (
    IKnowledgeRepository,
    ITextChunker,
    IVectorStore,
    RetrievedChunk,
)
from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.events import (
    ContextRetrieved,
    DocumentDeleted,
    DocumentIndexed,
)
from src.contexts.knowledge.domain.exceptions import (
    ChunkingFailed,
    DocumentNotFound,
    IndexingFailed,
    VectorStoreUnavailable,
)
from src.contexts.knowledge.domain.knowledge_document import KnowledgeDocument
from src.contexts.knowledge.domain.value_objects import (
    ChunkId,
    DocumentId,
    SourceType,
    WorkspaceId,
)

logger = logging.getLogger(__name__)


@dataclass
class IndexDocumentUseCase:
    """텍스트를 청킹 → KnowledgeDocument 조립 → 벡터 인덱싱 + 메타 저장."""
    repository: IKnowledgeRepository
    vector_store: IVectorStore
    chunker: ITextChunker

    def execute(
        self,
        workspace_id: WorkspaceId,
        title: str,
        source_text: str,
        source_type: SourceType,
        document_id: Optional[DocumentId] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> KnowledgeDocument:
        if not self.vector_store.is_available():
            raise VectorStoreUnavailable(
                "벡터 스토어 사용 불가 (chromadb 미설치/경로 권한)"
            )

        if not source_text or not source_text.strip():
            raise ChunkingFailed("source_text가 비어있음")

        chunk_texts = self.chunker.chunk(source_text)
        if not chunk_texts:
            raise ChunkingFailed("청킹 결과가 비어있음 (텍스트가 너무 짧거나 공백만)")

        doc_id = document_id or DocumentId(uuid.uuid4().hex)
        base_meta = dict(metadata or {})
        base_meta.setdefault("filename", title)
        base_meta.setdefault("doc_id", doc_id.value)

        chunks: list[KnowledgeChunk] = []
        for idx, text in enumerate(chunk_texts):
            chunks.append(
                KnowledgeChunk(
                    chunk_id=ChunkId(f"{doc_id.value}_chunk_{idx}"),
                    text=text,
                    chunk_index=idx,
                    metadata={**base_meta, "chunk_index": idx},
                )
            )

        document = KnowledgeDocument(
            document_id=doc_id,
            workspace_id=workspace_id,
            title=title,
            source_type=source_type,
            chunks=tuple(chunks),
            uploaded_at=datetime.now(timezone.utc),
        )

        try:
            self.vector_store.index(document)
        except VectorStoreUnavailable:
            raise
        except Exception as e:
            raise IndexingFailed(
                f"벡터 인덱싱 실패: {type(e).__name__}: {e}"
            ) from e

        self.repository.save(document)

        logger.info(
            "document indexed: workspace=%s doc=%s chunks=%d",
            workspace_id.value, doc_id.value, document.chunk_count,
        )
        # 이벤트는 일단 로깅으로만 (Phase 4에서 디스패처 없음)
        _ = DocumentIndexed(
            occurred_at=datetime.now(timezone.utc),
            document_id=doc_id,
            workspace_id=workspace_id,
            source_type=source_type,
            chunk_count=document.chunk_count,
        )
        return document


@dataclass
class RetrieveContextUseCase:
    """쿼리 → 벡터 검색 → RetrievedChunk 리스트.

    ContentGeneration BC가 호출하는 RAG 진입점.
    벡터 스토어 사용 불가 시 graceful: 빈 리스트 반환 (예외 X).
    """
    vector_store: IVectorStore

    def execute(
        self,
        workspace_id: WorkspaceId,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if not query or not query.strip():
            return []
        if top_k <= 0:
            return []
        if not self.vector_store.is_available():
            logger.debug("vector store unavailable, returning empty context")
            return []

        try:
            results = self.vector_store.search(
                workspace_id=workspace_id,
                query=query,
                top_k=top_k,
            )
        except Exception as e:
            logger.warning("vector search failed, returning empty: %s", e)
            return []

        _ = ContextRetrieved(
            occurred_at=datetime.now(timezone.utc),
            workspace_id=workspace_id,
            query_length=len(query),
            chunk_count=len(results),
        )
        return results


@dataclass
class DeleteDocumentUseCase:
    """문서 + 모든 청크 삭제."""
    repository: IKnowledgeRepository
    vector_store: IVectorStore

    def execute(
        self,
        workspace_id: WorkspaceId,
        document_id: DocumentId,
    ) -> None:
        existing = self.repository.find_by_id(workspace_id, document_id)
        if existing is None:
            raise DocumentNotFound(document_id, workspace_id)

        if self.vector_store.is_available():
            try:
                self.vector_store.delete(workspace_id, document_id)
            except Exception as e:
                logger.warning(
                    "vector delete failed, proceeding with metadata delete: %s", e,
                )

        self.repository.delete(workspace_id, document_id)

        _ = DocumentDeleted(
            occurred_at=datetime.now(timezone.utc),
            document_id=document_id,
            workspace_id=workspace_id,
        )


@dataclass
class ListDocumentsUseCase:
    """워크스페이스 내 문서 목록 조회."""
    repository: IKnowledgeRepository

    def execute(self, workspace_id: WorkspaceId) -> list[KnowledgeDocument]:
        return self.repository.list_by_workspace(workspace_id)
