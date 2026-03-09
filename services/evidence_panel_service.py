"""
증거 패널 서비스 — 주장에 대한 근거를 패널 형태로 구성
"""

import uuid
from dataclasses import dataclass, field

# 증거 유형별 가중치 (data/expert 높음)
_TYPE_WEIGHTS: dict[str, float] = {
    "data": 1.5,
    "expert": 1.3,
    "testimony": 1.0,
    "example": 0.8,
}

# 지원되는 증거 유형
VALID_EVIDENCE_TYPES = {"data", "testimony", "expert", "example"}


@dataclass
class EvidenceItem:
    """증거 항목"""
    item_id: str
    claim: str
    evidence_text: str
    evidence_type: str  # data / testimony / expert / example
    strength: int  # 1~5
    source: str = ""


@dataclass
class EvidencePanel:
    """증거 패널"""
    panel_id: str
    topic: str
    items: list[EvidenceItem] = field(default_factory=list)
    overall_score: float = 0.0


def create_panel(topic: str) -> EvidencePanel:
    """빈 증거 패널 생성

    Args:
        topic: 패널 주제

    Returns:
        새 증거 패널
    """
    return EvidencePanel(
        panel_id=str(uuid.uuid4()),
        topic=topic,
        items=[],
        overall_score=0.0,
    )


def add_evidence(
    panel: EvidencePanel,
    claim: str,
    text: str,
    evidence_type: str,
    strength: int,
    source: str = "",
) -> EvidencePanel:
    """근거 추가

    Args:
        panel: 대상 패널
        claim: 주장
        text: 근거 텍스트
        evidence_type: 증거 유형 (data/testimony/expert/example)
        strength: 강도 (1~5)
        source: 출처

    Returns:
        업데이트된 패널

    Raises:
        ValueError: 잘못된 증거 유형 또는 강도 범위
    """
    if evidence_type not in VALID_EVIDENCE_TYPES:
        raise ValueError(
            f"잘못된 증거 유형: {evidence_type}. "
            f"허용: {', '.join(sorted(VALID_EVIDENCE_TYPES))}"
        )
    if not (1 <= strength <= 5):
        raise ValueError(f"강도는 1~5 범위여야 합니다: {strength}")

    item = EvidenceItem(
        item_id=str(uuid.uuid4()),
        claim=claim,
        evidence_text=text,
        evidence_type=evidence_type,
        strength=strength,
        source=source,
    )
    panel.items.append(item)
    panel.overall_score = score_panel(panel)
    return panel


def score_panel(panel: EvidencePanel) -> float:
    """패널 종합 점수 계산 (가중 평균)

    data/expert 유형에 높은 가중치 적용.

    Args:
        panel: 대상 패널

    Returns:
        종합 점수 (0.0 ~ 5.0)
    """
    if not panel.items:
        return 0.0

    total_weighted = 0.0
    total_weight = 0.0

    for item in panel.items:
        type_weight = _TYPE_WEIGHTS.get(item.evidence_type, 1.0)
        total_weighted += item.strength * type_weight
        total_weight += type_weight

    return round(total_weighted / total_weight, 2) if total_weight > 0 else 0.0


def identify_gaps(panel: EvidencePanel) -> list[str]:
    """증거 유형 공백 식별

    Args:
        panel: 대상 패널

    Returns:
        커버되지 않은 증거 유형 목록
    """
    covered = {item.evidence_type for item in panel.items}
    gaps = sorted(VALID_EVIDENCE_TYPES - covered)
    return gaps


def rank_by_strength(panel: EvidencePanel) -> list[EvidenceItem]:
    """강도순 정렬 (내림차순)

    Args:
        panel: 대상 패널

    Returns:
        강도 순으로 정렬된 증거 목록
    """
    return sorted(panel.items, key=lambda x: x.strength, reverse=True)
