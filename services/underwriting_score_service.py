"""
언더라이팅 점수 서비스.

콘텐츠 리스크를 법적/브랜드/사실/기술 4개 팩터로 다차원 평가한다.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskFactor:
    """리스크 팩터."""
    factor_name: str
    score: float  # 0~100
    weight: float
    description: str


@dataclass
class UnderwritingResult:
    """언더라이팅 평가 결과."""
    content_id: str
    factors: list  # list[RiskFactor]
    total_score: float
    risk_level: str  # low / medium / high / critical
    recommendations: list  # list[str]


# 리스크 키워드 맵
_LEGAL_KEYWORDS = ["보증", "확실", "100%", "무조건", "절대", "반드시", "소송", "법적"]
_BRAND_KEYWORDS = ["경쟁사", "비방", "최고", "유일", "독보적"]
_FACTUAL_KEYWORDS = ["연구에 따르면", "통계", "수치", "데이터"]
_TECHNICAL_KEYWORDS = ["취약점", "해킹", "비밀번호", "개인정보"]


def _score_by_keywords(text: str, keywords: list, base_score: float = 20.0) -> float:
    """키워드 빈도 기반 리스크 점수 산출."""
    text_lower = text.lower()
    hit_count = sum(1 for kw in keywords if kw in text_lower)
    # 키워드당 15점, 최대 100
    return min(base_score + hit_count * 15.0, 100.0)


def assess_risk(content: dict, content_type: str = "general") -> UnderwritingResult:
    """콘텐츠 리스크를 4개 팩터로 평가한다."""
    content_id = content.get("id", "unknown")
    text = content.get("text", "")

    # 4개 리스크 팩터 평가
    legal = RiskFactor(
        factor_name="legal",
        score=_score_by_keywords(text, _LEGAL_KEYWORDS, 10.0),
        weight=0.35,
        description="법적 리스크 — 보증/단정적 표현",
    )
    brand = RiskFactor(
        factor_name="brand",
        score=_score_by_keywords(text, _BRAND_KEYWORDS, 10.0),
        weight=0.25,
        description="브랜드 리스크 — 경쟁사 비방/과장",
    )
    factual = RiskFactor(
        factor_name="factual",
        score=_score_by_keywords(text, _FACTUAL_KEYWORDS, 5.0),
        weight=0.20,
        description="사실 리스크 — 미검증 통계/주장",
    )
    technical = RiskFactor(
        factor_name="technical",
        score=_score_by_keywords(text, _TECHNICAL_KEYWORDS, 5.0),
        weight=0.20,
        description="기술 리스크 — 보안/개인정보 관련",
    )

    factors = [legal, brand, factual, technical]
    total = calculate_total_score(factors)
    level = classify_risk_level(total)

    result = UnderwritingResult(
        content_id=content_id,
        factors=factors,
        total_score=total,
        risk_level=level,
        recommendations=[],
    )
    result.recommendations = generate_recommendations(result)
    return result


def calculate_total_score(factors: list) -> float:
    """가중 평균 점수를 계산한다."""
    if not factors:
        return 0.0
    total_weight = sum(f.weight for f in factors)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(f.score * f.weight for f in factors)
    return round(weighted_sum / total_weight, 2)


def classify_risk_level(score: float) -> str:
    """점수를 리스크 등급으로 분류한다."""
    if score <= 30:
        return "low"
    elif score <= 60:
        return "medium"
    elif score <= 80:
        return "high"
    else:
        return "critical"


def generate_recommendations(result: UnderwritingResult) -> list:
    """리스크별 개선 권고를 생성한다."""
    recs = []
    for factor in result.factors:
        if factor.score > 60:
            recs.append(f"[{factor.factor_name}] 높은 리스크 — {factor.description} 검토 필요")
        elif factor.score > 30:
            recs.append(f"[{factor.factor_name}] 주의 — {factor.description} 확인 권장")

    if result.risk_level == "critical":
        recs.insert(0, "전체 리스크 수준 CRITICAL — 발행 전 법무/컴플라이언스 승인 필수")
    elif result.risk_level == "high":
        recs.insert(0, "전체 리스크 수준 HIGH — 발행 전 검토 권장")

    return recs
