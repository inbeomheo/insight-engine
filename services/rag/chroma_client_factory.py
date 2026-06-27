"""ChromaDB PersistentClient를 프로세스 단위로 단일 관리하는 팩토리.

배경:
    `services/rag/vector_store.py`와 `services/media/video_qa_service.py`가
    각각 `chromadb.PersistentClient(path=...)`를 별도로 생성하여
    동일한 디렉토리(`./data/chroma_db`)에 동시 쓰기를 수행해 왔다.
    ChromaDB 내부는 SQLite(WAL)로 동작하므로 다중 인스턴스가 같은 경로를
    잡으면 WAL 락 충돌이나 데이터 손상 위험이 있다.

해결:
    `get_chroma_client(path)`로 진입점을 통일하고, 동일 경로에 대해
    모듈 레벨 싱글톤(threading.Lock으로 보호)으로 단 하나의 클라이언트만 유지.

테스트 환경 호환:
    chromadb 자체는 함수 내부에서 lazy import (선택적 의존성).
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from utils.runtime_paths import app_data_path

_chroma_clients: Dict[str, Any] = {}
_chroma_lock = threading.Lock()


def _resolve_path(path: Optional[str]) -> str:
    """전달받은 경로(또는 환경변수)를 절대경로로 정규화."""
    actual = path or os.getenv("CHROMA_DB_PATH") or app_data_path("chroma_db")
    return os.path.abspath(actual)


def get_chroma_client(path: Optional[str] = None) -> Any:
    """ChromaDB PersistentClient를 프로세스 단위 싱글톤으로 반환.

    services/rag/vector_store.py와 services/media/video_qa_service.py가
    동일 디렉토리에 별개 인스턴스를 생성하던 문제를 해결.
    동일 디렉토리 동시 쓰기 시 SQLite 락 충돌 위험 방지.

    Args:
        path: ChromaDB 영속 디렉토리 경로. 미지정 시 `CHROMA_DB_PATH`
            환경변수 또는 `./data/chroma_db` 기본값 사용.

    Returns:
        chromadb.PersistentClient 인스턴스.

    Raises:
        ImportError: chromadb 패키지가 설치되어 있지 않은 경우.
    """
    resolved = _resolve_path(path)

    client = _chroma_clients.get(resolved)
    if client is not None:
        return client

    with _chroma_lock:
        client = _chroma_clients.get(resolved)
        if client is None:
            import chromadb  # lazy import (선택적 의존성)

            os.makedirs(resolved, exist_ok=True)
            client = chromadb.PersistentClient(path=resolved)
            _chroma_clients[resolved] = client
    return client


def reset_chroma_clients() -> None:
    """테스트용: 캐시된 클라이언트 핸들을 해제.

    프로덕션 코드에서는 호출하지 말 것. ChromaDB가 내부적으로 보유한
    SQLite 핸들은 GC 타이밍에 따라 닫히므로, 동일 경로에 새 인스턴스를
    바로 만들면 충돌할 수 있다.
    """
    with _chroma_lock:
        _chroma_clients.clear()
