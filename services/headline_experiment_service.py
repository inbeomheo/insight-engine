"""
헤드라인 A/B 실험 서비스

여러 헤드라인 후보에 대해 규칙 기반 점수를 계산하고
최적의 헤드라인을 선정합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 점수 가중치
_WEIGHTS = {
    "length": 0.20,       # 적정 길이 (15~40자)
    "number": 0.15,       # 숫자 포함 여부
    "question": 0.10,     # 질문형 여부
    "power_word": 0.20,   # 파워 워드 포함
    "clarity": 0.20,      # 명확성 (특수문자 과다 감점)
    "uniqueness": 0.15,   # 다른 후보 대비 고유성
}

# 클릭률을 높이는 파워 워드
_POWER_WORDS_KR = {
    "방법", "비결", "핵심", "필수", "완벽", "실전",
    "무료", "즉시", "간단", "쉬운", "빠른", "효과",
    "비밀", "공개", "추천", "정리", "가이드", "팁",
}
_POWER_WORDS_EN = {
    "how", "why", "best", "top", "guide", "tips",
    "free", "easy", "simple", "fast", "secret", "proven",
    "ultimate", "essential", "complete", "step",
}
_POWER_WORDS = _POWER_WORDS_KR | _POWER_WORDS_EN


@dataclass
class WinnerHeadline:
    """A/B 실험 결과"""
    headline: str
    score: float
    reasons: List[str]
    all_scores: List[dict] = field(default_factory=list)


def _score_length(headline: str) -> float:
    """길이 점수: 15~40자가 최적."""
    length = len(headline)
    if 15 <= length <= 40:
        return 1.0
    elif 10 <= length < 15 or 40 < length <= 60:
        return 0.6
    elif length < 5:
        return 0.1
    else:
        return 0.3


def _score_number(headline: str) -> float:
    """숫자 포함 점수."""
    return 1.0 if re.search(r'\d+', headline) else 0.0


def _score_question(headline: str) -> float:
    """질문형 점수."""
    return 1.0 if headline.strip().endswith("?") else 0.0


def _score_power_word(headline: str) -> float:
    """파워 워드 포함 점수."""
    lower = headline.lower()
    matches = sum(1 for w in _POWER_WORDS if w in lower)
    if matches >= 3:
        return 1.0
    elif matches >= 2:
        return 0.8
    elif matches >= 1:
        return 0.5
    return 0.0


def _score_clarity(headline: str) -> float:
    """명확성 점수: 특수문자 과다, 대문자 남발 감점."""
    special_count = len(re.findall(r'[!@#$%^&*(){}|<>~`]', headline))
    if special_count == 0:
        return 1.0
    elif special_count <= 2:
        return 0.7
    else:
        return 0.3


def _score_uniqueness(headline: str, others: list[str]) -> float:
    """다른 후보 대비 고유성 점수."""
    if not others:
        return 1.0

    headline_words = set(headline.lower().split())
    if not headline_words:
        return 0.5

    overlaps = []
    for other in others:
        other_words = set(other.lower().split())
        if headline_words and other_words:
            overlap = len(headline_words & other_words) / len(headline_words)
            overlaps.append(overlap)

    avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
    return round(1.0 - avg_overlap, 2)


def _evaluate_headline(
    headline: str,
    others: list[str],
    audience_sample: dict | None = None,
) -> tuple[float, list[str]]:
    """개별 헤드라인 평가 — 총합 점수 + 이유 리스트."""
    scores = {
        "length": _score_length(headline),
        "number": _score_number(headline),
        "question": _score_question(headline),
        "power_word": _score_power_word(headline),
        "clarity": _score_clarity(headline),
        "uniqueness": _score_uniqueness(headline, others),
    }

    # 타겟 오디언스 보정
    if audience_sample:
        age_group = audience_sample.get("age_group", "")
        if age_group in ("10대", "20대") and scores["question"] > 0:
            scores["question"] = min(scores["question"] * 1.3, 1.0)

    total = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
    total = round(total, 4)

    reasons: list[str] = []
    if scores["length"] >= 0.8:
        reasons.append("적절한 길이")
    elif scores["length"] <= 0.3:
        reasons.append("길이가 너무 짧거나 김")
    if scores["number"] > 0:
        reasons.append("숫자 포함으로 구체성 확보")
    if scores["question"] > 0:
        reasons.append("질문형으로 호기심 유발")
    if scores["power_word"] >= 0.5:
        reasons.append("파워 워드 포함")
    if scores["clarity"] >= 0.8:
        reasons.append("명확한 표현")
    if scores["uniqueness"] >= 0.7:
        reasons.append("차별화된 표현")

    return total, reasons


def run_headline_ab(
    headlines: list[str],
    audience_sample: dict | None = None,
) -> WinnerHeadline:
    """헤드라인 A/B 실험 — 점수 기반 승자 선정.

    Args:
        headlines: 비교할 헤드라인 후보 리스트 (2개 이상 권장)
        audience_sample: 타겟 오디언스 정보 (선택, {"age_group": "20대"} 등)

    Returns:
        WinnerHeadline: 승자 헤드라인, 점수, 이유, 전체 점수 목록

    Raises:
        ValueError: 헤드라인이 비어 있는 경우
    """
    if not headlines:
        raise ValueError("최소 1개 이상의 헤드라인이 필요합니다.")

    # 중복 제거 (순서 유지)
    seen = set()
    unique: list[str] = []
    for h in headlines:
        stripped = h.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            unique.append(stripped)

    if not unique:
        raise ValueError("유효한 헤드라인이 없습니다.")

    all_scores: list[dict] = []

    for headline in unique:
        others = [h for h in unique if h != headline]
        score, reasons = _evaluate_headline(headline, others, audience_sample)
        all_scores.append({
            "headline": headline,
            "score": score,
            "reasons": reasons,
        })

    # 점수 내림차순 정렬
    all_scores.sort(key=lambda x: x["score"], reverse=True)
    winner = all_scores[0]

    logger.info("헤드라인 실험 완료: 승자='%s' (%.4f)", winner["headline"], winner["score"])

    return WinnerHeadline(
        headline=winner["headline"],
        score=winner["score"],
        reasons=winner["reasons"],
        all_scores=all_scores,
    )
