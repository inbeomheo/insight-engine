"""
감정-카피 불일치 감지 서비스

콘텐츠 텍스트에서 감지된 감정과 의도된 감정 간의 불일치를 분석하고,
문제가 되는 구절과 개선 제안을 제공합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class MismatchReport:
    """감정-카피 불일치 분석 보고서"""
    intended_emotion: str
    detected_emotion: str
    mismatch_score: float
    problem_phrases: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# 감정별 키워드 사전
_EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "joy": ["기쁨", "행복", "즐거운", "신나는", "좋은", "멋진", "환상적", "축하", "웃음", "재미"],
    "sadness": ["슬픔", "아쉬운", "우울", "눈물", "안타까운", "외로운", "고독", "실망", "허무", "쓸쓸"],
    "anger": ["분노", "화남", "짜증", "격분", "불만", "억울", "답답", "열받", "최악", "심각"],
    "fear": ["두려움", "불안", "걱정", "공포", "위험", "무서운", "긴장", "경고", "위기", "주의"],
    "trust": ["신뢰", "믿음", "안전", "보장", "검증", "확실", "안심", "보호", "약속", "책임"],
    "surprise": ["놀라운", "충격", "예상", "갑자기", "의외", "반전", "깜짝", "세상에", "대박", "불가능"],
    "neutral": ["정보", "설명", "개요", "방법", "절차", "과정", "단계", "구조", "현황", "분석"],
}

# 감정 간 거리 (불일치 정도). 값이 클수록 멀리 떨어진 감정
_EMOTION_DISTANCE: Dict[str, Dict[str, float]] = {
    "joy": {"joy": 0, "sadness": 1.0, "anger": 0.9, "fear": 0.7, "trust": 0.3, "surprise": 0.4, "neutral": 0.5},
    "sadness": {"joy": 1.0, "sadness": 0, "anger": 0.5, "fear": 0.4, "trust": 0.6, "surprise": 0.6, "neutral": 0.5},
    "anger": {"joy": 0.9, "sadness": 0.5, "anger": 0, "fear": 0.4, "trust": 0.8, "surprise": 0.5, "neutral": 0.6},
    "fear": {"joy": 0.7, "sadness": 0.4, "anger": 0.4, "fear": 0, "trust": 0.7, "surprise": 0.3, "neutral": 0.5},
    "trust": {"joy": 0.3, "sadness": 0.6, "anger": 0.8, "fear": 0.7, "trust": 0, "surprise": 0.5, "neutral": 0.3},
    "surprise": {"joy": 0.4, "sadness": 0.6, "anger": 0.5, "fear": 0.3, "surprise": 0, "trust": 0.5, "neutral": 0.5},
    "neutral": {"joy": 0.5, "sadness": 0.5, "anger": 0.6, "fear": 0.5, "trust": 0.3, "surprise": 0.5, "neutral": 0},
}

# 감정별 개선 제안 템플릿
_SUGGESTIONS: Dict[str, List[str]] = {
    "joy": ["긍정적인 형용사와 감탄 표현을 추가하세요.", "성공 사례나 혜택을 강조하세요."],
    "sadness": ["공감 표현을 사용하되 과도한 부정어는 피하세요.", "해결 방안과 함께 제시하세요."],
    "anger": ["강한 어조를 사용하되 비난보다는 문제 지적에 초점을 맞추세요.", "행동 촉구(CTA)를 명확히 하세요."],
    "fear": ["위험 요소를 구체적으로 제시하세요.", "긴급성을 강조하되 해결책도 함께 제공하세요."],
    "trust": ["데이터나 근거를 제시하세요.", "보증이나 검증 관련 표현을 활용하세요."],
    "surprise": ["예상 밖의 사실이나 통계를 활용하세요.", "반전 구조로 흥미를 유도하세요."],
    "neutral": ["객관적 톤을 유지하고 감정적 표현을 줄이세요.", "정보 전달에 집중하세요."],
}


def _detect_emotion(content: str) -> str:
    """텍스트에서 지배적 감정을 감지합니다."""
    scores: Dict[str, int] = {emotion: 0 for emotion in _EMOTION_KEYWORDS}

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        for kw in keywords:
            count = len(re.findall(re.escape(kw), content))
            scores[emotion] += count

    # 최고 점수 감정 반환 (모두 0이면 neutral)
    max_score = max(scores.values())
    if max_score == 0:
        return "neutral"

    return max(scores, key=lambda e: scores[e])


def _find_problem_phrases(content: str, intended: str, detected: str) -> List[str]:
    """의도와 불일치하는 감정을 유발하는 구절을 찾습니다."""
    if intended == detected:
        return []

    problems: List[str] = []
    # 감지된(의도하지 않은) 감정의 키워드가 포함된 문장 추출
    detected_keywords = _EMOTION_KEYWORDS.get(detected, [])
    sentences = re.split(r'[.!?\n]+', content)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        for kw in detected_keywords:
            if kw in sentence and sentence not in problems:
                problems.append(sentence)
                break

    return problems[:5]  # 최대 5개


def detect_mismatch(content: str, intended_emotion: str) -> MismatchReport:
    """콘텐츠의 감정 불일치를 감지합니다.

    Args:
        content: 분석할 콘텐츠 텍스트.
        intended_emotion: 의도한 감정 (joy, sadness, anger, fear, trust, surprise, neutral).

    Returns:
        MismatchReport: 불일치 분석 결과.
    """
    if not content or not content.strip():
        logger.warning("빈 콘텐츠가 전달되었습니다.")
        return MismatchReport(
            intended_emotion=intended_emotion,
            detected_emotion="neutral",
            mismatch_score=0.0,
        )

    # 의도된 감정 정규화
    intended = intended_emotion.lower().strip()
    if intended not in _EMOTION_KEYWORDS:
        logger.warning("알 수 없는 감정: '%s', neutral로 대체합니다.", intended)
        intended = "neutral"

    detected = _detect_emotion(content)

    # 불일치 점수 계산
    distance_map = _EMOTION_DISTANCE.get(intended, {})
    mismatch_score = distance_map.get(detected, 0.5)

    problem_phrases = _find_problem_phrases(content, intended, detected)

    # 개선 제안 생성
    suggestions: List[str] = []
    if mismatch_score > 0.3:
        suggestions = list(_SUGGESTIONS.get(intended, []))
        if problem_phrases:
            suggestions.append(
                f"'{detected}' 톤의 표현 {len(problem_phrases)}개를 "
                f"'{intended}' 톤으로 교체하세요."
            )

    logger.info(
        "감정 불일치 분석: intended=%s, detected=%s, score=%.2f",
        intended, detected, mismatch_score,
    )

    return MismatchReport(
        intended_emotion=intended,
        detected_emotion=detected,
        mismatch_score=round(mismatch_score, 4),
        problem_phrases=problem_phrases,
        suggestions=suggestions,
    )
