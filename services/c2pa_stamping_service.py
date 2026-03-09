"""
C2PA 스탬핑 서비스 — 콘텐츠 출처 증명 메타데이터 생성
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class C2PAManifest:
    """C2PA 매니페스트"""
    manifest_id: str
    content_hash: str  # SHA-256 해시
    creator: str
    created_at: str  # ISO 8601
    tool: str
    actions: list  # ["created", "edited", "cropped", ...]
    parent_hash: str  # None이면 원본


def _compute_hash(content: str) -> str:
    """SHA-256 해시 계산"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_manifest(content: str, creator: str, tool: str) -> C2PAManifest:
    """매니페스트 생성"""
    return C2PAManifest(
        manifest_id=str(uuid.uuid4()),
        content_hash=_compute_hash(content),
        creator=creator,
        created_at=datetime.now().isoformat(),
        tool=tool,
        actions=["created"],
        parent_hash="",
    )


def add_action(manifest: C2PAManifest, action: str) -> C2PAManifest:
    """편집 행위 추가"""
    if action not in manifest.actions:
        manifest.actions.append(action)
    return manifest


def verify_manifest(manifest: C2PAManifest, content: str) -> bool:
    """무결성 검증 — 콘텐츠 해시가 매니페스트와 일치하는지"""
    return _compute_hash(content) == manifest.content_hash


def chain_manifests(parent: C2PAManifest, child_content: str, creator: str = "", tool: str = "") -> C2PAManifest:
    """부모-자식 매니페스트 체인"""
    child = C2PAManifest(
        manifest_id=str(uuid.uuid4()),
        content_hash=_compute_hash(child_content),
        creator=creator or parent.creator,
        created_at=datetime.now().isoformat(),
        tool=tool or parent.tool,
        actions=["derived"],
        parent_hash=parent.content_hash,
    )
    return child


def export_manifest(manifest: C2PAManifest) -> dict:
    """JSON 내보내기"""
    return {
        "manifest_id": manifest.manifest_id,
        "content_hash": manifest.content_hash,
        "creator": manifest.creator,
        "created_at": manifest.created_at,
        "tool": manifest.tool,
        "actions": list(manifest.actions),
        "parent_hash": manifest.parent_hash,
    }
