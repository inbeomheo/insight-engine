"""Knowledge BC 포트 인터페이스 (ACL).

도메인 계층이 인프라(ChromaDB, Supabase, 임베딩 모델 등) 세부 사항에 의존하지 않도록
추상화. 각 어댑터는 `src/contexts/knowledge/infrastructure/`에서 구현.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.knowledge_document import KnowledgeDocument
from src.contexts.knowledge.domain.value_objects import (
    DocumentId,
    Embedding,
    WorkspaceId,
)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """RAG 검색 결과 1건.

    벡터 거리(distance, 0에 가까울수록 유사)와 옵션 리랭크 점수를 함께 보관.
    UseCase 호출자는 이 객체로 정렬·필터·표시까지 모두 처리 가능.
    """
    chunk: KnowledgeChunk
    distance: float
    rerank_score: Optional[float] = None


class IVectorStore(ABC):
    """벡터 인덱싱/검색 ACL.

    ChromaDB 같은 벡터 DB의 추상화. workspace_id가 격리 단위 (컬렉션/네임스페이스).
    """

    @abstractmethod
    def index(self, document: KnowledgeDocument) -> None:
        """문서의 모든 청크를 벡터 DB에 인덱싱."""

    @abstractmethod
    def search(
        self,
        workspace_id: WorkspaceId,
        query: str,
        top_k: int = 5,
        query_embedding: Optional[Embedding] = None,
    ) -> list[RetrievedChunk]:
        """워크스페이스 범위 내에서 유사도 검색.

        `query_embedding`이 주어지면 그것으로, 아니면 어댑터 내부에서 query 문자열로 검색.
        """

    @abstractmethod
    def delete(self, workspace_id: WorkspaceId, document_id: DocumentId) -> None:
        """문서에 속한 모든 청크 삭제."""

    @abstractmethod
    def is_available(self) -> bool:
        """벡터 스토어 사용 가능 여부 (chromadb 설치/디렉토리 등)."""


class IKnowledgeRepository(ABC):
    """KnowledgeDocument 메타 영속 ACL.

    벡터 인덱스(IVectorStore)와 분리된 메타데이터 저장소.
    `list_by_workspace`는 청크 본문/임베딩을 포함하지 않을 수 있음 (요약 카드용).
    """

    @abstractmethod
    def find_by_id(
        self,
        workspace_id: WorkspaceId,
        document_id: DocumentId,
    ) -> Optional[KnowledgeDocument]:
        ...

    @abstractmethod
    def list_by_workspace(self, workspace_id: WorkspaceId) -> list[KnowledgeDocument]:
        ...

    @abstractmethod
    def save(self, document: KnowledgeDocument) -> None:
        ...

    @abstractmethod
    def delete(self, workspace_id: WorkspaceId, document_id: DocumentId) -> None:
        ...


class ITextChunker(ABC):
    """텍스트를 청크 본문 리스트로 분할."""

    @abstractmethod
    def chunk(self, text: str) -> list[str]:
        """청크 본문 리스트. 빈 텍스트가 들어오면 빈 리스트."""


class IEmbeddingProvider(ABC):
    """텍스트 → 벡터 임베딩.

    선택적 포트. 사용하지 않으면 ChromaDB 기본 임베더가 자동으로 처리한다.
    명시적 임베딩 제공이 필요한 경우(GPU 모델/외부 API)에만 주입.
    """

    @abstractmethod
    def embed(self, text: str) -> Embedding: ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[Embedding]: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...


__all__ = [
    "RetrievedChunk",
    "IVectorStore",
    "IKnowledgeRepository",
    "ITextChunker",
    "IEmbeddingProvider",
]
