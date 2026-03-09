"""
시즌 예보 서비스

주제(키워드)의 트렌드 시즌 단계를 예측합니다.
rising → peak → declining → reignite 4단계 라이프사이클 모델.
"""
import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 시즌 단계 정의
PHASES = ("rising", "peak", "declining", "reignite")

# 키워드 기반 시즌 힌트 (간단한 규칙 기반)
_SEASONAL_KEYWORDS: dict[str, list[str]] = {
    "rising": [
        "신규", "출시", "런칭", "오픈", "새로운", "떠오르는",
        "launch", "new", "emerging", "trend",
    ],
    "peak": [
        "인기", "화제", "대세", "핫", "폭발", "viral",
        "popular", "hot", "trending", "boom",
    ],
    "declining": [
        "하락", "감소", "줄어드는", "쇠퇴", "끝",
        "decline", "fading", "slowdown", "drop",
    ],
    "reignite": [
        "부활", "복귀", "재등장", "다시", "리메이크",
        "comeback", "revival", "return", "reboot",
    ],
}

# 단계별 기본 추천
_PHASE_RECOMMENDATIONS: dict[str, str] = {
    "rising": "상승 추세입니다. 빠르게 콘텐츠를 발행하여 선점 효과를 노리세요.",
    "peak": "정점 시기입니다. 차별화된 깊이 있는 콘텐츠로 경쟁에서 돋보이세요.",
    "declining": "하락 추세입니다. 관련 신규 앵글을 찾거나 다른 주제로 전환을 고려하세요.",
    "reignite": "재점화 시기입니다. 과거 성공 콘텐츠를 업데이트하여 재활용하세요.",
}


@dataclass
class SeasonForecast:
    """시즌 예보 결과"""
    topic: str
    phase: str         # "rising" | "peak" | "declining" | "reignite"
    confidence: float  # 0.0~1.0
    recommendation: str


def _normalize_topic(topic: str) -> str:
    """주제 문자열 정규화 (소문자, 공백 정리)."""
    return re.sub(r'\s+', ' ', topic.strip().lower())


def _hash_score(topic: str) -> float:
    """주제 해시 기반 결정적 점수 (0.0~1.0).

    키워드 매칭이 없을 때 일관된 기본 단계를 제공하기 위한 폴백.
    """
    h = hashlib.md5(topic.encode('utf-8')).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _keyword_match_scores(topic: str) -> dict[str, float]:
    """주제에서 각 단계별 키워드 매칭 점수 계산."""
    normalized = _normalize_topic(topic)
    scores: dict[str, float] = {}

    for phase, keywords in _SEASONAL_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in normalized)
        total = len(keywords)
        scores[phase] = match_count / total if total > 0 else 0.0

    return scores


def forecast_season(topic: str) -> SeasonForecast:
    """주제의 시즌 단계 예측.

    Args:
        topic: 분석할 주제/키워드

    Returns:
        SeasonForecast: 시즌 단계, 신뢰도, 추천 포함
    """
    if not topic or not topic.strip():
        logger.warning("빈 주제 입력")
        return SeasonForecast(
            topic="",
            phase="rising",
            confidence=0.0,
            recommendation="주제를 입력해주세요.",
        )

    normalized = _normalize_topic(topic)
    scores = _keyword_match_scores(normalized)

    # 최고 점수 단계 선택
    max_score = max(scores.values())

    if max_score > 0:
        # 키워드 매칭이 있으면 해당 단계 사용
        best_phase = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = round(min(max_score * 2, 1.0), 2)  # 매칭 비율을 신뢰도로 변환
    else:
        # 키워드 매칭이 없으면 해시 기반 폴백
        hash_val = _hash_score(normalized)
        phase_index = int(hash_val * len(PHASES)) % len(PHASES)
        best_phase = PHASES[phase_index]
        confidence = 0.3  # 키워드 매칭 없으므로 낮은 신뢰도

    recommendation = _PHASE_RECOMMENDATIONS.get(
        best_phase,
        "데이터를 추가로 수집하여 분석 정확도를 높이세요.",
    )

    return SeasonForecast(
        topic=topic.strip(),
        phase=best_phase,
        confidence=confidence,
        recommendation=recommendation,
    )


def get_phase_label_kr(phase: str) -> str:
    """단계를 한국어 라벨로 변환."""
    labels = {
        "rising": "상승기",
        "peak": "정점기",
        "declining": "하락기",
        "reignite": "재점화기",
    }
    return labels.get(phase, phase)
