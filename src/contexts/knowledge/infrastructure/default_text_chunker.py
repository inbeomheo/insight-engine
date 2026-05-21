"""DefaultTextChunker — `ITextChunker` 어댑터.

`services/rag/chunker.py`의 `chunk_text(text, chunk_size, overlap)` 함수를 lazy import wrap.
chromadb 등 무거운 의존성 없이 동작 가능 (chunker는 순수 함수).
"""
from __future__ import annotations

from src.contexts.knowledge.application.ports import ITextChunker
from src.contexts.knowledge.domain.exceptions import ChunkingFailed


class DefaultTextChunker(ITextChunker):
    """기본 텍스트 청커.

    services/rag/chunker.chunk_text의 슬라이딩 윈도우 청킹을 래핑.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100):
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError(
                f"chunk_size는 양의 정수여야 함: {chunk_size!r}"
            )
        if not isinstance(overlap, int) or overlap < 0:
            raise ValueError(
                f"overlap은 0 이상의 정수여야 함: {overlap!r}"
            )
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap({overlap})은 chunk_size({chunk_size})보다 작아야 함"
            )
        self._chunk_size = chunk_size
        self._overlap = overlap

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @property
    def overlap(self) -> int:
        return self._overlap

    def chunk(self, text: str) -> list[str]:
        """텍스트를 청크 본문 리스트로 분할. 빈 텍스트면 빈 리스트."""
        if not isinstance(text, str) or not text.strip():
            return []

        chunk_text = _load_chunk_text()
        try:
            return chunk_text(text, chunk_size=self._chunk_size, overlap=self._overlap)
        except Exception as e:
            raise ChunkingFailed(
                f"청킹 실패: {type(e).__name__}: {e}"
            ) from e


# ---------- 모듈 로더 ----------
# `services/rag/__init__.py`가 vector_store(chromadb 필요)를 즉시 import 하므로
# `from services.rag.chunker import chunk_text`는 chromadb 미설치 환경에서 실패한다.
# chunker.py는 순수 함수만 가지므로 패키지 __init__을 우회해 파일 경로로 직접 로드.
_chunk_text_cache = None


def _load_chunk_text():
    """services/rag/chunker.py의 chunk_text 함수를 패키지 __init__ 우회 로드."""
    global _chunk_text_cache
    if _chunk_text_cache is not None:
        return _chunk_text_cache

    import importlib.util
    import os
    import sys

    # 1차 시도: services.rag.chunker 직접 모듈 import (sys.modules에 이미 있으면 재사용)
    mod = sys.modules.get("services.rag.chunker")
    if mod is not None and hasattr(mod, "chunk_text"):
        _chunk_text_cache = mod.chunk_text
        return _chunk_text_cache

    # 2차 시도: 파일 경로로 직접 로드 (패키지 __init__.py 우회)
    here = os.path.dirname(os.path.abspath(__file__))
    # src/contexts/knowledge/infrastructure → 4단계 위가 프로젝트 루트
    project_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    chunker_path = os.path.join(project_root, "services", "rag", "chunker.py")

    if not os.path.isfile(chunker_path):
        raise ChunkingFailed(
            f"services/rag/chunker.py를 찾을 수 없음: {chunker_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "_knowledge_chunker_isolated", chunker_path
    )
    if spec is None or spec.loader is None:
        raise ChunkingFailed("chunker.py spec 생성 실패")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ChunkingFailed(
            f"chunker.py 로드 실패: {type(e).__name__}: {e}"
        ) from e

    fn = getattr(module, "chunk_text", None)
    if fn is None:
        raise ChunkingFailed("chunker.py에 chunk_text 함수 없음")
    _chunk_text_cache = fn
    return _chunk_text_cache
