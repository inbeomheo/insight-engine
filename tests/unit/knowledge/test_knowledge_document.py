"""KnowledgeDocument Aggregate 단위 테스트.

- 빈 title / 빈 chunks 거부
- list로 들어온 chunks가 tuple로 변환
- chunk_index 연속성 검증 (불연속·역순 거부)
- 파생 속성: chunk_count / total_text_length / chunk_texts() / chunk_ids()
- uploaded_at 옵셔널
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.knowledge_document import KnowledgeDocument
from src.contexts.knowledge.domain.value_objects import (
    ChunkId,
    DocumentId,
    SourceType,
    WorkspaceId,
)


DOC_ID = DocumentId("doc-001")
WS_ID = WorkspaceId("ws-001")
FIXED_TS = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)


def make_chunk(idx: int, text: str = "default-text") -> KnowledgeChunk:
    """헬퍼: 연속 인덱스의 청크 생성."""
    return KnowledgeChunk(
        chunk_id=ChunkId(f"doc-001_chunk_{idx}"),
        text=text,
        chunk_index=idx,
    )


class TestKnowledgeDocument:
    def test_basic_construction(self) -> None:
        chunks = (make_chunk(0, "first"), make_chunk(1, "second"))
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Document",
            source_type=SourceType.MARKDOWN,
            chunks=chunks,
        )
        assert doc.document_id == DOC_ID
        assert doc.workspace_id == WS_ID
        assert doc.title == "My Document"
        assert doc.source_type == SourceType.MARKDOWN
        assert doc.chunks == chunks
        assert doc.uploaded_at is None

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="title은 비어있을 수 없음"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="",
                source_type=SourceType.TEXT,
                chunks=(make_chunk(0),),
            )

    def test_whitespace_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="title은 비어있을 수 없음"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="   ",
                source_type=SourceType.TEXT,
                chunks=(make_chunk(0),),
            )

    def test_empty_chunks_rejected(self) -> None:
        with pytest.raises(ValueError, match="chunks는 비어있을 수 없음"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="My Doc",
                source_type=SourceType.TEXT,
                chunks=(),
            )

    def test_list_chunks_converted_to_tuple(self) -> None:
        # __post_init__에서 list → tuple 자동 변환
        chunks_list = [make_chunk(0), make_chunk(1)]
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=chunks_list,  # type: ignore[arg-type]
        )
        assert isinstance(doc.chunks, tuple)
        assert len(doc.chunks) == 2

    def test_non_continuous_chunk_index_rejected(self) -> None:
        # 0, 2 (1이 빠짐) — 불연속
        bad_chunks = (make_chunk(0), make_chunk(2))
        with pytest.raises(ValueError, match="0부터 연속"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="My Doc",
                source_type=SourceType.TEXT,
                chunks=bad_chunks,
            )

    def test_out_of_order_chunk_index_rejected(self) -> None:
        # 1, 0 — 순서 어긋남
        bad_chunks = (make_chunk(1), make_chunk(0))
        with pytest.raises(ValueError, match="0부터 연속"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="My Doc",
                source_type=SourceType.TEXT,
                chunks=bad_chunks,
            )

    def test_not_starting_at_zero_rejected(self) -> None:
        # 1부터 시작 — 0부터가 아니므로 거부
        bad_chunks = (make_chunk(1), make_chunk(2))
        with pytest.raises(ValueError, match="0부터 연속"):
            KnowledgeDocument(
                document_id=DOC_ID,
                workspace_id=WS_ID,
                title="My Doc",
                source_type=SourceType.TEXT,
                chunks=bad_chunks,
            )

    def test_chunk_count(self) -> None:
        chunks = (make_chunk(0), make_chunk(1), make_chunk(2))
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=chunks,
        )
        assert doc.chunk_count == 3

    def test_total_text_length(self) -> None:
        # "hello"(5) + "world!"(6) = 11
        chunks = (make_chunk(0, "hello"), make_chunk(1, "world!"))
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=chunks,
        )
        assert doc.total_text_length == 11

    def test_chunk_texts(self) -> None:
        chunks = (make_chunk(0, "hello"), make_chunk(1, "world"))
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=chunks,
        )
        assert doc.chunk_texts() == ["hello", "world"]

    def test_chunk_ids(self) -> None:
        chunks = (make_chunk(0), make_chunk(1))
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=chunks,
        )
        assert doc.chunk_ids() == ["doc-001_chunk_0", "doc-001_chunk_1"]

    def test_uploaded_at_optional(self) -> None:
        # 미지정 시 None
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=(make_chunk(0),),
        )
        assert doc.uploaded_at is None

    def test_uploaded_at_preserved(self) -> None:
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="My Doc",
            source_type=SourceType.TEXT,
            chunks=(make_chunk(0),),
            uploaded_at=FIXED_TS,
        )
        assert doc.uploaded_at == FIXED_TS

    def test_single_chunk_document(self) -> None:
        # 청크 1개도 정상
        doc = KnowledgeDocument(
            document_id=DOC_ID,
            workspace_id=WS_ID,
            title="Single",
            source_type=SourceType.PDF,
            chunks=(make_chunk(0, "only"),),
        )
        assert doc.chunk_count == 1
        assert doc.total_text_length == 4
