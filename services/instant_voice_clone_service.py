"""
인스턴트 음성 복제 서비스 (T13.1)
3초 음성 클론 시뮬레이션 — 외부 API 없이 규칙 기반으로 음성 특성을 추출합니다.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 샘플 길이 → 품질 점수 매핑 기준
_QUALITY_THRESHOLDS = [
    (200, 95.0),   # 200자 이상 → 최대 95
    (100, 85.0),   # 100자 이상 → 85
    (50, 70.0),    # 50자 이상 → 70
    (20, 55.0),    # 20자 이상 → 55
    (1, 40.0),     # 1자 이상 → 40
]

# 기본 음성 특성
_DEFAULT_CHARACTERISTICS = {
    "pitch": "medium",
    "speed": "normal",
    "tone": "warm",
}

# 키워드 → 특성 매핑
_PITCH_KEYWORDS = {
    "high": ["높", "high", "sharp", "날카", "밝"],
    "low": ["낮", "low", "deep", "깊", "무거"],
}

_SPEED_KEYWORDS = {
    "fast": ["빠", "fast", "quick", "급", "빠른"],
    "slow": ["느", "slow", "천천", "여유"],
}

_TONE_KEYWORDS = {
    "warm": ["따뜻", "warm", "부드", "soft", "온화"],
    "cold": ["차가", "cold", "cool", "날카"],
    "bright": ["밝", "bright", "활발", "경쾌", "명랑"],
    "calm": ["차분", "calm", "안정", "편안", "고요"],
}


@dataclass
class VoiceClone:
    """음성 복제 결과"""
    clone_id: str
    voice_name: str
    sample_length: int
    characteristics: dict
    quality_score: float
    created_at: str


def _calculate_quality_score(sample_length: int) -> float:
    """샘플 길이에 따라 품질 점수를 산정합니다. 길수록 높음, 최대 100."""
    if sample_length <= 0:
        return 0.0

    for threshold, score in _QUALITY_THRESHOLDS:
        if sample_length >= threshold:
            return min(score + (sample_length - threshold) * 0.02, 100.0)

    return 0.0


def _extract_characteristics(sample_text: str) -> dict:
    """샘플 텍스트에서 키워드를 기반으로 음성 특성을 추출합니다."""
    text_lower = sample_text.lower()
    result = dict(_DEFAULT_CHARACTERISTICS)

    # 피치 감지
    for pitch_val, keywords in _PITCH_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result["pitch"] = pitch_val
            break

    # 속도 감지
    for speed_val, keywords in _SPEED_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result["speed"] = speed_val
            break

    # 톤 감지
    for tone_val, keywords in _TONE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result["tone"] = tone_val
            break

    return result


def clone_voice(sample_text: str, voice_name: str = '') -> VoiceClone:
    """
    3초 음성 클론 시뮬레이션

    샘플 텍스트를 분석하여 음성 특성을 추출하고, 복제 결과를 반환합니다.

    Args:
        sample_text: 음성 샘플 텍스트
        voice_name: 음성 이름 (빈 문자열이면 자동 생성)

    Returns:
        VoiceClone 결과 객체

    Raises:
        ValueError: 샘플 텍스트가 비어있을 때
    """
    if not sample_text or not sample_text.strip():
        raise ValueError("샘플 텍스트가 필요합니다")

    sample_text = sample_text.strip()
    sample_length = len(sample_text)

    # 음성 이름 자동 생성
    if not voice_name or not voice_name.strip():
        voice_name = f"voice_{uuid.uuid4().hex[:8]}"
    else:
        voice_name = voice_name.strip()

    characteristics = _extract_characteristics(sample_text)
    quality_score = _calculate_quality_score(sample_length)

    clone = VoiceClone(
        clone_id=uuid.uuid4().hex,
        voice_name=voice_name,
        sample_length=sample_length,
        characteristics=characteristics,
        quality_score=quality_score,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        "음성 복제 완료: name=%s, length=%d, quality=%.1f",
        clone.voice_name, clone.sample_length, clone.quality_score,
    )

    return clone
