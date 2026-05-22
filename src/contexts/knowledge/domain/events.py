"""Knowledge BC 도메인 이벤트."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.contexts.knowledge.domain.value_objects import (
    DocumentId,
    SourceType,
    WorkspaceId,
)


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentIndexed(DomainEvent):
    """문서 인덱싱 성공."""
    document_id: DocumentId
    workspace_id: WorkspaceId
    source_type: SourceType
    chunk_count: int


@dataclass(frozen=True)
class DocumentDeleted(DomainEvent):
    """문서 삭제 완료."""
    document_id: DocumentId
    workspace_id: WorkspaceId


@dataclass(frozen=True)
class ContextRetrieved(DomainEvent):
    """RAG 검색 수행."""
    workspace_id: WorkspaceId
    query_length: int
    chunk_count: int
