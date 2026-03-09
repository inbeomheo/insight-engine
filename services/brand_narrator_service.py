"""
브랜드 내레이터 서비스 (T13.1)
브랜드 설명에서 키워드를 추출하여 보이스 프로필을 설계합니다.
"""
import logging
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 톤 키워드 매핑
_TONE_MAP = {
    "professional": ["전문", "비즈니스", "공식", "professional", "business", "formal", "기업"],
    "friendly": ["친근", "친절", "따뜻", "friendly", "warm", "casual", "편안"],
    "authoritative": ["권위", "신뢰", "전문가", "authoritative", "expert", "trusted"],
    "playful": ["재미", "유쾌", "활발", "playful", "fun", "lively", "밝"],
    "calm": ["차분", "안정", "고요", "calm", "serene", "peaceful", "편안"],
    "energetic": ["에너지", "열정", "역동", "energetic", "passionate", "dynamic"],
}

# 속도 키워드 매핑
_PACE_MAP = {
    "slow": ["느", "천천", "여유", "slow", "relaxed"],
    "moderate": ["보통", "적당", "moderate", "standard"],
    "fast": ["빠", "빠른", "급", "fast", "quick", "dynamic"],
}

# 어휘 수준 키워드 매핑
_VOCAB_MAP = {
    "simple": ["쉬운", "간단", "대중", "simple", "easy", "beginner", "일반"],
    "intermediate": ["중간", "보통", "intermediate"],
    "advanced": ["전문", "고급", "technical", "advanced", "심화", "기술"],
}

# 브랜드 가치 → 보이스 특성 매핑
_VALUE_TRAIT_MAP = {
    "innovation": "혁신적 사고를 반영하는 목소리",
    "trust": "신뢰감을 주는 안정적인 톤",
    "creativity": "창의적이고 자유로운 표현",
    "quality": "정제되고 품격 있는 어조",
    "speed": "빠르고 간결한 전달력",
    "simplicity": "군더더기 없는 명확한 화법",
    "warmth": "따뜻하고 공감하는 목소리",
    "혁신": "혁신적 사고를 반영하는 목소리",
    "신뢰": "신뢰감을 주는 안정적인 톤",
    "창의": "창의적이고 자유로운 표현",
    "품질": "정제되고 품격 있는 어조",
    "속도": "빠르고 간결한 전달력",
    "단순": "군더더기 없는 명확한 화법",
    "따뜻": "따뜻하고 공감하는 목소리",
}


@dataclass
class NarratorProfile:
    """브랜드 내레이터 프로필"""
    narrator_id: str
    name: str
    description: str
    voice_traits: list
    tone: str
    pace: str
    vocabulary_level: str
    sample_script: str


def _detect_value(text: str, keyword_map: dict, default: str) -> str:
    """텍스트에서 키워드를 매칭하여 값을 감지합니다."""
    text_lower = text.lower()
    for value, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            return value
    return default


def _build_voice_traits(description: str, brand_values: list) -> list:
    """설명과 브랜드 가치에서 보이스 특성 목록을 생성합니다."""
    traits = []

    # 브랜드 가치에서 특성 추출
    if brand_values:
        for value in brand_values:
            value_lower = value.lower().strip()
            for key, trait in _VALUE_TRAIT_MAP.items():
                if key in value_lower:
                    traits.append(trait)
                    break
            else:
                # 매핑에 없으면 직접 특성으로 추가
                traits.append(f"{value} 지향적 화법")

    # 설명에서 추가 특성 추출
    desc_lower = description.lower()
    if "유머" in desc_lower or "humor" in desc_lower:
        traits.append("적절한 유머 활용")
    if "데이터" in desc_lower or "data" in desc_lower:
        traits.append("데이터 기반 설득력")
    if "스토리" in desc_lower or "story" in desc_lower:
        traits.append("스토리텔링 중심 전달")

    # 특성이 없으면 기본값 추가
    if not traits:
        traits = ["명확한 전달력", "일관된 톤 유지"]

    return traits


def _generate_sample_script(name: str, tone: str, pace: str) -> str:
    """내레이터 프로필 기반 샘플 스크립트를 생성합니다."""
    tone_intro = {
        "professional": "안녕하세요, 오늘 소개해 드릴 내용은",
        "friendly": "안녕하세요! 오늘은 정말 재미있는 이야기를 해볼게요.",
        "authoritative": "주목해 주십시오. 오늘 다룰 주제는",
        "playful": "자, 여러분! 오늘은 신나는 이야기가 준비되어 있어요!",
        "calm": "편안하게 들어주세요. 오늘 나눌 이야기는",
        "energetic": "여러분, 준비되셨나요? 오늘의 주제로 바로 들어갑니다!",
    }

    intro = tone_intro.get(tone, "안녕하세요, 오늘 소개해 드릴 내용은")
    return f"[{name}] {intro} 이 콘텐츠의 핵심 내용에 대한 것입니다."


def design_narrator(description: str, brand_values: list = None) -> NarratorProfile:
    """
    브랜드 보이스 내레이터를 설계합니다.

    설명 텍스트에서 키워드를 추출하여 톤, 속도, 어휘 수준을 결정하고,
    브랜드 가치가 있으면 보이스 특성에 반영합니다.

    Args:
        description: 브랜드/내레이터 설명 텍스트
        brand_values: 브랜드 핵심 가치 목록 (선택)

    Returns:
        NarratorProfile 객체

    Raises:
        ValueError: 설명이 비어있을 때
    """
    if not description or not description.strip():
        raise ValueError("브랜드 설명이 필요합니다")

    description = description.strip()
    brand_values = brand_values or []

    # 키워드 기반 속성 감지
    tone = _detect_value(description, _TONE_MAP, "professional")
    pace = _detect_value(description, _PACE_MAP, "moderate")
    vocabulary_level = _detect_value(description, _VOCAB_MAP, "intermediate")

    # 보이스 특성 생성
    voice_traits = _build_voice_traits(description, brand_values)

    # 내레이터 이름 생성
    name = f"Narrator-{uuid.uuid4().hex[:6]}"

    # 샘플 스크립트 생성
    sample_script = _generate_sample_script(name, tone, pace)

    profile = NarratorProfile(
        narrator_id=uuid.uuid4().hex,
        name=name,
        description=description,
        voice_traits=voice_traits,
        tone=tone,
        pace=pace,
        vocabulary_level=vocabulary_level,
        sample_script=sample_script,
    )

    logger.info(
        "내레이터 프로필 생성: name=%s, tone=%s, pace=%s, vocab=%s",
        profile.name, profile.tone, profile.pace, profile.vocabulary_level,
    )

    return profile
