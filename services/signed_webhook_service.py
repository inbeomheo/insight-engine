"""
서명형 웹훅 서비스 — HMAC 서명이 포함된 웹훅 페이로드 생성/검증
"""

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WebhookPayload:
    """웹훅 페이로드"""
    payload_id: str
    event_type: str
    data: dict
    timestamp: str  # ISO 8601
    signature: str  # HMAC-SHA256


def _compute_signature(event_type: str, data: dict, timestamp: str, secret: str) -> str:
    """HMAC-SHA256 서명 생성"""
    message = f"{event_type}:{timestamp}:{json.dumps(data, sort_keys=True)}"
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_payload(event_type: str, data: dict, secret: str) -> WebhookPayload:
    """페이로드 + HMAC-SHA256 서명 생성"""
    timestamp = datetime.now().isoformat()
    signature = _compute_signature(event_type, data, timestamp, secret)

    return WebhookPayload(
        payload_id=str(uuid.uuid4()),
        event_type=event_type,
        data=data,
        timestamp=timestamp,
        signature=signature,
    )


def verify_signature(payload: WebhookPayload, secret: str) -> bool:
    """서명 검증"""
    expected = _compute_signature(
        payload.event_type,
        payload.data,
        payload.timestamp,
        secret,
    )
    return hmac.compare_digest(payload.signature, expected)


def format_headers(payload: WebhookPayload) -> dict:
    """HTTP 헤더 생성"""
    return {
        "Content-Type": "application/json",
        "X-Webhook-Id": payload.payload_id,
        "X-Webhook-Event": payload.event_type,
        "X-Webhook-Timestamp": payload.timestamp,
        "X-Webhook-Signature": f"sha256={payload.signature}",
    }


def is_replay_attack(payload: WebhookPayload, max_age_seconds: int, current_time: str) -> bool:
    """리플레이 공격 감지 — 타임스탬프가 허용 범위를 벗어나면 True"""
    try:
        payload_time = datetime.fromisoformat(payload.timestamp)
        current = datetime.fromisoformat(current_time)
        diff = abs((current - payload_time).total_seconds())
        return diff > max_age_seconds
    except (ValueError, TypeError):
        return True  # 파싱 실패 시 공격으로 간주
