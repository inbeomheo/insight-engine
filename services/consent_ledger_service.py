"""
동의 원장 서비스.

사용자 동의 이력을 불변 원장으로 관리한다.
IP는 SHA256으로 해시하여 저장, 시간 순서 무결성을 검증.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ConsentRecord:
    """동의 기록."""
    record_id: str
    user_id: str
    consent_type: str  # data_collection / marketing / analytics / third_party
    granted: bool
    timestamp: str
    ip_hash: str
    version: str


@dataclass
class ConsentLedger:
    """동의 원장."""
    ledger_id: str
    records: list  # list[ConsentRecord]


# 유효한 동의 유형
VALID_CONSENT_TYPES = {"data_collection", "marketing", "analytics", "third_party"}


def _hash_ip(ip: str) -> str:
    """IP 주소를 SHA256 해시한다."""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    """현재 UTC 시간을 ISO 형식으로 반환한다."""
    return datetime.now(timezone.utc).isoformat()


def record_consent(
    ledger: ConsentLedger,
    user_id: str,
    consent_type: str,
    granted: bool,
    ip: str,
    version: str = "1.0",
) -> ConsentLedger:
    """동의를 기록하고 업데이트된 원장을 반환한다."""
    record = ConsentRecord(
        record_id=f"cr_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        consent_type=consent_type,
        granted=granted,
        timestamp=_now_iso(),
        ip_hash=_hash_ip(ip),
        version=version,
    )
    new_records = list(ledger.records) + [record]
    return ConsentLedger(ledger_id=ledger.ledger_id, records=new_records)


def get_current_consents(ledger: ConsentLedger, user_id: str) -> dict:
    """사용자의 최신 동의 상태를 반환한다.

    Returns:
        {consent_type: bool} 형태의 딕셔너리
    """
    # 시간순 정렬 — 나중 기록이 이전 기록을 덮어씀
    user_records = [r for r in ledger.records if r.user_id == user_id]
    user_records.sort(key=lambda r: r.timestamp)

    consents = {}
    for record in user_records:
        consents[record.consent_type] = record.granted
    return consents


def check_consent(
    ledger: ConsentLedger,
    user_id: str,
    consent_type: str,
) -> bool:
    """특정 동의 유형의 현재 상태를 확인한다."""
    current = get_current_consents(ledger, user_id)
    return current.get(consent_type, False)


def get_audit_trail(
    ledger: ConsentLedger,
    user_id: str,
) -> list:
    """사용자의 전체 동의 감사 추적을 반환한다."""
    return [r for r in ledger.records if r.user_id == user_id]


def verify_integrity(ledger: ConsentLedger) -> bool:
    """원장 무결성을 검증한다 (시간 순서 체크).

    레코드가 시간 순서대로 정렬되어 있는지 확인.
    """
    if len(ledger.records) <= 1:
        return True

    for i in range(1, len(ledger.records)):
        prev_ts = ledger.records[i - 1].timestamp
        curr_ts = ledger.records[i].timestamp
        if curr_ts < prev_ts:
            return False
    return True
