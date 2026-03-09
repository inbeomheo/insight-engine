"""
B-roll 삽입 제안 서비스 (T12.3)
스크립트 공백 구간에 적합한 시각 자료를 추천합니다.
"""
import uuid
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 시각 자료 유형
VISUAL_TYPES = [
    "stock_video",
    "animation",
    "infographic",
    "photo",
    "screen_recording",
]

# 키워드 → 시각 자료 유형 매핑
KEYWORD_VISUAL_MAP = {
    # screen_recording 관련
    'demo': 'screen_recording',
    'tutorial': 'screen_recording',
    'walkthrough': 'screen_recording',
    'setup': 'screen_recording',
    'install': 'screen_recording',
    '설치': 'screen_recording',
    '설정': 'screen_recording',
    '튜토리얼': 'screen_recording',
    # infographic 관련
    'data': 'infographic',
    'statistics': 'infographic',
    'chart': 'infographic',
    'graph': 'infographic',
    'comparison': 'infographic',
    '통계': 'infographic',
    '비교': 'infographic',
    '수치': 'infographic',
    '데이터': 'infographic',
    # animation 관련
    'process': 'animation',
    'workflow': 'animation',
    'pipeline': 'animation',
    'flow': 'animation',
    '과정': 'animation',
    '흐름': 'animation',
    '프로세스': 'animation',
    # photo 관련
    'portrait': 'photo',
    'landscape': 'photo',
    'product': 'photo',
    'team': 'photo',
    '사진': 'photo',
    '인물': 'photo',
    '제품': 'photo',
}

# 기본 시각 자료 유형
DEFAULT_VISUAL_TYPE = 'stock_video'

# 기본 B-roll 길이 (초)
DEFAULT_DURATION = 5


@dataclass
class BrollSuggestion:
    """B-roll 삽입 제안"""
    suggestion_id: str
    description: str
    visual_type: str
    duration_seconds: int
    relevance: float
    search_keywords: list[str] = field(default_factory=list)


def _extract_keywords(text: str) -> list[str]:
    """텍스트에서 키워드를 추출합니다."""
    if not text:
        return []

    # 소문자 변환 후 단어 분리
    words = re.findall(r'[a-zA-Z가-힣]+', text.lower())
    # 2글자 이상만
    keywords = [w for w in words if len(w) >= 2]
    # 중복 제거 + 순서 유지
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _infer_visual_type(keywords: list[str]) -> str:
    """키워드로부터 적합한 시각 자료 유형을 추론합니다."""
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in KEYWORD_VISUAL_MAP:
            return KEYWORD_VISUAL_MAP[kw_lower]
    return DEFAULT_VISUAL_TYPE


def _calculate_relevance(script_gap: str, context: str, keywords: list[str]) -> float:
    """관련도 점수를 계산합니다 (0.0 ~ 1.0)."""
    score = 0.5  # 기본 점수

    # 키워드가 많을수록 높은 점수
    if len(keywords) >= 5:
        score += 0.2
    elif len(keywords) >= 3:
        score += 0.1

    # 컨텍스트가 있으면 추가 점수
    if context and context.strip():
        context_lower = context.lower()
        matching = sum(1 for kw in keywords if kw in context_lower)
        if matching > 0:
            score += min(0.3, matching * 0.1)

    return min(round(score, 2), 1.0)


def _estimate_duration(script_gap: str) -> int:
    """스크립트 공백 길이에 따른 B-roll 길이를 추정합니다."""
    word_count = len(script_gap.split())
    if word_count <= 5:
        return 3
    elif word_count <= 15:
        return 5
    elif word_count <= 30:
        return 8
    else:
        return 10


def _build_description(keywords: list[str], visual_type: str) -> str:
    """B-roll 설명을 생성합니다."""
    type_labels = {
        'stock_video': '스톡 영상',
        'animation': '애니메이션',
        'infographic': '인포그래픽',
        'photo': '사진',
        'screen_recording': '화면 녹화',
    }
    type_label = type_labels.get(visual_type, visual_type)
    kw_text = ', '.join(keywords[:5]) if keywords else '일반'
    return f"{type_label} — 관련 키워드: {kw_text}"


def generate_broll(script_gap: str, context: str = '') -> list[BrollSuggestion]:
    """스크립트 공백 구간에 대한 B-roll 삽입 제안을 생성합니다.

    Args:
        script_gap: B-roll이 필요한 스크립트 구간 텍스트
        context: 전체 영상의 맥락 정보 (선택)

    Returns:
        BrollSuggestion 리스트 (최대 3개)

    Raises:
        ValueError: script_gap이 비어있을 때
    """
    if not script_gap or not script_gap.strip():
        raise ValueError("script_gap은 필수입니다")

    keywords = _extract_keywords(script_gap)
    context_keywords = _extract_keywords(context) if context else []

    # 키워드 합산 (script_gap 우선)
    all_keywords = keywords + [k for k in context_keywords if k not in keywords]

    suggestions = []

    # 주요 유형 제안
    primary_type = _infer_visual_type(keywords)
    primary_relevance = _calculate_relevance(script_gap, context, keywords)
    duration = _estimate_duration(script_gap)

    suggestions.append(BrollSuggestion(
        suggestion_id=uuid.uuid4().hex[:12],
        description=_build_description(keywords, primary_type),
        visual_type=primary_type,
        duration_seconds=duration,
        relevance=primary_relevance,
        search_keywords=keywords[:8],
    ))

    # 대안 유형 제안 (최대 2개 추가)
    alternative_types = [vt for vt in VISUAL_TYPES if vt != primary_type]
    for alt_type in alternative_types[:2]:
        alt_relevance = max(round(primary_relevance - 0.15, 2), 0.1)
        suggestions.append(BrollSuggestion(
            suggestion_id=uuid.uuid4().hex[:12],
            description=_build_description(keywords, alt_type),
            visual_type=alt_type,
            duration_seconds=duration,
            relevance=alt_relevance,
            search_keywords=keywords[:8],
        ))

    logger.info(f"B-roll 제안 생성: {len(suggestions)}개, 주요 유형={primary_type}")
    return suggestions
