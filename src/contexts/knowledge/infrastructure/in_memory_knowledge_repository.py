"""InMemoryKnowledgeRepository — `IKnowledgeRepository` 인메모리 구현.

스레드 안전 (`threading.Lock`).
저장 구조: `dict[workspace_id, dict[doc_id, KnowledgeDocument]]`.
삭제 시 빈 워크스페이스 dict는 즉시 정리해 메모리 누수 방지.

분산/영속 저장이 필요하면 Supabase/DB 어댑터를 추가로 구현한다.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from src.contexts.knowledge.application.ports import IKnowledgeRepository
from src.contexts.knowledge.domain.knowledge_document import KnowledgeDocument
from src.contexts.knowledge.domain.value_objects import DocumentId, WorkspaceId

logger = logging.getLogger(__name__)


class InMemoryKnowledgeRepository(IKnowledgeRepository):
    """프로세스 인메모리 KnowledgeDocument 저장소.

    멀티프로세스 환경에서는 각 워커가 독립된 저장소를 갖는다.
    """

    def __init__(self) -> None:
        # workspace_id.value → { document_id.value → KnowledgeDocument }
        self._store: dict[str, dict[str, KnowledgeDocument]] = {}
        self._lock = threading.Lock()

    def find_by_id(
        self,
        workspace_id: WorkspaceId,
        document_id: DocumentId,
    ) -> Optional[KnowledgeDocument]:
        with self._lock:
            ws = self._store.get(workspace_id.value)
            if not ws:
                return None
            return ws.get(document_id.value)

    def list_by_workspace(self, workspace_id: WorkspaceId) -> list[KnowledgeDocument]:
        with self._lock:
            ws = self._store.get(workspace_id.value)
            if not ws:
                return []
            # dict 순회 중 변경 방지를 위해 값들의 list 복사본 반환
            return list(ws.values())

    def save(self, document: KnowledgeDocument) -> None:
        ws_key = document.workspace_id.value
        doc_key = document.document_id.value
        with self._lock:
            ws = self._store.get(ws_key)
            if ws is None:
                ws = {}
                self._store[ws_key] = ws
            ws[doc_key] = document
        logger.debug("KnowledgeDocument saved: workspace=%s, doc=%s", ws_key, doc_key)

    def delete(self, workspace_id: WorkspaceId, document_id: DocumentId) -> None:
        ws_key = workspace_id.value
        doc_key = document_id.value
        with self._lock:
            ws = self._store.get(ws_key)
            if not ws:
                return
            ws.pop(doc_key, None)
            # 빈 워크스페이스 dict 정리
            if not ws:
                del self._store[ws_key]
        logger.debug("KnowledgeDocument deleted: workspace=%s, doc=%s", ws_key, doc_key)

    # ---------- 테스트/디버그용 (인터페이스 외) ----------
    def clear(self) -> None:
        """저장소 전체 초기화. 테스트/디버그용."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """현재 저장된 전체 문서 수. 테스트/디버그용."""
        with self._lock:
            return sum(len(ws) for ws in self._store.values())
