"""
클레임 매핑 서비스 — 보험/법적 클레임 분석
"""

import uuid
from dataclasses import dataclass, field


VALID_CLAIM_TYPES = ('property', 'liability', 'medical', 'business')
VALID_STATUSES = ('filed', 'reviewing', 'approved', 'denied')


@dataclass
class Claim:
    """클레임"""
    claim_id: str
    claimant: str
    claim_type: str  # property / liability / medical / business
    amount: float
    status: str  # filed / reviewing / approved / denied
    evidence: list[str]


def create_claim(claimant: str, claim_type: str, amount: float,
                 evidence: list[str]) -> Claim:
    """클레임 생성"""
    if claim_type not in VALID_CLAIM_TYPES:
        raise ValueError(f"유효하지 않은 클레임 유형: {claim_type}")
    return Claim(
        claim_id=str(uuid.uuid4())[:8],
        claimant=claimant,
        claim_type=claim_type,
        amount=amount,
        status='filed',
        evidence=evidence
    )


def assess_claim(claim: Claim) -> dict:
    """클레임 평가 — 증거 수, 금액 기준"""
    evidence_score = min(len(claim.evidence) / 3.0, 1.0)
    amount_risk = 'high' if claim.amount > 100000 else ('medium' if claim.amount > 10000 else 'low')

    recommendation = 'approve' if evidence_score >= 0.7 else ('review' if evidence_score >= 0.3 else 'deny')

    return {
        'claim_id': claim.claim_id,
        'evidence_score': round(evidence_score, 2),
        'amount_risk': amount_risk,
        'recommendation': recommendation
    }


def update_status(claim: Claim, new_status: str) -> Claim:
    """클레임 상태 업데이트"""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"유효하지 않은 상태: {new_status}")
    return Claim(
        claim_id=claim.claim_id,
        claimant=claim.claimant,
        claim_type=claim.claim_type,
        amount=claim.amount,
        status=new_status,
        evidence=claim.evidence
    )


def calculate_total_exposure(claims: list[Claim]) -> float:
    """총 위험 노출액 — filed 또는 reviewing 상태인 클레임 합산"""
    return sum(c.amount for c in claims if c.status in ('filed', 'reviewing'))


def group_by_type(claims: list[Claim]) -> dict:
    """유형별 그룹핑"""
    groups: dict[str, list[Claim]] = {}
    for c in claims:
        groups.setdefault(c.claim_type, []).append(c)
    return groups
