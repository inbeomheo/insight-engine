"""
감정 미스매치 탐지 서비스 — 텍스트와 의도된 감정의 불일치 탐지
"""

import uuid
from dataclasses import dataclass, field


# 감정별 키워드 사전
EMOTION_KEYWORDS = {
    'joy': ['기쁘', '행복', '즐거', '좋아', '환호', '축하', '웃', '신나', 'happy', 'joy', 'glad', 'great', 'love', 'wonderful'],
    'sadness': ['슬프', '우울', '눈물', '아프', '외로', '그리', '안타', 'sad', 'cry', 'miss', 'lonely', 'pain', 'sorry'],
    'anger': ['화나', '분노', '짜증', '열받', '격분', '못된', 'angry', 'rage', 'furious', 'hate', 'annoying'],
    'fear': ['무서', '두려', '공포', '불안', '걱정', '위험', 'fear', 'afraid', 'scary', 'worried', 'danger', 'terrified'],
    'surprise': ['놀라', '깜짝', '예상', '믿기', '충격', 'surprise', 'shocked', 'unexpected', 'wow', 'amazing'],
    'neutral': []
}


@dataclass
class EmotionAnalysis:
    """감정 분석 결과"""
    text: str
    detected_emotion: str  # joy / sadness / anger / fear / surprise / neutral
    confidence: float
    keywords_found: list[str]


@dataclass
class MismatchReport:
    """미스매치 보고서"""
    content_id: str
    analyses: list[EmotionAnalysis]
    mismatches: list[dict]
    severity: str  # low / medium / high


def detect_emotion(text: str) -> EmotionAnalysis:
    """감정 탐지 — 키워드 매칭"""
    text_lower = text.lower()
    scores: dict[str, list[str]] = {}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        found = [kw for kw in keywords if kw in text_lower]
        if found:
            scores[emotion] = found

    if not scores:
        return EmotionAnalysis(
            text=text,
            detected_emotion='neutral',
            confidence=0.5,
            keywords_found=[]
        )

    # 최다 키워드 감정 선택
    best_emotion = max(scores, key=lambda e: len(scores[e]))
    total_keywords = sum(len(v) for v in scores.values())
    confidence = round(min(1.0, len(scores[best_emotion]) / max(total_keywords, 1) * 1.5), 3)

    return EmotionAnalysis(
        text=text,
        detected_emotion=best_emotion,
        confidence=confidence,
        keywords_found=scores[best_emotion]
    )


def check_mismatch(text: str, intended_emotion: str) -> 'dict | None':
    """의도 vs 실제 감정 불일치 확인"""
    analysis = detect_emotion(text)

    if analysis.detected_emotion == intended_emotion:
        return None
    if analysis.detected_emotion == 'neutral':
        return None  # 중립은 불일치로 보지 않음

    return {
        'intended': intended_emotion,
        'detected': analysis.detected_emotion,
        'confidence': analysis.confidence,
        'keywords': analysis.keywords_found,
        'text_snippet': text[:100]
    }


def scan_content(content: str, intended_emotion: str) -> MismatchReport:
    """전체 콘텐츠 스캔 — 문단 단위"""
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    if not paragraphs:
        paragraphs = [content]

    analyses = []
    mismatches = []

    for para in paragraphs:
        analysis = detect_emotion(para)
        analyses.append(analysis)

        mismatch = check_mismatch(para, intended_emotion)
        if mismatch:
            mismatches.append(mismatch)

    # 심각도: 미스매치 비율 기반
    mismatch_ratio = len(mismatches) / max(len(paragraphs), 1)
    if mismatch_ratio > 0.5:
        severity = 'high'
    elif mismatch_ratio > 0.2:
        severity = 'medium'
    else:
        severity = 'low'

    return MismatchReport(
        content_id=str(uuid.uuid4())[:8],
        analyses=analyses,
        mismatches=mismatches,
        severity=severity
    )
