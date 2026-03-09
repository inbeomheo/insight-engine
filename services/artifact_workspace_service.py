"""
산출물 워크스페이스 서비스 — 세션별 산출물 독립 관리
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Artifact:
    """산출물 항목"""
    artifact_id: str
    artifact_type: str  # "text", "html", "json", "markdown", "image_ref"
    content: str
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class Workspace:
    """산출물 워크스페이스"""
    workspace_id: str
    session_id: str
    name: str
    artifacts: list[Artifact] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


# 허용 산출물 타입
VALID_ARTIFACT_TYPES = {"text", "html", "json", "markdown", "image_ref"}


class ArtifactWorkspaceService:
    """인메모리 산출물 워크스페이스 관리"""

    def __init__(self):
        # workspace_id -> Workspace
        self._workspace_store: dict[str, Workspace] = {}

    def create_workspace(
        self,
        session_id: str,
        name: str = "",
    ) -> Workspace:
        """산출물 독립 워크스페이스 생성"""
        if not session_id or not session_id.strip():
            raise ValueError("session_id는 필수입니다")

        workspace = Workspace(
            workspace_id=f"ws_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            name=name or f"Workspace-{len(self._workspace_store) + 1}",
        )
        self._workspace_store[workspace.workspace_id] = workspace
        return workspace

    def add_artifact(
        self,
        workspace_id: str,
        artifact_type: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        """워크스페이스에 산출물 추가"""
        if workspace_id not in self._workspace_store:
            raise KeyError(f"워크스페이스를 찾을 수 없습니다: {workspace_id}")

        if artifact_type not in VALID_ARTIFACT_TYPES:
            raise ValueError(
                f"잘못된 산출물 타입: {artifact_type} "
                f"(허용: {', '.join(sorted(VALID_ARTIFACT_TYPES))})"
            )

        artifact = Artifact(
            artifact_id=f"art_{uuid.uuid4().hex[:12]}",
            artifact_type=artifact_type,
            content=content,
            metadata=metadata or {},
        )
        self._workspace_store[workspace_id].artifacts.append(artifact)
        return artifact

    def get_workspace(self, workspace_id: str) -> Workspace:
        """워크스페이스 조회"""
        if workspace_id not in self._workspace_store:
            raise KeyError(f"워크스페이스를 찾을 수 없습니다: {workspace_id}")
        return self._workspace_store[workspace_id]

    def list_workspaces(
        self, session_id: Optional[str] = None
    ) -> list[Workspace]:
        """워크스페이스 목록 조회"""
        workspaces = list(self._workspace_store.values())
        if session_id is not None:
            workspaces = [
                w for w in workspaces if w.session_id == session_id
            ]
        # 생성 시간 오름차순
        workspaces.sort(key=lambda w: w.created_at)
        return workspaces
