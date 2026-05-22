"""KnowledgeDocument — RAG 지식 문서 Aggregate Root.

워크스페이스에 등록된 한 문서. 여러 KnowledgeChunk를 보유.
청킹 정책 자체는 외부(`ITextChunker`)에서 수행하지만, Aggregate는
조립된 청크의 일관성(인덱스 연속성, 비어있지 않음 등)을 보장한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.value_objects import (
    DocumentId,
    SourceType,
    WorkspaceId,
)


@dataclass
class KnowledgeDocument:
    """KnowledgeDocument Aggregate Root.

    문서 단위로 저장·삭제·검색 권한이 결정된다 (Aggregate boundary).
    `chunks`는 불변 tuple로 보관. 입력이 list여도 __post_init__에서 변환.
    """
    document_id: DocumentId
    workspace_id: WorkspaceId
    title: str
    source_type: SourceType
    chunks: tuple[KnowledgeChunk, ...]
    uploaded_at: Optional[datetime] = None

    def __post_init__(self):
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("KnowledgeDocument.title은 비어있을 수 없음")
        if not self.chunks:
            raise ValueError("KnowledgeDocument.chunks는 비어있을 수 없음")
        if not isinstance(self.chunks, tuple):
            object.__setattr__(self, "chunks", tuple(self.chunks))

        # chunk_index 연속성 검증 (0..N-1 순서)
        indices = [c.chunk_index for c in self.chunks]
        if indices != list(range(len(self.chunks))):
            raise ValueError(
                f"chunk_index는 0부터 연속이어야 함: {indices}"
            )

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def total_text_length(self) -> int:
        return sum(len(c.text) for c in self.chunks)

    def chunk_texts(self) -> list[str]:
        """ChromaDB add용 청크 본문 리스트."""
        return [c.text for c in self.chunks]

    def chunk_ids(self) -> list[str]:
        """ChromaDB add용 ID 리스트."""
        return [c.chunk_id.value for c in self.chunks]
