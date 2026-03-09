"""
클라이언트 포털 서비스 — 클라이언트별 콘텐츠 공유 공간
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

VALID_ACCESS_LEVELS = ("viewer", "reviewer", "editor")


@dataclass
class PortalClient:
    """포털 클라이언트"""
    client_id: str
    name: str
    email: str
    access_level: str  # viewer / reviewer / editor
    created_at: str


@dataclass
class Portal:
    """클라이언트 포털"""
    portal_id: str
    client: PortalClient
    shared_content: list  # [{"content_id": str, "title": str, "shared_at": str}]
    messages: list  # [{"sender": str, "message": str, "sent_at": str}]


def create_portal(client_name: str, email: str, access_level: str = "viewer") -> Portal:
    """클라이언트 포털 생성"""
    if access_level not in VALID_ACCESS_LEVELS:
        raise ValueError(f"유효하지 않은 접근 레벨: {access_level}. 허용: {VALID_ACCESS_LEVELS}")
    if not client_name.strip():
        raise ValueError("클라이언트 이름은 필수입니다")
    if not email.strip():
        raise ValueError("이메일은 필수입니다")

    now = datetime.now().isoformat()
    client = PortalClient(
        client_id=str(uuid.uuid4()),
        name=client_name.strip(),
        email=email.strip(),
        access_level=access_level,
        created_at=now,
    )

    return Portal(
        portal_id=str(uuid.uuid4()),
        client=client,
        shared_content=[],
        messages=[],
    )


def share_content(portal: Portal, content_id: str, title: str) -> Portal:
    """콘텐츠 공유"""
    # 중복 공유 방지
    existing_ids = {c["content_id"] for c in portal.shared_content}
    if content_id in existing_ids:
        return portal

    portal.shared_content.append({
        "content_id": content_id,
        "title": title,
        "shared_at": datetime.now().isoformat(),
    })
    return portal


def add_message(portal: Portal, sender: str, message: str) -> Portal:
    """메시지 추가"""
    portal.messages.append({
        "sender": sender,
        "message": message,
        "sent_at": datetime.now().isoformat(),
    })
    return portal


def get_activity_log(portal: Portal) -> list:
    """활동 로그 (공유/메시지 통합, 시간순)"""
    log = []

    for content in portal.shared_content:
        log.append({
            "type": "share",
            "description": f"콘텐츠 공유: {content['title']}",
            "timestamp": content["shared_at"],
        })

    for msg in portal.messages:
        log.append({
            "type": "message",
            "description": f"{msg['sender']}: {msg['message'][:50]}",
            "timestamp": msg["sent_at"],
        })

    log.sort(key=lambda x: x["timestamp"])
    return log
