"""Knowledge BC 예외 계층."""
from __future__ import annotations


class KnowledgeException(Exception):
    """Knowledge BC 공통 베이스."""


class DocumentNotFound(KnowledgeException):
    """문서 ID로 조회 실패."""

    def __init__(self, document_id, workspace_id=None):
        self.document_id = document_id
        self.workspace_id = workspace_id
        msg = f"KnowledgeDocument 조회 실패: {document_id}"
        if workspace_id is not None:
            msg += f" (workspace={workspace_id})"
        super().__init__(msg)


class EmbeddingFailed(KnowledgeException):
    """임베딩 생성 실패 (모델 호출 오류, 입력 너무 길음 등)."""


class IndexingFailed(KnowledgeException):
    """벡터 인덱싱 실패 (ChromaDB 쓰기 오류 등)."""


class VectorStoreUnavailable(KnowledgeException):
    """벡터 스토어가 사용 불가 (ChromaDB 미설치, 경로 권한 등)."""


class ChunkingFailed(KnowledgeException):
    """청킹 실패 (지원하지 않는 파일 형식 등)."""
