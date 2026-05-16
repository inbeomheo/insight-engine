"""
가독성 최적화 서비스

콘텐츠의 가독성을 분석하고 목표 수준에 맞게
규칙 기반으로 개선 제안을 생성합니다.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 가독성 수준 정의
READABILITY_LEVELS = {
    'easy': {
        'label': '쉬움',
        'max_sentence_length': 30,
        'max_paragraph_sentences': 4,
        'description': '초등학생도 이해할 수 있는 수준 (SNS, 캐주얼 블로그)',
    },
    'standard': {
        'label': '보통',
        'max_sentence_length': 50,
        'max_paragraph_sentences': 6,
        'description': '일반 독자가 편하게 읽을 수 있는 수준 (뉴스, 블로그)',
    },
    'advanced': {
        'label': '전문적',
        'max_sentence_length': 80,
        'max_paragraph_sentences': 8,
        'description': '전문 지식이 있는 독자 대상 (기술 문서, 보고서)',
    },
}

SUPPORTED_LEVELS = list(READABILITY_LEVELS.keys())

# 복잡한 표현 → 간단한 대안
_SIMPLIFICATION_MAP = {
    '에 있어서': '에서',
    '하는 것이 가능하다': '할 수 있다',
    '를 실시하다': '하다',
    '에 대하여': '에 대해',
    '함에 있어': '할 때',
    '하는 바이다': '합니다',
    '인 것으로 판단된다': '로 보인다',
    '할 필요가 있다': '해야 한다',
    '하는 것으로 나타났다': '했다',
    '의 경우에는': '에서는',
}


def _split_sentences(text: str) -> List[str]:
    """문장 단위 분리."""
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _count_chars_no_space(text: str) -> int:
    """공백 제외 글자 수."""
    return len(re.sub(r'\s', '', text))


def analyze_readability(content: str) -> dict:
    """콘텐츠의 가독성을 분석합니다.

    Returns:
        {
            'level': str,
            'score': float (0.0~1.0, 높을수록 읽기 쉬움),
            'avg_sentence_length': float,
            'long_sentences': [{'text': str, 'length': int, 'index': int}],
            'complex_expressions': [{'original': str, 'suggestion': str}],
            'paragraph_stats': {'count': int, 'avg_sentences': float},
            'suggestions': [str],
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()
    # 마크다운 헤딩 제거 후 분석
    clean_text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE).strip()
    sentences = _split_sentences(clean_text)

    if not sentences:
        return _empty_result()

    # 문장 길이 분석
    lengths = [_count_chars_no_space(s) for s in sentences]
    avg_length = sum(lengths) / len(lengths)

    # 긴 문장 감지 (50자 초과)
    long_sentences = []
    for i, (sent, length) in enumerate(zip(sentences, lengths)):
        if length > 50:
            long_sentences.append({
                'text': sent[:100] + ('...' if len(sent) > 100 else ''),
                'length': length,
                'index': i,
            })

    # 복잡한 표현 감지
    complex_expressions = []
    for pattern, suggestion in _SIMPLIFICATION_MAP.items():
        if pattern in clean_text:
            complex_expressions.append({
                'original': pattern,
                'suggestion': suggestion,
            })

    # 문단 분석
    paragraphs = [p for p in text.split('\n\n') if p.strip() and not p.strip().startswith('#')]
    paragraph_count = len(paragraphs) if paragraphs else 1
    para_sentence_counts = []
    for para in paragraphs:
        para_sents = _split_sentences(para)
        para_sentence_counts.append(len(para_sents))
    avg_para_sentences = sum(para_sentence_counts) / max(1, len(para_sentence_counts))

    # 가독성 점수 (0~1, 높을수록 쉬움)
    score = _calculate_score(avg_length, len(long_sentences), len(sentences), complex_expressions)

    # 수준 판정
    if score >= 0.7:
        level = 'easy'
    elif score >= 0.4:
        level = 'standard'
    else:
        level = 'advanced'

    # 개선 제안 생성
    suggestions = _generate_suggestions(
        avg_length, long_sentences, complex_expressions,
        avg_para_sentences, level,
    )

    return {
        'level': level,
        'score': round(score, 2),
        'avg_sentence_length': round(avg_length, 1),
        'long_sentences': long_sentences[:10],
        'complex_expressions': complex_expressions,
        'paragraph_stats': {
            'count': paragraph_count,
            'avg_sentences': round(avg_para_sentences, 1),
        },
        'suggestions': suggestions,
    }


def _calculate_score(avg_length: float, long_count: int,
                     total_sentences: int, complex_exprs: list) -> float:
    """가독성 점수 계산."""
    score = 1.0

    # 평균 문장 길이 패널티
    if avg_length > 60:
        score -= 0.4
    elif avg_length > 40:
        score -= 0.2
    elif avg_length > 30:
        score -= 0.1

    # 긴 문장 비율 패널티
    if total_sentences > 0:
        long_ratio = long_count / total_sentences
        score -= min(0.3, long_ratio * 0.5)

    # 복잡한 표현 패널티
    score -= min(0.2, len(complex_exprs) * 0.05)

    return max(0.0, min(1.0, score))


def _generate_suggestions(avg_length: float, long_sentences: list,
                          complex_exprs: list, avg_para_sentences: float,
                          level: str) -> List[str]:
    """개선 제안 목록을 생성합니다."""
    suggestions = []

    if avg_length > 40:
        suggestions.append(
            f'평균 문장 길이({avg_length:.0f}자)가 길어요. 30~40자로 줄이면 읽기 쉬워집니다.'
        )

    if long_sentences:
        suggestions.append(
            f'{len(long_sentences)}개 문장이 50자를 초과합니다. 나눠서 쓰는 것을 권장합니다.'
        )

    if complex_exprs:
        examples = ', '.join(f'"{e["original"]}"→"{e["suggestion"]}"' for e in complex_exprs[:3])
        suggestions.append(f'복잡한 표현을 간결하게: {examples}')

    if avg_para_sentences > 6:
        suggestions.append(
            f'문단당 평균 {avg_para_sentences:.1f}개 문장이 있습니다. 4~5개로 나누면 가독성이 높아집니다.'
        )

    if not suggestions:
        suggestions.append('가독성이 좋습니다! 현재 수준을 유지하세요.')

    return suggestions


def get_readability_levels() -> list:
    """지원 가독성 수준 목록을 반환합니다."""
    return [
        {'id': level, 'label': info['label'], 'description': info['description']}
        for level, info in READABILITY_LEVELS.items()
    ]


def _empty_result() -> dict:
    return {
        'level': 'standard',
        'score': 0.0,
        'avg_sentence_length': 0,
        'long_sentences': [],
        'complex_expressions': [],
        'paragraph_stats': {'count': 0, 'avg_sentences': 0},
        'suggestions': [],
    }
