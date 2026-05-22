"""Knowledge BC 값 객체.

- `DocumentId`: 문서 식별자 (UUID 또는 외부 시스템 ID, 비어있을 수 없음)
- `ChunkId`: 청크 식별자 (보통 `{doc_id}_chunk_{idx}` 패턴)
- `WorkspaceId`: 문서가 속한 워크스페이스 (Identity BC 연동, 단방향 값 객체)
- `Embedding`: 벡터 임베딩 (float tuple). 차원 일관성은 도메인 외부에서 보장.
- `SourceType`: 문서 출처 enum (PDF / MARKDOWN / TEXT / WEB / NOTE)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DocumentId:
    """지식 문서 식별자."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(f"document_id는 비어있지 않은 문자열이어야 함: {self.value!r}")


@dataclass(frozen=True, slots=True)
class ChunkId:
    """청크 식별자."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(f"chunk_id는 비어있지 않은 문자열이어야 함: {self.value!r}")


@dataclass(frozen=True, slots=True)
class WorkspaceId:
    """워크스페이스 식별자 (Identity BC와 단방향 연동).

    user_id를 그대로 워크스페이스 ID로 쓰는 기존 코드 호환을 위해
    str 형태만 보장하고 형식 강제는 하지 않는다.
    """
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError(f"workspace_id는 비어있지 않은 문자열이어야 함: {self.value!r}")


class SourceType(Enum):
    """문서 출처.

    파일 업로드/메모/웹 등 콘텐츠 유형을 구분. 청킹/임베딩 전략에는 영향을 주지 않으며,
    검색 시 출처 표시(필터링 포함)에 사용된다.
    """
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    WEB = "web"
    NOTE = "note"

    @classmethod
    def from_filename(cls, filename: str) -> "SourceType":
        """파일명 확장자로 SourceType 추정.

        지원: .pdf → PDF / .md → MARKDOWN / .txt → TEXT.
        그 외에는 TEXT (가장 일반적인 폴백)로 매핑.
        """
        if not filename:
            return cls.TEXT
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return cls.PDF
        if lower.endswith(".md") or lower.endswith(".markdown"):
            return cls.MARKDOWN
        return cls.TEXT


@dataclass(frozen=True, slots=True)
class Embedding:
    """벡터 임베딩.

    ChromaDB 기본 임베더가 768~1024 차원을 반환하지만, 도메인 레벨에서 차원을 강제하지 않는다.
    동일 컬렉션 내에서는 일관된 차원이어야 한다는 제약은 인프라(`IVectorStore`)에서 보장.
    """
    values: tuple[float, ...]

    def __post_init__(self):
        if not isinstance(self.values, tuple):
            object.__setattr__(self, "values", tuple(self.values))
        if not self.values:
            raise ValueError("embedding values는 비어있을 수 없음")
        # 모든 원소가 수치형인지 가벼운 검증
        for v in self.values:
            if not isinstance(v, (int, float)):
                raise ValueError(f"embedding values는 수치형만 허용: {v!r}")

    @property
    def dimension(self) -> int:
        return len(self.values)

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> "Embedding":
        return cls(tuple(float(v) for v in values))
