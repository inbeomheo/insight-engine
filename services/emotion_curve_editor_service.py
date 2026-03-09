"""
감정 곡선 편집 서비스

세그먼트별 감정 데이터를 받아 감정 곡선(CurvePoint + 전환)을 생성합니다.
외부 API 없이 규칙 기반으로 동작합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict

logger = logging.getLogger(__name__)

# 지원하는 감정 목록
SUPPORTED_EMOTIONS = (
    'joy', 'sadness', 'anger', 'fear', 'surprise',
    'trust', 'anticipation', 'neutral',
)


@dataclass
class CurvePoint:
    """감정 곡선의 한 점"""
    position: int       # 0-based 위치 인덱스
    emotion: str
    intensity: float    # 0.0 ~ 1.0


@dataclass
class EmotionCurve:
    """감정 곡선 전체"""
    points: List[CurvePoint] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    smoothness: float = 0.0  # 0.0(급격) ~ 1.0(매끄러움)


# 전환 설명 매핑 (감정A → 감정B)
_TRANSITION_LABELS = {
    ('neutral', 'joy'): '평온 → 기쁨: 분위기가 밝아집니다',
    ('joy', 'neutral'): '기쁨 → 평온: 차분하게 정리합니다',
    ('neutral', 'sadness'): '평온 → 슬픔: 감정이 깊어집니다',
    ('sadness', 'neutral'): '슬픔 → 평온: 감정이 회복됩니다',
    ('neutral', 'surprise'): '평온 → 놀라움: 반전이 등장합니다',
    ('surprise', 'neutral'): '놀라움 → 평온: 안정을 되찾습니다',
    ('joy', 'sadness'): '기쁨 → 슬픔: 감정의 급격한 전환입니다',
    ('sadness', 'joy'): '슬픔 → 기쁨: 반전 효과가 극대화됩니다',
    ('neutral', 'anger'): '평온 → 분노: 긴장감이 높아집니다',
    ('anger', 'neutral'): '분노 → 평온: 갈등이 해소됩니다',
    ('neutral', 'fear'): '평온 → 두려움: 불안 요소가 등장합니다',
    ('fear', 'neutral'): '두려움 → 평온: 안도감이 찾아옵니다',
    ('neutral', 'anticipation'): '평온 → 기대: 전개에 대한 기대가 형성됩니다',
    ('anticipation', 'neutral'): '기대 → 평온: 기대가 충족되었습니다',
    ('neutral', 'trust'): '평온 → 신뢰: 안정감이 형성됩니다',
    ('trust', 'neutral'): '신뢰 → 평온: 자연스러운 마무리입니다',
}

_DEFAULT_TRANSITION = '{prev} → {curr}: 감정이 전환됩니다'


def _validate_segment(segment: dict) -> bool:
    """세그먼트 데이터의 유효성을 검증합니다."""
    if not isinstance(segment, dict):
        return False
    if 'emotion' not in segment:
        return False
    if segment.get('emotion') not in SUPPORTED_EMOTIONS:
        return False
    intensity = segment.get('intensity', 0.5)
    if not isinstance(intensity, (int, float)):
        return False
    if not (0.0 <= float(intensity) <= 1.0):
        return False
    return True


def _get_transition_label(prev_emotion: str, curr_emotion: str) -> str:
    """두 감정 사이의 전환 설명을 반환합니다."""
    key = (prev_emotion, curr_emotion)
    if key in _TRANSITION_LABELS:
        return _TRANSITION_LABELS[key]
    return _DEFAULT_TRANSITION.format(prev=prev_emotion, curr=curr_emotion)


def _calculate_smoothness(points: List[CurvePoint]) -> float:
    """곡선의 매끄러움을 계산합니다. (인접 점 간 차이 기반)"""
    if len(points) < 2:
        return 1.0

    total_diff = 0.0
    for i in range(1, len(points)):
        # 감정 변화: 다른 감정이면 0.5, 같으면 0
        emotion_diff = 0.0 if points[i].emotion == points[i - 1].emotion else 0.5
        # 강도 변화
        intensity_diff = abs(points[i].intensity - points[i - 1].intensity)
        total_diff += emotion_diff + intensity_diff

    # 정규화: 최대 변화량 대비 비율 → 매끄러움 역전
    max_diff = (len(points) - 1) * 1.5  # 최대: 0.5(감정) + 1.0(강도)
    roughness = total_diff / max_diff if max_diff > 0 else 0.0
    return round(1.0 - roughness, 3)


def edit_emotion_curve(
    segments: List[Dict],
) -> EmotionCurve:
    """
    세그먼트별 감정 데이터로 감정 곡선을 편집합니다.

    Args:
        segments: 감정 세그먼트 리스트
            각 항목: {"emotion": str, "intensity": float(0~1)}

    Returns:
        EmotionCurve 결과

    Raises:
        ValueError: 유효하지 않은 세그먼트 데이터가 포함된 경우
    """
    if not segments:
        return EmotionCurve(points=[], transitions=[], smoothness=1.0)

    # 유효성 검증
    invalid_indices = []
    for i, seg in enumerate(segments):
        if not _validate_segment(seg):
            invalid_indices.append(i)

    if invalid_indices:
        raise ValueError(
            f'유효하지 않은 세그먼트 인덱스: {invalid_indices}. '
            f'지원 감정: {SUPPORTED_EMOTIONS}, intensity: 0.0~1.0'
        )

    # 포인트 생성
    points = []
    for i, seg in enumerate(segments):
        intensity = float(seg.get('intensity', 0.5))
        intensity = max(0.0, min(1.0, intensity))
        points.append(CurvePoint(
            position=i,
            emotion=seg['emotion'],
            intensity=round(intensity, 3),
        ))

    # 전환 생성
    transitions = []
    for i in range(1, len(points)):
        prev = points[i - 1].emotion
        curr = points[i].emotion
        if prev != curr:
            transitions.append(_get_transition_label(prev, curr))
        else:
            transitions.append(f'{curr}: 감정이 유지됩니다 (강도 변화)')

    # 매끄러움 계산
    smoothness = _calculate_smoothness(points)

    return EmotionCurve(
        points=points,
        transitions=transitions,
        smoothness=smoothness,
    )
