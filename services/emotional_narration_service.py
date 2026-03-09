"""
감정 내레이션 서비스 (T13.2)
텍스트를 감정 태그 기반으로 세그먼트 분할하여 SSML 힌트를 생성합니다.
"""
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 감정별 키워드 매핑 (한국어 + 영어)
_EMOTION_KEYWORDS = {
    "joy": [
        "기쁘", "행복", "즐거", "좋아", "축하", "웃", "신나", "환호", "감사",
        "happy", "joy", "glad", "wonderful", "great", "amazing", "love",
    ],
    "sadness": [
        "슬프", "눈물", "아쉬", "그리", "우울", "외로", "안타깝",
        "sad", "cry", "tear", "miss", "lonely", "sorrow", "grief",
    ],
    "anger": [
        "화나", "분노", "짜증", "열받", "억울", "불만",
        "angry", "fury", "rage", "annoyed", "frustrated", "furious",
    ],
    "fear": [
        "무서", "두려", "불안", "겁", "공포", "걱정", "초조",
        "fear", "scared", "afraid", "anxious", "worry", "terror",
    ],
    "surprise": [
        "놀라", "깜짝", "충격", "황당", "믿기",
        "surprise", "shocked", "amazed", "unexpected", "wow",
    ],
    "calm": [
        "평화", "고요", "편안", "차분", "안정", "여유", "조용",
        "calm", "peaceful", "serene", "relaxed", "quiet", "gentle",
    ],
    "excitement": [
        "흥분", "열정", "기대", "설레", "두근",
        "excited", "thrilled", "eager", "anticipation", "passionate",
    ],
}

# 감정별 SSML 힌트
_SSML_HINTS = {
    "joy": "<prosody rate='medium' pitch='+2st' volume='loud'>",
    "sadness": "<prosody rate='slow' pitch='-2st' volume='soft'>",
    "anger": "<prosody rate='fast' pitch='+3st' volume='x-loud'>",
    "fear": "<prosody rate='fast' pitch='+1st' volume='soft'>",
    "surprise": "<prosody rate='medium' pitch='+4st' volume='loud'>",
    "calm": "<prosody rate='slow' pitch='-1st' volume='medium'>",
    "excitement": "<prosody rate='fast' pitch='+2st' volume='loud'>",
    "neutral": "<prosody rate='medium' pitch='0st' volume='medium'>",
}

# 감정별 기본 강도
_EMOTION_BASE_INTENSITY = {
    "joy": 0.7,
    "sadness": 0.6,
    "anger": 0.8,
    "fear": 0.7,
    "surprise": 0.8,
    "calm": 0.4,
    "excitement": 0.8,
    "neutral": 0.3,
}

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?。])\s+|(?<=\n)\s*')


@dataclass
class EmotionSegment:
    """감정 세그먼트"""
    text: str
    emotion: str
    intensity: float
    ssml_hint: str


@dataclass
class EmotionalNarration:
    """감정 내레이션 결과"""
    text: str
    segments: list
    dominant_emotion: str
    total_segments: int


def _split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리합니다."""
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _detect_emotion(sentence: str, emotion_tags: list = None) -> tuple:
    """
    문장에서 감정을 감지합니다.

    Args:
        sentence: 분석할 문장
        emotion_tags: 우선 적용할 감정 태그 목록

    Returns:
        (감정 이름, 강도) 튜플
    """
    sentence_lower = sentence.lower()

    # 감정 태그가 지정된 경우 우선 매칭
    if emotion_tags:
        for tag in emotion_tags:
            tag_lower = tag.lower().strip()
            if tag_lower in _EMOTION_KEYWORDS:
                keywords = _EMOTION_KEYWORDS[tag_lower]
                if any(kw in sentence_lower for kw in keywords):
                    base = _EMOTION_BASE_INTENSITY.get(tag_lower, 0.5)
                    # 키워드 매칭 수에 따라 강도 보정
                    match_count = sum(1 for kw in keywords if kw in sentence_lower)
                    intensity = min(base + match_count * 0.05, 1.0)
                    return tag_lower, intensity

    # 전체 감정 키워드 스캔
    best_emotion = "neutral"
    best_score = 0

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in sentence_lower)
        if match_count > best_score:
            best_score = match_count
            best_emotion = emotion

    if best_score == 0:
        return "neutral", _EMOTION_BASE_INTENSITY["neutral"]

    base = _EMOTION_BASE_INTENSITY.get(best_emotion, 0.5)
    intensity = min(base + best_score * 0.05, 1.0)
    return best_emotion, intensity


def _get_dominant_emotion(segments: list) -> str:
    """세그먼트 목록에서 가장 빈번한 감정을 반환합니다."""
    if not segments:
        return "neutral"

    # neutral 제외하고 가장 빈번한 감정 찾기
    emotion_counts = {}
    for seg in segments:
        if seg.emotion != "neutral":
            emotion_counts[seg.emotion] = emotion_counts.get(seg.emotion, 0) + 1

    if not emotion_counts:
        return "neutral"

    return max(emotion_counts, key=emotion_counts.get)


def narrate_with_emotion(text: str, emotion_tags: list = None) -> EmotionalNarration:
    """
    텍스트를 감정 태그 기반으로 내레이션 세그먼트로 분할합니다.

    각 문장의 감정을 감지하여 SSML 마크업 힌트를 생성합니다.

    Args:
        text: 내레이션할 텍스트
        emotion_tags: 우선 감지할 감정 태그 목록 (선택)

    Returns:
        EmotionalNarration 결과 객체

    Raises:
        ValueError: 텍스트가 비어있을 때
    """
    if not text or not text.strip():
        raise ValueError("내레이션할 텍스트가 필요합니다")

    text = text.strip()
    sentences = _split_sentences(text)

    # 문장이 분리되지 않으면 전체를 하나의 세그먼트로
    if not sentences:
        sentences = [text]

    segments = []
    for sentence in sentences:
        emotion, intensity = _detect_emotion(sentence, emotion_tags)
        ssml_hint = _SSML_HINTS.get(emotion, _SSML_HINTS["neutral"])

        segment = EmotionSegment(
            text=sentence,
            emotion=emotion,
            intensity=round(intensity, 2),
            ssml_hint=ssml_hint,
        )
        segments.append(segment)

    dominant_emotion = _get_dominant_emotion(segments)

    result = EmotionalNarration(
        text=text,
        segments=segments,
        dominant_emotion=dominant_emotion,
        total_segments=len(segments),
    )

    logger.info(
        "감정 내레이션 완료: segments=%d, dominant=%s",
        result.total_segments, result.dominant_emotion,
    )

    return result
