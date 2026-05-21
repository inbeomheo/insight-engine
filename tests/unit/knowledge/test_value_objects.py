"""Knowledge BC 값 객체(VO) 단위 테스트.

- `DocumentId` / `ChunkId` / `WorkspaceId`: 비어있지 않은 문자열 검증 + frozen 불변성
- `Embedding`: list→tuple 자동 변환, dimension 속성, from_iterable 클래스메서드
- `SourceType`: 5개 멤버 + from_filename 확장자 매핑
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.domain.value_objects import (
    ChunkId,
    DocumentId,
    Embedding,
    SourceType,
    WorkspaceId,
)


class TestDocumentId:
    def test_valid_value(self) -> None:
        doc_id = DocumentId("doc-001")
        assert doc_id.value == "doc-001"

    def test_uuid_like_value(self) -> None:
        # UUID hex 문자열도 정상 통과
        doc_id = DocumentId("abc123def456")
        assert doc_id.value == "abc123def456"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            DocumentId("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            DocumentId("   ")

    def test_none_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            DocumentId(None)  # type: ignore[arg-type]

    def test_immutable_frozen_slots(self) -> None:
        # frozen=True, slots=True인 dataclass는 수정 시 AttributeError 발생
        doc_id = DocumentId("doc-001")
        with pytest.raises((AttributeError, Exception)):
            doc_id.value = "new-value"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        # frozen dataclass는 값 기반 동등성
        assert DocumentId("doc-001") == DocumentId("doc-001")
        assert DocumentId("doc-001") != DocumentId("doc-002")

    def test_hashable(self) -> None:
        # frozen → hashable → set/dict 키로 사용 가능
        s = {DocumentId("doc-001"), DocumentId("doc-001"), DocumentId("doc-002")}
        assert len(s) == 2


class TestChunkId:
    def test_valid_value(self) -> None:
        cid = ChunkId("doc-001_chunk_0")
        assert cid.value == "doc-001_chunk_0"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            ChunkId("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            ChunkId("  \t  ")

    def test_immutable_frozen(self) -> None:
        cid = ChunkId("doc-001_chunk_0")
        with pytest.raises((AttributeError, Exception)):
            cid.value = "doc-001_chunk_1"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        assert ChunkId("c1") == ChunkId("c1")
        assert ChunkId("c1") != ChunkId("c2")


class TestWorkspaceId:
    def test_valid_value(self) -> None:
        ws = WorkspaceId("ws-001")
        assert ws.value == "ws-001"

    def test_user_id_as_workspace_id(self) -> None:
        # user_id 그대로 워크스페이스 ID로 쓰는 기존 호환
        ws = WorkspaceId("user-uuid-12345")
        assert ws.value == "user-uuid-12345"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            WorkspaceId("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있지 않은 문자열"):
            WorkspaceId(" ")

    def test_immutable_frozen(self) -> None:
        ws = WorkspaceId("ws-001")
        with pytest.raises((AttributeError, Exception)):
            ws.value = "ws-002"  # type: ignore[misc]


class TestEmbedding:
    def test_tuple_input(self) -> None:
        emb = Embedding((0.1, 0.2, 0.3))
        assert emb.values == (0.1, 0.2, 0.3)
        assert emb.dimension == 3

    def test_list_converted_to_tuple(self) -> None:
        # list 입력 시 __post_init__에서 tuple로 자동 변환
        emb = Embedding([0.1, 0.2, 0.3])  # type: ignore[arg-type]
        assert isinstance(emb.values, tuple)
        assert emb.values == (0.1, 0.2, 0.3)

    def test_empty_list_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            Embedding(())

    def test_empty_iterable_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어있을 수 없음"):
            Embedding([])  # type: ignore[arg-type]

    def test_non_numeric_element_rejected(self) -> None:
        with pytest.raises(ValueError, match="수치형"):
            Embedding((0.1, "bad", 0.3))  # type: ignore[arg-type]

    def test_none_element_rejected(self) -> None:
        with pytest.raises(ValueError, match="수치형"):
            Embedding((0.1, None, 0.3))  # type: ignore[arg-type]

    def test_int_elements_allowed(self) -> None:
        # int도 수치형으로 허용
        emb = Embedding((1, 2, 3))
        assert emb.values == (1, 2, 3)
        assert emb.dimension == 3

    def test_dimension_property(self) -> None:
        assert Embedding((0.1,)).dimension == 1
        assert Embedding((0.1, 0.2, 0.3, 0.4)).dimension == 4

    def test_from_iterable_classmethod(self) -> None:
        # 제너레이터에서도 정상 생성
        emb = Embedding.from_iterable(iter([1, 2, 3]))
        assert emb.values == (1.0, 2.0, 3.0)
        assert emb.dimension == 3

    def test_from_iterable_converts_to_float(self) -> None:
        # int 입력도 float로 변환
        emb = Embedding.from_iterable([1, 2, 3])
        assert all(isinstance(v, float) for v in emb.values)

    def test_immutable_frozen(self) -> None:
        emb = Embedding((0.1, 0.2))
        with pytest.raises((AttributeError, Exception)):
            emb.values = (0.5, 0.6)  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        assert Embedding((0.1, 0.2)) == Embedding((0.1, 0.2))
        assert Embedding((0.1, 0.2)) != Embedding((0.1, 0.3))


class TestSourceType:
    def test_pdf_value(self) -> None:
        assert SourceType.PDF.value == "pdf"

    def test_markdown_value(self) -> None:
        assert SourceType.MARKDOWN.value == "markdown"

    def test_text_value(self) -> None:
        assert SourceType.TEXT.value == "text"

    def test_web_value(self) -> None:
        assert SourceType.WEB.value == "web"

    def test_note_value(self) -> None:
        assert SourceType.NOTE.value == "note"

    def test_exactly_five_members(self) -> None:
        # 5개 멤버 고정 — 추가 시 from_filename 매핑 정책 재검토 필요
        assert len(list(SourceType)) == 5

    def test_from_filename_pdf(self) -> None:
        assert SourceType.from_filename("report.pdf") == SourceType.PDF
        assert SourceType.from_filename("REPORT.PDF") == SourceType.PDF

    def test_from_filename_md(self) -> None:
        assert SourceType.from_filename("README.md") == SourceType.MARKDOWN

    def test_from_filename_markdown(self) -> None:
        # .markdown 확장자도 MARKDOWN으로 매핑
        assert SourceType.from_filename("doc.markdown") == SourceType.MARKDOWN

    def test_from_filename_txt(self) -> None:
        assert SourceType.from_filename("notes.txt") == SourceType.TEXT

    def test_from_filename_unknown_extension_falls_back_to_text(self) -> None:
        # 알 수 없는 확장자는 TEXT 폴백
        assert SourceType.from_filename("file.docx") == SourceType.TEXT
        assert SourceType.from_filename("data.json") == SourceType.TEXT

    def test_from_filename_empty_string(self) -> None:
        # 빈 문자열도 TEXT 폴백
        assert SourceType.from_filename("") == SourceType.TEXT

    def test_from_filename_no_extension(self) -> None:
        # 확장자 없는 파일명도 TEXT 폴백
        assert SourceType.from_filename("README") == SourceType.TEXT
