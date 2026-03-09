"""
감정 곡선(Emotion Arc) 분석 서비스
자막 텍스트를 구간별로 나누어 감정 키워드 매칭 기반으로
감정 곡선을 생성한다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 유효 감정 타입
VALID_EMOTIONS = {"joy", "sadness", "anger", "fear", "surprise", "neutral"}

# 감정 키워드 사전 (한국어 + 영어)
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "joy": [
        "기쁘", "행복", "즐겁", "좋", "최고", "멋지", "훌륭", "감사",
        "축하", "사랑", "재밌", "웃", "대박", "신나", "만족",
        "happy", "great", "love", "awesome", "wonderful", "enjoy",
        "amazing", "fantastic", "excellent", "fun", "glad", "pleased",
    ],
    "sadness": [
        "슬프", "아쉽", "안타깝", "그립", "외롭", "우울", "눈물",
        "힘들", "괴롭", "불행", "상실", "이별", "실망",
        "sad", "miss", "lonely", "depressed", "unfortunate",
        "disappointed", "sorrow", "grief", "regret", "lost",
    ],
    "anger": [
        "화나", "분노", "짜증", "열받", "어이없", "미치", "싫",
        "나쁘", "못된", "비겁", "불공정", "부당",
        "angry", "furious", "annoyed", "frustrated", "hate",
        "outraged", "irritated", "mad", "unfair", "ridiculous",
    ],
    "fear": [
        "무섭", "두렵", "걱정", "불안", "긴장", "위험", "공포",
        "겁", "조심", "위협", "경고",
        "afraid", "scary", "worried", "anxious", "danger",
        "fear", "nervous", "threat", "warning", "panic",
    ],
    "surprise": [
        "놀라", "깜짝", "신기", "의외", "예상", "뜻밖", "충격",
        "반전", "갑자기", "헉", "와",
        "surprise", "unexpected", "wow", "shocking", "sudden",
        "unbelievable", "incredible", "plot twist", "turns out",
    ],
}

# 감정별 기본 강도 가중치
EMOTION_BASE_INTENSITY = {
    "joy": 0.6,
    "sadness": 0.6,
    "anger": 0.7,
    "fear": 0.7,
    "surprise": 0.8,
    "neutral": 0.3,
}


@dataclass
class EmotionPoint:
    """감정 곡선의 한 지점"""
    timestamp: str
    emotion: str
    intensity: float  # 0.0 ~ 1.0
    text_snippet: str


@dataclass
class EmotionArc:
    """전체 감정 곡선"""
    video_id: str
    points: List[EmotionPoint]
    dominant_emotion: str
    arc_type: str  # "rising", "falling", "wave", "stable"


def _detect_emotion(text: str) -> Tuple[str, float]:
    """텍스트에서 감정과 강도를 탐지

    Returns:
        (감정, 강도) 튜플
    """
    text_lower = text.lower()
    scores: Dict[str, int] = {e: 0 for e in VALID_EMOTIONS if e != "neutral"}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[emotion] = scores.get(emotion, 0) + 1

    total_hits = sum(scores.values())
    if total_hits == 0:
        return "neutral", EMOTION_BASE_INTENSITY["neutral"]

    # 가장 높은 감정 선택
    best_emotion = max(scores, key=scores.get)
    best_count = scores[best_emotion]

    # 강도 계산: 기본 강도 + 키워드 매칭 비율 보정
    base = EMOTION_BASE_INTENSITY.get(best_emotion, 0.5)
    bonus = min(best_count * 0.1, 0.4)  # 최대 0.4 보너스
    intensity = round(min(base + bonus, 1.0), 2)

    return best_emotion, intensity


def _split_into_segments(
    transcript: str,
    segment_count: int = 10,
) -> List[Tuple[str, str]]:
    """자막을 구간별로 분할

    [MM:SS] 타임스탬프가 있으면 그 기준으로, 없으면 균등 분할.

    Returns:
        [(타임스탬프, 텍스트)] 리스트
    """
    # 타임스탬프 패턴 감지
    pattern = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?)(?=\[|$)', re.DOTALL)
    matches = list(pattern.finditer(transcript))

    if matches:
        segments = []
        for match in matches:
            ts = match.group(1)
            text = match.group(2).strip()
            if text:
                segments.append((ts, text))
        return segments

    # 타임스탬프 없으면 균등 분할
    lines = [ln.strip() for ln in transcript.split('\n') if ln.strip()]
    if not lines:
        return []

    # segment_count 조절 (최소 라인 수 고려)
    actual_segments = min(segment_count, len(lines))
    if actual_segments <= 0:
        return []

    chunk_size = max(1, len(lines) // actual_segments)
    segments = []

    for i in range(actual_segments):
        start = i * chunk_size
        end = start + chunk_size if i < actual_segments - 1 else len(lines)
        chunk_text = ' '.join(lines[start:end])
        # 가상 타임스탬프 생성 (구간 비율 기반)
        total_seconds = actual_segments * 60  # 1구간 = 약 1분 가정
        ts_seconds = i * 60
        minutes = ts_seconds // 60
        seconds = ts_seconds % 60
        ts = f"{minutes:02d}:{seconds:02d}"
        segments.append((ts, chunk_text))

    return segments


def _determine_arc_type(points: List[EmotionPoint]) -> str:
    """감정 포인트 시퀀스에서 곡선 유형 결정"""
    if len(points) < 2:
        return "stable"

    intensities = [p.intensity for p in points]

    # 상승/하강 추세 판별
    rising_count = 0
    falling_count = 0

    for i in range(1, len(intensities)):
        diff = intensities[i] - intensities[i - 1]
        if diff > 0.05:
            rising_count += 1
        elif diff < -0.05:
            falling_count += 1

    total_changes = rising_count + falling_count
    if total_changes == 0:
        return "stable"

    rising_ratio = rising_count / total_changes
    falling_ratio = falling_count / total_changes

    # 상승과 하강이 비슷하면 wave
    if abs(rising_ratio - falling_ratio) < 0.3:
        return "wave"

    if rising_ratio > 0.6:
        return "rising"
    if falling_ratio > 0.6:
        return "falling"

    return "wave"


def _determine_dominant_emotion(points: List[EmotionPoint]) -> str:
    """가장 많이 등장하는 감정 결정"""
    if not points:
        return "neutral"

    emotion_counts: Dict[str, int] = {}
    for p in points:
        emotion_counts[p.emotion] = emotion_counts.get(p.emotion, 0) + 1

    return max(emotion_counts, key=emotion_counts.get)


def _truncate_snippet(text: str, max_len: int = 100) -> str:
    """텍스트 스니펫을 최대 길이로 자름"""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def map_emotion_arc(
    video_id: str,
    transcript: str = '',
) -> EmotionArc:
    """자막 텍스트에서 감정 곡선을 생성한다.

    Args:
        video_id: YouTube 영상 ID
        transcript: 자막 텍스트

    Returns:
        EmotionArc
    """
    if not video_id or not video_id.strip():
        logger.warning("video_id가 비어 있습니다")
        return EmotionArc(
            video_id="", points=[], dominant_emotion="neutral", arc_type="stable",
        )

    video_id = video_id.strip()

    if not transcript or not transcript.strip():
        logger.info("자막이 비어 있어 빈 감정 곡선을 반환합니다")
        return EmotionArc(
            video_id=video_id, points=[], dominant_emotion="neutral", arc_type="stable",
        )

    # 구간 분할
    segments = _split_into_segments(transcript)
    if not segments:
        return EmotionArc(
            video_id=video_id, points=[], dominant_emotion="neutral", arc_type="stable",
        )

    # 각 구간 감정 분석
    points: List[EmotionPoint] = []
    for ts, text in segments:
        emotion, intensity = _detect_emotion(text)
        points.append(EmotionPoint(
            timestamp=ts,
            emotion=emotion,
            intensity=intensity,
            text_snippet=_truncate_snippet(text),
        ))

    dominant = _determine_dominant_emotion(points)
    arc_type = _determine_arc_type(points)

    logger.info(
        "video_id=%s: 감정 곡선 생성 (%d 포인트, 주요 감정: %s, 유형: %s)",
        video_id, len(points), dominant, arc_type,
    )

    return EmotionArc(
        video_id=video_id,
        points=points,
        dominant_emotion=dominant,
        arc_type=arc_type,
    )
