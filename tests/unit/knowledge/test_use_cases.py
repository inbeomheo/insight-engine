"""Knowledge BC UseCase 단위 테스트.

각 UseCase 동작을 MagicMock(spec=...)으로 의존성 대체하여 검증.

- IndexDocumentUseCase: 청킹 → 조립 → 인덱싱 → 메타 저장
- RetrieveContextUseCase: graceful 검색 (예외 시 빈 리스트 반환)
- DeleteDocumentUseCase: 인덱스 + 메타 양쪽 삭제 (벡터 실패 시 메타는 진행)
- ListDocumentsUseCase: repository 위임
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.contexts.knowledge.application.ports import (
    IKnowledgeRepository,
    ITextChunker,
    IVectorStore,
    RetrievedChunk,
)
from src.contexts.knowledge.application.use_cases import (
    DeleteDocumentUseCase,
    IndexDocumentUseCase,
    ListDocumentsUseCase,
    RetrieveContextUseCase,
)
from src.contexts.knowledge.domain.chunk import KnowledgeChunk
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


WS_ID = WorkspaceId("ws-001")
DOC_ID = DocumentId("doc-001")


def make_repository() -> MagicMock:
    """IKnowledgeRepository mock 팩토리."""
    return MagicMock(spec=IKnowledgeRepository)


def make_vector_store(available: bool = True) -> MagicMock:
    """IVectorStore mock 팩토리.

    is_available은 메서드(callable) → return_value로 설정.
    """
    vs = MagicMock(spec=IVectorStore)
    vs.is_available.return_value = available
    return vs


def make_chunker(chunks: list[str]) -> MagicMock:
    """ITextChunker mock 팩토리 — 미리 정해진 청크 리스트 반환."""
    ch = MagicMock(spec=ITextChunker)
    ch.chunk.return_value = chunks
    return ch


# ---------------------------------------------------------------------------
# IndexDocumentUseCase
# ---------------------------------------------------------------------------


class TestIndexDocumentUseCase:
    def test_vector_store_unavailable_raises(self) -> None:
        repo = make_repository()
        vs = make_vector_store(available=False)
        chunker = make_chunker(["chunk1"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(VectorStoreUnavailable):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="some text",
                source_type=SourceType.TEXT,
            )
        # 인덱싱·저장 어느 쪽도 호출되면 안 됨
        vs.index.assert_not_called()
        repo.save.assert_not_called()
        chunker.chunk.assert_not_called()

    def test_empty_source_text_raises_chunking_failed(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["unused"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(ChunkingFailed):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="",
                source_type=SourceType.TEXT,
            )
        chunker.chunk.assert_not_called()

    def test_whitespace_only_source_text_raises_chunking_failed(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["unused"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(ChunkingFailed):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="   \n\t  ",
                source_type=SourceType.TEXT,
            )
        chunker.chunk.assert_not_called()

    def test_empty_chunk_result_raises_chunking_failed(self) -> None:
        # chunker가 빈 리스트 반환 → 청킹 실패로 간주
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker([])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(ChunkingFailed, match="비어있음"):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="some text",
                source_type=SourceType.TEXT,
            )
        vs.index.assert_not_called()
        repo.save.assert_not_called()

    def test_successful_indexing_calls_vector_store_and_repository(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["chunk-a", "chunk-b"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        doc = uc.execute(
            workspace_id=WS_ID,
            title="my-title",
            source_text="text to be chunked",
            source_type=SourceType.MARKDOWN,
            document_id=DOC_ID,
        )

        # vector_store.index와 repository.save가 호출되어야 함
        vs.index.assert_called_once()
        repo.save.assert_called_once()
        # 두 호출 모두 같은 문서를 받았는지 확인
        indexed_doc = vs.index.call_args.args[0]
        saved_doc = repo.save.call_args.args[0]
        assert indexed_doc is doc
        assert saved_doc is doc

    def test_auto_generates_document_id_when_not_provided(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["text"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        doc = uc.execute(
            workspace_id=WS_ID,
            title="t",
            source_text="content",
            source_type=SourceType.TEXT,
        )

        # document_id가 자동 생성 (uuid 기반, 비어있지 않은 문자열)
        assert isinstance(doc.document_id, DocumentId)
        assert doc.document_id.value
        assert len(doc.document_id.value) > 0

    def test_provided_document_id_is_used(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["text"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        custom_id = DocumentId("custom-doc-id")
        doc = uc.execute(
            workspace_id=WS_ID,
            title="t",
            source_text="content",
            source_type=SourceType.TEXT,
            document_id=custom_id,
        )

        assert doc.document_id == custom_id

    def test_metadata_propagated_to_chunks(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["a", "b"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        doc = uc.execute(
            workspace_id=WS_ID,
            title="my-title",
            source_text="content",
            source_type=SourceType.TEXT,
            document_id=DOC_ID,
            metadata={"source": "upload", "user": "alice"},
        )

        # 모든 청크에 사용자 메타 + filename/doc_id가 포함되어야 함
        for chunk in doc.chunks:
            assert chunk.metadata["source"] == "upload"
            assert chunk.metadata["user"] == "alice"
            assert chunk.metadata["filename"] == "my-title"
            assert chunk.metadata["doc_id"] == DOC_ID.value

    def test_chunk_indices_are_continuous(self) -> None:
        # chunker 결과 N개 → chunk_index 0..N-1 자동 부여
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["a", "b", "c", "d"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        doc = uc.execute(
            workspace_id=WS_ID,
            title="t",
            source_text="content",
            source_type=SourceType.TEXT,
            document_id=DOC_ID,
        )

        indices = [c.chunk_index for c in doc.chunks]
        assert indices == [0, 1, 2, 3]

    def test_chunk_ids_follow_pattern(self) -> None:
        # 패턴: {doc_id}_chunk_{idx}
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["a", "b"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        doc = uc.execute(
            workspace_id=WS_ID,
            title="t",
            source_text="content",
            source_type=SourceType.TEXT,
            document_id=DOC_ID,
        )

        assert doc.chunks[0].chunk_id == ChunkId("doc-001_chunk_0")
        assert doc.chunks[1].chunk_id == ChunkId("doc-001_chunk_1")

    def test_vector_store_index_exception_promoted_to_indexing_failed(self) -> None:
        # 일반 예외는 IndexingFailed로 승격
        repo = make_repository()
        vs = make_vector_store()
        vs.index.side_effect = RuntimeError("chromadb write error")
        chunker = make_chunker(["text"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(IndexingFailed, match="벡터 인덱싱 실패"):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="content",
                source_type=SourceType.TEXT,
            )

    def test_vector_store_unavailable_during_index_propagates(self) -> None:
        # VectorStoreUnavailable는 그대로 전파 (IndexingFailed로 감싸지 않음)
        repo = make_repository()
        vs = make_vector_store()
        vs.index.side_effect = VectorStoreUnavailable("chromadb closed mid-write")
        chunker = make_chunker(["text"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(VectorStoreUnavailable):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="content",
                source_type=SourceType.TEXT,
            )

    def test_repository_not_called_when_indexing_fails(self) -> None:
        # 인덱싱 실패 시 메타 저장은 진행되면 안 됨 (atomicity)
        repo = make_repository()
        vs = make_vector_store()
        vs.index.side_effect = RuntimeError("boom")
        chunker = make_chunker(["text"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        with pytest.raises(IndexingFailed):
            uc.execute(
                workspace_id=WS_ID,
                title="t",
                source_text="content",
                source_type=SourceType.TEXT,
            )

        repo.save.assert_not_called()

    def test_returns_knowledge_document(self) -> None:
        repo = make_repository()
        vs = make_vector_store()
        chunker = make_chunker(["a"])
        uc = IndexDocumentUseCase(repository=repo, vector_store=vs, chunker=chunker)

        result = uc.execute(
            workspace_id=WS_ID,
            title="t",
            source_text="content",
            source_type=SourceType.TEXT,
        )

        assert isinstance(result, KnowledgeDocument)
        assert result.workspace_id == WS_ID
        assert result.title == "t"
        assert result.source_type == SourceType.TEXT
        # uploaded_at은 timezone-aware datetime이어야 함
        assert result.uploaded_at is not None
        assert result.uploaded_at.tzinfo is not None


# ---------------------------------------------------------------------------
# RetrieveContextUseCase
# ---------------------------------------------------------------------------


class TestRetrieveContextUseCase:
    def test_empty_query_returns_empty_list(self) -> None:
        vs = make_vector_store()
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="", top_k=5)

        assert results == []
        vs.search.assert_not_called()

    def test_whitespace_query_returns_empty_list(self) -> None:
        vs = make_vector_store()
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="   \n  ", top_k=5)

        assert results == []
        vs.search.assert_not_called()

    def test_top_k_zero_returns_empty_list(self) -> None:
        vs = make_vector_store()
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="hello", top_k=0)

        assert results == []
        vs.search.assert_not_called()

    def test_top_k_negative_returns_empty_list(self) -> None:
        vs = make_vector_store()
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="hello", top_k=-3)

        assert results == []
        vs.search.assert_not_called()

    def test_vector_store_unavailable_returns_empty_no_exception(self) -> None:
        # graceful: 예외 던지지 않고 빈 리스트
        vs = make_vector_store(available=False)
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="hello", top_k=5)

        assert results == []
        vs.search.assert_not_called()

    def test_search_exception_returns_empty_no_exception(self) -> None:
        # vector_store.search가 예외 → graceful 빈 리스트
        vs = make_vector_store()
        vs.search.side_effect = RuntimeError("chromadb query failed")
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="hello", top_k=5)

        assert results == []

    def test_returns_vector_store_results_as_is(self) -> None:
        # 정상 시 vector_store.search 결과 그대로 반환
        chunk = KnowledgeChunk(
            chunk_id=ChunkId("c1"), text="result", chunk_index=0,
        )
        retrieved = [RetrievedChunk(chunk=chunk, distance=0.1, rerank_score=None)]
        vs = make_vector_store()
        vs.search.return_value = retrieved
        uc = RetrieveContextUseCase(vector_store=vs)

        results = uc.execute(workspace_id=WS_ID, query="hello", top_k=5)

        assert results is retrieved
        assert len(results) == 1
        assert results[0].chunk.text == "result"

    def test_workspace_id_query_top_k_passed_to_search(self) -> None:
        vs = make_vector_store()
        vs.search.return_value = []
        uc = RetrieveContextUseCase(vector_store=vs)

        uc.execute(workspace_id=WS_ID, query="my-query", top_k=7)

        vs.search.assert_called_once_with(
            workspace_id=WS_ID, query="my-query", top_k=7,
        )

    def test_default_top_k_is_five(self) -> None:
        vs = make_vector_store()
        vs.search.return_value = []
        uc = RetrieveContextUseCase(vector_store=vs)

        uc.execute(workspace_id=WS_ID, query="hello")

        vs.search.assert_called_once_with(
            workspace_id=WS_ID, query="hello", top_k=5,
        )


# ---------------------------------------------------------------------------
# DeleteDocumentUseCase
# ---------------------------------------------------------------------------


def make_existing_document() -> KnowledgeDocument:
    """find_by_id 응답용 더미 문서."""
    chunk = KnowledgeChunk(
        chunk_id=ChunkId("doc-001_chunk_0"),
        text="existing",
        chunk_index=0,
    )
    return KnowledgeDocument(
        document_id=DOC_ID,
        workspace_id=WS_ID,
        title="existing",
        source_type=SourceType.TEXT,
        chunks=(chunk,),
    )


class TestDeleteDocumentUseCase:
    def test_document_not_found_raises(self) -> None:
        repo = make_repository()
        repo.find_by_id.return_value = None
        vs = make_vector_store()
        uc = DeleteDocumentUseCase(repository=repo, vector_store=vs)

        with pytest.raises(DocumentNotFound):
            uc.execute(workspace_id=WS_ID, document_id=DOC_ID)

        # vector / repo delete 모두 호출되면 안 됨
        vs.delete.assert_not_called()
        repo.delete.assert_not_called()

    def test_successful_delete_calls_both_vector_and_repository(self) -> None:
        repo = make_repository()
        repo.find_by_id.return_value = make_existing_document()
        vs = make_vector_store()
        uc = DeleteDocumentUseCase(repository=repo, vector_store=vs)

        uc.execute(workspace_id=WS_ID, document_id=DOC_ID)

        vs.delete.assert_called_once_with(WS_ID, DOC_ID)
        repo.delete.assert_called_once_with(WS_ID, DOC_ID)

    def test_vector_store_unavailable_still_deletes_metadata(self) -> None:
        # 벡터 사용 불가 시 vector.delete는 skip, repo.delete만 호출
        repo = make_repository()
        repo.find_by_id.return_value = make_existing_document()
        vs = make_vector_store(available=False)
        uc = DeleteDocumentUseCase(repository=repo, vector_store=vs)

        uc.execute(workspace_id=WS_ID, document_id=DOC_ID)

        vs.delete.assert_not_called()
        repo.delete.assert_called_once_with(WS_ID, DOC_ID)

    def test_vector_delete_exception_proceeds_to_metadata_delete(self) -> None:
        # vector.delete가 예외를 던져도 repo.delete는 진행 (graceful)
        repo = make_repository()
        repo.find_by_id.return_value = make_existing_document()
        vs = make_vector_store()
        vs.delete.side_effect = RuntimeError("vector delete crashed")
        uc = DeleteDocumentUseCase(repository=repo, vector_store=vs)

        uc.execute(workspace_id=WS_ID, document_id=DOC_ID)

        vs.delete.assert_called_once()
        repo.delete.assert_called_once_with(WS_ID, DOC_ID)


# ---------------------------------------------------------------------------
# ListDocumentsUseCase
# ---------------------------------------------------------------------------


class TestListDocumentsUseCase:
    def test_returns_repository_result(self) -> None:
        docs = [make_existing_document()]
        repo = make_repository()
        repo.list_by_workspace.return_value = docs
        uc = ListDocumentsUseCase(repository=repo)

        result = uc.execute(workspace_id=WS_ID)

        assert result is docs
        repo.list_by_workspace.assert_called_once_with(WS_ID)

    def test_empty_list_returned_as_is(self) -> None:
        repo = make_repository()
        repo.list_by_workspace.return_value = []
        uc = ListDocumentsUseCase(repository=repo)

        result = uc.execute(workspace_id=WS_ID)

        assert result == []
        repo.list_by_workspace.assert_called_once_with(WS_ID)
