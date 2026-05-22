"""KnowledgeChunk 단위 테스트.

- 빈/공백 text 거부, 음수 chunk_index 거부
- has_embedding 파생 속성
- metadata 기본값 독립성 (default_factory 검증)
- frozen 불변성
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.domain.chunk import KnowledgeChunk
from src.contexts.knowledge.domain.value_objects import ChunkId, Embedding


CID = ChunkId("doc-001_chunk_0")


class TestKnowledgeChunk:
    def test_basic_construction(self) -> None:
        c = KnowledgeChunk(chunk_id=CID, text="hello world", chunk_index=0)
        assert c.chunk_id == CID
        assert c.text == "hello world"
        assert c.chunk_index == 0
        assert c.embedding is None
        assert c.metadata == {}

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            KnowledgeChunk(chunk_id=CID, text="", chunk_index=0)

    def test_whitespace_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            KnowledgeChunk(chunk_id=CID, text="   ", chunk_index=0)

    def test_newline_only_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            KnowledgeChunk(chunk_id=CID, text="\n\t\r", chunk_index=0)

    def test_negative_chunk_index_rejected(self) -> None:
        with pytest.raises(ValueError, match="0 이상의 정수"):
            KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=-1)

    def test_non_integer_chunk_index_rejected(self) -> None:
        # float은 거부 (정수만 허용)
        with pytest.raises(ValueError, match="0 이상의 정수"):
            KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=1.5)  # type: ignore[arg-type]

    def test_has_embedding_false_when_none(self) -> None:
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=0)
        assert c.has_embedding is False

    def test_has_embedding_true_when_provided(self) -> None:
        emb = Embedding((0.1, 0.2, 0.3))
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=0, embedding=emb)
        assert c.has_embedding is True
        assert c.embedding == emb

    def test_default_metadata_is_empty_dict(self) -> None:
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=0)
        assert c.metadata == {}
        assert isinstance(c.metadata, dict)

    def test_default_metadata_independent_per_instance(self) -> None:
        # default_factory 사용 시 인스턴스 간 독립적인지 검증
        # (가변 기본값 버그가 발생하지 않아야 함)
        c1 = KnowledgeChunk(chunk_id=ChunkId("c1"), text="a", chunk_index=0)
        c2 = KnowledgeChunk(chunk_id=ChunkId("c2"), text="b", chunk_index=0)
        c1.metadata["mutation"] = "leak"
        assert c2.metadata == {}
        assert c1.metadata is not c2.metadata

    def test_custom_metadata_preserved(self) -> None:
        c = KnowledgeChunk(
            chunk_id=CID,
            text="ok",
            chunk_index=0,
            metadata={"filename": "doc.md", "doc_id": "doc-001"},
        )
        assert c.metadata == {"filename": "doc.md", "doc_id": "doc-001"}

    def test_immutable_frozen(self) -> None:
        # frozen=True → 필드 재할당 시 예외
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=0)
        with pytest.raises((AttributeError, Exception)):
            c.text = "modified"  # type: ignore[misc]

    def test_chunk_index_zero_allowed(self) -> None:
        # 0은 유효 (음수만 거부)
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=0)
        assert c.chunk_index == 0

    def test_large_chunk_index_allowed(self) -> None:
        c = KnowledgeChunk(chunk_id=CID, text="ok", chunk_index=999)
        assert c.chunk_index == 999
