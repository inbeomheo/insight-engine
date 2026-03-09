"""
비디오-리걸 서비스.

비디오 콘텐츠(자막/메타데이터)의 법적 리스크를 키워드 매칭으로 평가한다.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LegalRisk:
    """법적 리스크."""
    risk_type: str  # copyright / defamation / privacy / trademark / medical_claim
    severity: str  # low / medium / high
    description: str
    timestamp: str  # 자막 내 발생 위치 (예: "02:30")


@dataclass
class LegalReview:
    """법적 검토 결과."""
    video_id: str
    risks: list  # list[LegalRisk]
    overall_risk: str  # low / medium / high
    clearance_status: str  # cleared / review_needed / blocked


# 리스크 유형별 키워드
_RISK_KEYWORDS = {
    "copyright": {
        "keywords": ["저작권", "원작", "무단 복제", "불법 다운", "크랙", "토렌트"],
        "default_severity": "high",
    },
    "defamation": {
        "keywords": ["명예훼손", "비방", "거짓말", "사기꾼", "협잡"],
        "default_severity": "high",
    },
    "privacy": {
        "keywords": ["개인정보", "주소", "전화번호", "신상", "신용정보"],
        "default_severity": "medium",
    },
    "trademark": {
        "keywords": ["상표", "®", "™", "특허 침해", "짝퉁", "위조"],
        "default_severity": "medium",
    },
    "medical_claim": {
        "keywords": ["치료", "완치", "효과 보장", "부작용 없", "만병통치", "기적의"],
        "default_severity": "high",
    },
}


def scan_for_risks(transcript: str, metadata: dict = None) -> LegalReview:
    """자막과 메타데이터에서 법적 리스크를 스캔한다."""
    metadata = metadata or {}
    video_id = metadata.get("video_id", f"vid_{uuid.uuid4().hex[:8]}")
    title = metadata.get("title", "")

    # 전체 텍스트 (자막 + 제목)
    full_text = f"{title} {transcript}"
    risks = []

    for risk_type, config in _RISK_KEYWORDS.items():
        for keyword in config["keywords"]:
            if keyword in full_text:
                severity = classify_severity(risk_type, keyword)
                risks.append(LegalRisk(
                    risk_type=risk_type,
                    severity=severity,
                    description=f"'{keyword}' 키워드 탐지됨",
                    timestamp=_find_timestamp(transcript, keyword),
                ))

    # 전체 리스크 수준
    overall = _calculate_overall_risk(risks)
    clearance = recommend_clearance(
        LegalReview(video_id=video_id, risks=risks, overall_risk=overall, clearance_status="")
    )

    return LegalReview(
        video_id=video_id,
        risks=risks,
        overall_risk=overall,
        clearance_status=clearance,
    )


def _find_timestamp(transcript: str, keyword: str) -> str:
    """키워드가 자막 내 어디에 있는지 대략적 위치를 반환한다."""
    idx = transcript.find(keyword)
    if idx < 0:
        return "N/A"
    # 전체 길이 대비 비율로 대략적 시간 추정 (10분 기준)
    ratio = idx / max(len(transcript), 1)
    total_seconds = int(ratio * 600)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def classify_severity(risk_type: str, context: str = "") -> str:
    """리스크 유형과 컨텍스트로 심각도를 분류한다."""
    config = _RISK_KEYWORDS.get(risk_type)
    if config:
        return config["default_severity"]
    return "low"


def _calculate_overall_risk(risks: list) -> str:
    """전체 리스크 수준을 결정한다."""
    if not risks:
        return "low"

    severity_order = {"high": 3, "medium": 2, "low": 1}
    max_severity = max(severity_order.get(r.severity, 0) for r in risks)

    # 리스크 개수도 고려
    if max_severity >= 3 or len(risks) >= 5:
        return "high"
    elif max_severity >= 2 or len(risks) >= 3:
        return "medium"
    return "low"


def recommend_clearance(review: LegalReview) -> str:
    """승인 상태를 결정한다."""
    if not review.risks:
        return "cleared"

    high_risks = [r for r in review.risks if r.severity == "high"]
    if high_risks:
        return "blocked"

    medium_risks = [r for r in review.risks if r.severity == "medium"]
    if medium_risks:
        return "review_needed"

    return "cleared"


def generate_legal_summary(review: LegalReview) -> str:
    """법적 요약 보고서를 생성한다."""
    lines = [
        f"=== 법적 검토 보고서 ===",
        f"비디오 ID: {review.video_id}",
        f"전체 리스크: {review.overall_risk}",
        f"승인 상태: {review.clearance_status}",
        f"탐지된 리스크: {len(review.risks)}건",
        "",
    ]

    if review.risks:
        lines.append("--- 상세 리스크 ---")
        for i, risk in enumerate(review.risks, 1):
            lines.append(
                f"  {i}. [{risk.risk_type}] {risk.severity} — {risk.description} (위치: {risk.timestamp})"
            )
    else:
        lines.append("법적 리스크가 탐지되지 않았습니다.")

    return "\n".join(lines)
