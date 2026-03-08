"""
콘텐츠 길이 최적화 서비스

플랫폼별 최적 길이를 분석하고 현재 콘텐츠 대비 추천을 제공합니다.
"""
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# 플랫폼별 최적 길이 범위 (글자 수 기준)
PLATFORM_RANGES = {
    'blog': {'min': 1500, 'max': 3000, 'label': '블로그'},
    'naver_blog': {'min': 1500, 'max': 2500, 'label': '네이버 블로그'},
    'brunch': {'min': 2000, 'max': 4000, 'label': '브런치'},
    'medium': {'min': 1600, 'max': 3200, 'label': 'Medium'},
    'twitter': {'min': 100, 'max': 280, 'label': 'Twitter/X'},
    'instagram': {'min': 100, 'max': 2200, 'label': 'Instagram'},
    'linkedin': {'min': 300, 'max': 1300, 'label': 'LinkedIn'},
    'newsletter': {'min': 500, 'max': 1500, 'label': '뉴스레터'},
    'youtube_desc': {'min': 200, 'max': 500, 'label': 'YouTube 설명'},
    'seo': {'min': 1800, 'max': 2500, 'label': 'SEO 최적화'},
}


def _count_chars(text: str) -> int:
    """공백 제외 글자 수."""
    return len(re.sub(r'\s+', '', text))


def _count_words(text: str) -> int:
    """단어 수 (공백 기준)."""
    return len(text.split())


def _count_sentences(text: str) -> int:
    """문장 수."""
    sentences = re.split(r'[.!?。]+', text)
    return len([s for s in sentences if s.strip()])


def _determine_length_status(char_count: int, platform: Dict) -> tuple:
    """글자 수와 플랫폼 범위를 비교하여 상태/추천을 반환합니다.

    Returns:
        (status, recommendation, optimal_range)
    """
    opt_min = platform['min']
    opt_max = platform['max']
    label = platform.get('label', '')

    if char_count < opt_min:
        diff = opt_min - char_count
        return 'short', f'{label} 기준 약 {diff}자 부족합니다. 내용을 보충하면 더 효과적입니다.', {'min': opt_min, 'max': opt_max}
    elif char_count > opt_max:
        diff = char_count - opt_max
        return 'long', f'{label} 기준 약 {diff}자 초과입니다. 핵심 내용 중심으로 줄이면 가독성이 올라갑니다.', {'min': opt_min, 'max': opt_max}
    return 'optimal', f'{label}에 적합한 길이입니다.', {'min': opt_min, 'max': opt_max}


def analyze_length(
    content: str,
    target_platform: str = 'blog',
) -> Dict:
    """콘텐츠 길이를 분석하고 플랫폼별 최적화를 추천합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        target_platform: 대상 플랫폼 (기본 'blog')

    Returns:
        char_count, word_count, sentence_count, status, recommendation 등을 포함하는 dict
    """
    platform = PLATFORM_RANGES.get(target_platform, PLATFORM_RANGES['blog'])

    if not content or not content.strip():
        return {
            'char_count': 0, 'word_count': 0, 'sentence_count': 0,
            'target_platform': target_platform,
            'optimal_range': {'min': platform['min'], 'max': platform['max']},
            'status': 'short',
            'recommendation': '콘텐츠가 비어 있습니다.',
            'reading_time_min': 0.0,
        }

    char_count = _count_chars(content)
    status, recommendation, optimal_range = _determine_length_status(char_count, platform)

    return {
        'char_count': char_count,
        'word_count': _count_words(content),
        'sentence_count': _count_sentences(content),
        'target_platform': target_platform,
        'optimal_range': optimal_range,
        'status': status,
        'recommendation': recommendation,
        'reading_time_min': round(char_count / 500, 1),
    }
