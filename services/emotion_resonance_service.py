"""
감정 공명 분석 서비스

콘텐츠의 텍스트에서 목표 감정과의 공명도를 분석합니다.
외부 API 없이 키워드 기반 감정 분석으로 동작합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 목표 감정별 관련 키워드 사전
_EMOTION_KEYWORDS = {
    'joy': {
        'ko': ['기쁨', '행복', '즐거운', '웃음', '좋은', '신나는', '환호', '축하', '감사', '사랑',
               '설레', '밝은', '희망', '기뻐', '만족', '뿌듯', '흐뭇', '재미', '유쾌'],
        'en': ['happy', 'joy', 'glad', 'delight', 'cheerful', 'wonderful', 'great',
               'love', 'amazing', 'fantastic', 'excited', 'fun', 'smile', 'laugh'],
    },
    'trust': {
        'ko': ['신뢰', '믿음', '확신', '안전', '보장', '검증', '증명', '실증', '전문',
               '경험', '데이터', '근거', '실제', '사실', '정확', '꾸준', '일관'],
        'en': ['trust', 'reliable', 'proven', 'verified', 'safe', 'secure', 'expert',
               'experience', 'data', 'evidence', 'fact', 'accurate', 'consistent'],
    },
    'anticipation': {
        'ko': ['기대', '앞으로', '미래', '다가올', '준비', '예정', '계획', '전망',
               '가능성', '곧', '드디어', '변화', '새로운', '혁신', '발전', '성장'],
        'en': ['anticipate', 'expect', 'future', 'upcoming', 'prepare', 'plan',
               'potential', 'soon', 'change', 'new', 'innovation', 'growth', 'next'],
    },
    'surprise': {
        'ko': ['놀랍', '충격', '예상치', '반전', '의외', '뜻밖', '갑자기', '깜짝',
               '상상도', '몰랐', '처음', '특이', '독특', '파격', '전례없'],
        'en': ['surprise', 'unexpected', 'shocking', 'twist', 'sudden', 'unbelievable',
               'astonishing', 'remarkable', 'unprecedented', 'never', 'first', 'unique'],
    },
}

# 감정별 개선 제안 템플릿
_SUGGESTIONS = {
    'joy': [
        '긍정적 결과나 성취를 강조하는 문장을 추가하세요',
        '독자가 공감할 수 있는 기쁜 경험을 포함하세요',
        '감사나 축하의 표현을 자연스럽게 녹여보세요',
    ],
    'trust': [
        '구체적인 수치나 데이터를 인용하세요',
        '전문가 의견이나 사례를 추가하세요',
        '출처를 명확히 밝혀 신뢰도를 높이세요',
    ],
    'anticipation': [
        '미래의 가능성과 비전을 제시하세요',
        '독자가 기대할 수 있는 구체적 혜택을 나열하세요',
        '"다음 단계"나 "앞으로" 같은 전진 표현을 활용하세요',
    ],
    'surprise': [
        '예상을 뒤집는 사실이나 통계를 배치하세요',
        '도입부에 반전 요소를 추가하세요',
        '"사실은...", "의외로..." 같은 전환 표현을 사용하세요',
    ],
}

SUPPORTED_EMOTIONS = list(_EMOTION_KEYWORDS.keys())


@dataclass
class ResonanceScore:
    """감정 공명 분석 결과"""
    target_emotion: str
    resonance_level: float  # 0.0 ~ 1.0
    matching_phrases: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


def _find_matching_phrases(content: str, keywords: dict) -> List[str]:
    """콘텐츠에서 감정 키워드와 매칭되는 구절을 찾습니다."""
    matches = []
    content_lower = content.lower()
    all_keywords = keywords.get('ko', []) + keywords.get('en', [])

    for keyword in all_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in content_lower:
            # 키워드 주변 컨텍스트 추출 (앞뒤 15자)
            idx = content_lower.find(keyword_lower)
            start = max(0, idx - 15)
            end = min(len(content), idx + len(keyword) + 15)
            phrase = content[start:end].strip()
            if phrase and phrase not in matches:
                matches.append(phrase)

    return matches


def _calculate_resonance(content: str, keywords: dict) -> float:
    """감정 키워드 빈도 기반으로 공명도를 계산합니다."""
    if not content:
        return 0.0

    content_lower = content.lower()
    words = content_lower.split()
    total_words = len(words) if words else 1

    all_keywords = keywords.get('ko', []) + keywords.get('en', [])
    match_count = 0
    for keyword in all_keywords:
        match_count += content_lower.count(keyword.lower())

    # 키워드 밀도 → 0~1 정규화 (밀도 0.05 이상이면 1.0)
    density = match_count / total_words
    resonance = min(1.0, density / 0.05)
    return round(resonance, 3)


def _get_suggestions(target_emotion: str, resonance_level: float) -> List[str]:
    """공명도에 따른 개선 제안을 반환합니다."""
    suggestions = _SUGGESTIONS.get(target_emotion, [])
    if resonance_level >= 0.7:
        return [f'현재 {target_emotion} 감정이 잘 전달되고 있습니다']
    return suggestions


def analyze_resonance(content: str, target_emotion: str) -> ResonanceScore:
    """
    콘텐츠의 감정 공명도를 분석합니다.

    Args:
        content: 분석 대상 텍스트
        target_emotion: 목표 감정 ("joy", "trust", "anticipation", "surprise")

    Returns:
        ResonanceScore 결과

    Raises:
        ValueError: 지원하지 않는 감정이 지정된 경우
    """
    if not content or not content.strip():
        return ResonanceScore(
            target_emotion=target_emotion,
            resonance_level=0.0,
            matching_phrases=[],
            suggestions=_SUGGESTIONS.get(target_emotion, []),
        )

    if target_emotion not in _EMOTION_KEYWORDS:
        raise ValueError(
            f'지원하지 않는 감정: {target_emotion}. '
            f'지원 목록: {SUPPORTED_EMOTIONS}'
        )

    keywords = _EMOTION_KEYWORDS[target_emotion]
    matching_phrases = _find_matching_phrases(content, keywords)
    resonance_level = _calculate_resonance(content, keywords)
    suggestions = _get_suggestions(target_emotion, resonance_level)

    return ResonanceScore(
        target_emotion=target_emotion,
        resonance_level=resonance_level,
        matching_phrases=matching_phrases,
        suggestions=suggestions,
    )
