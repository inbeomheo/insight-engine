"""
Breaking Fitness 서비스

콘텐츠가 브레이킹 뉴스/트렌드 토픽에 얼마나 적합한지 평가합니다.
키워드 매칭, 의미적 관련도, 시의성을 분석하여 적합성 점수를 산출합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class FitnessScore:
    """브레이킹 토픽 적합성 평가 결과"""
    topic: str
    fitness_score: float
    relevance_factors: List[str] = field(default_factory=list)
    recommended_action: str = ""
    urgency: str = "not_urgent"


# ── 시의성 키워드 (한국어/영어) ──
_URGENCY_KEYWORDS_IMMEDIATE = [
    "속보", "긴급", "breaking", "urgent", "just in",
    "방금", "실시간", "live", "지금 막",
]
_URGENCY_KEYWORDS_HOURS = [
    "오늘", "today", "최신", "latest", "new release",
    "발표", "공개", "출시", "announced",
]
_URGENCY_KEYWORDS_NEXT_DAY = [
    "이번 주", "this week", "최근", "recently", "업데이트",
    "update", "변경", "changed",
]

# ── 관련도 신호 패턴 ──
_DIRECT_MENTION_WEIGHT = 3.0
_KEYWORD_OVERLAP_WEIGHT = 2.0
_CONTEXT_SIGNAL_WEIGHT = 1.0

_CONTEXT_SIGNALS = [
    (re.compile(r"(?:영향|impact|affect|변화|change)", re.IGNORECASE), "영향/변화 언급"),
    (re.compile(r"(?:전문가|expert|분석가|analyst)", re.IGNORECASE), "전문가 의견 포함"),
    (re.compile(r"(?:데이터|data|통계|statistics|수치)", re.IGNORECASE), "데이터/통계 근거"),
    (re.compile(r"(?:비교|compare|대비|versus|vs)", re.IGNORECASE), "비교 분석"),
    (re.compile(r"(?:전망|outlook|예측|forecast|predict)", re.IGNORECASE), "전망/예측 포함"),
    (re.compile(r"(?:원인|cause|이유|reason|배경|background)", re.IGNORECASE), "원인/배경 설명"),
]


def _normalize(text: str) -> str:
    """텍스트를 정규화합니다 (소문자, 불필요한 공백 제거)."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_topic_keywords(topic: str) -> List[str]:
    """토픽 문자열에서 의미 있는 키워드를 추출합니다."""
    normalized = _normalize(topic)
    # 2글자 이상인 단어만 추출
    words = re.findall(r"[a-z가-힣]{2,}", normalized)
    return list(dict.fromkeys(words))  # 순서 유지 중복 제거


def _detect_urgency(content: str) -> str:
    """콘텐츠의 시의성 수준을 판별합니다."""
    lower = content.lower()
    for kw in _URGENCY_KEYWORDS_IMMEDIATE:
        if kw in lower:
            return "immediate"
    for kw in _URGENCY_KEYWORDS_HOURS:
        if kw in lower:
            return "within_hours"
    for kw in _URGENCY_KEYWORDS_NEXT_DAY:
        if kw in lower:
            return "next_day"
    return "not_urgent"


def _calculate_relevance(content: str, topic: str) -> tuple:
    """콘텐츠와 토픽 간 관련도를 계산합니다.

    Returns:
        (score: float, factors: list[str])
    """
    content_lower = _normalize(content)
    topic_lower = _normalize(topic)
    factors: List[str] = []
    score = 0.0

    # 1) 토픽 직접 언급 횟수
    direct_count = content_lower.count(topic_lower)
    if direct_count > 0:
        score += min(direct_count * _DIRECT_MENTION_WEIGHT, 15.0)
        factors.append(f"토픽 직접 언급 {direct_count}회")

    # 2) 키워드 오버랩
    keywords = _extract_topic_keywords(topic)
    if keywords:
        matched = [kw for kw in keywords if kw in content_lower]
        overlap_ratio = len(matched) / len(keywords) if keywords else 0
        score += overlap_ratio * _KEYWORD_OVERLAP_WEIGHT * 10
        if matched:
            factors.append(f"키워드 매칭: {', '.join(matched[:5])}")

    # 3) 컨텍스트 신호
    for pattern, label in _CONTEXT_SIGNALS:
        if pattern.search(content):
            score += _CONTEXT_SIGNAL_WEIGHT
            factors.append(label)

    return score, factors


def _determine_action(fitness: float, urgency: str) -> str:
    """적합성 점수와 시의성에 따른 권장 행동을 결정합니다."""
    if fitness >= 80:
        if urgency == "immediate":
            return "즉시 발행 — 브레이킹 토픽에 최적 콘텐츠"
        return "우선 발행 권장 — 높은 적합성"
    if fitness >= 50:
        return "토픽 키워드 보강 후 발행 권장"
    if fitness >= 25:
        return "토픽 연관성 부족 — 관련 내용 추가 필요"
    return "토픽과 관련 없음 — 다른 콘텐츠 사용 권장"


def score_breaking_fitness(content: str, breaking_topic: str) -> FitnessScore:
    """콘텐츠의 브레이킹 토픽 적합성을 평가합니다.

    Args:
        content: 평가할 콘텐츠 텍스트
        breaking_topic: 브레이킹 뉴스/트렌드 토픽

    Returns:
        FitnessScore 평가 결과 (0~100점)
    """
    if not content or not content.strip() or not breaking_topic or not breaking_topic.strip():
        return FitnessScore(
            topic=breaking_topic or "",
            fitness_score=0.0,
            relevance_factors=[],
            recommended_action="입력 데이터 부족",
            urgency="not_urgent",
        )

    # 관련도 계산
    raw_score, factors = _calculate_relevance(content, breaking_topic)

    # 시의성 판별
    urgency = _detect_urgency(content)

    # 시의성 보너스
    urgency_bonus = {
        "immediate": 10.0,
        "within_hours": 5.0,
        "next_day": 2.0,
        "not_urgent": 0.0,
    }
    raw_score += urgency_bonus[urgency]

    # 0~100 범위로 정규화
    fitness = round(min(100.0, max(0.0, raw_score * 2.5)), 1)

    action = _determine_action(fitness, urgency)

    return FitnessScore(
        topic=breaking_topic,
        fitness_score=fitness,
        relevance_factors=factors,
        recommended_action=action,
        urgency=urgency,
    )
