"""KnowledgeChunk — 문서를 청킹한 단편.

`KnowledgeDocument` Aggregate의 구성 요소. 단독으로 영속화·검색되지만
도메인 계층에서는 항상 문서 컨텍스트와 함께 다뤄야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.contexts.knowledge.domain.value_objects import ChunkId, Embedding


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """문서의 청크 한 조각.

    - `text`: 청크 본문 (공백만은 거부)
    - `chunk_index`: 문서 내 순번 (0부터)
    - `embedding`: 선택. 어댑터에서 인덱싱 시 채워질 수 있음.
    - `metadata`: 출처 표시 등 보조 정보 (filename, doc_id, uploaded_at 등)
    """
    chunk_id: ChunkId
    text: str
    chunk_index: int
    embedding: Optional[Embedding] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("KnowledgeChunk.text는 비어있을 수 없음")
        if not isinstance(self.chunk_index, int) or self.chunk_index < 0:
            raise ValueError(f"chunk_index는 0 이상의 정수: {self.chunk_index!r}")

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None
