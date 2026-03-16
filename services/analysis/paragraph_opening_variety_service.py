"""
Paragraph Opening Variety Checker 서비스

문단 첫 문장의 시작 패턴이 반복되는지 점검합니다.
단조로운 문단 도입을 감지하여 다양한 시작 방식을 권장합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


# 마크다운 헤딩
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 마크다운 리스트/인용 제거
_LIST_RE = re.compile(r'^\s*[-*+]\s+|^\s*\d+[.)]\s+|^>\s+', re.MULTILINE)

# 문단 시작 패턴 추출 (첫 2-3어절)
_OPENING_EXTRACT_KO = re.compile(r'^([가-힣]+(?:\s+[가-힣]+)?)')
_OPENING_EXTRACT_EN = re.compile(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)', re.IGNORECASE)


def _extract_paragraphs(content: str) -> List[str]:
    """콘텐츠에서 문단 첫 문장을 추출합니다."""
    # 헤딩, 리스트 제거
    cleaned = _HEADING_RE.sub('', content)
    cleaned = _LIST_RE.sub('', cleaned)

    # 빈 줄로 문단 분리
    paragraphs = re.split(r'\n\s*\n', cleaned)
    openings = []
    for para in paragraphs:
        text = para.strip()
        if text and len(text) >= 5:
            # 첫 문장 추출
            first_sentence = re.split(r'[.!?]\s', text)[0].strip()
            if first_sentence and len(first_sentence) >= 3:
                openings.append(first_sentence)
    return openings


def _get_opening_pattern(sentence: str) -> str:
    """문장의 시작 패턴(첫 1-2 어절)을 추출합니다."""
    sentence = sentence.strip()
    # 한국어 시작
    m = _OPENING_EXTRACT_KO.match(sentence)
    if m:
        return m.group(1)
    # 영어 시작
    m = _OPENING_EXTRACT_EN.match(sentence)
    if m:
        return m.group(1).lower()
    # 기타
    words = sentence.split()
    if words:
        return words[0].lower() if len(words[0]) > 1 else ' '.join(words[:2]).lower()
    return ''


_EMPTY_SUMMARY = {'total_paragraphs': 0, 'unique_patterns': 0,
                   'variety_rate': 0.0, 'most_repeated': ''}


def _build_opening_data(paragraph_openings: list) -> tuple:
    """문단 시작 패턴 데이터를 구성합니다.

    Returns:
        (openings, pattern_frequency, pattern_counter)
    """
    patterns = [_get_opening_pattern(o) for o in paragraph_openings]
    pattern_counter = Counter(p for p in patterns if p)

    openings = []
    for text, pattern in zip(paragraph_openings, patterns):
        openings.append({
            'text': text if len(text) <= 80 else text[:77] + '...',
            'pattern': pattern,
            'is_repeated': pattern_counter.get(pattern, 0) > 1,
        })

    pattern_frequency = [
        {'pattern': pattern, 'count': count}
        for pattern, count in pattern_counter.most_common()
        if count > 1
    ]

    return openings, pattern_frequency, pattern_counter


def _compute_variety_score(variety_rate: float, max_repeat: int) -> float:
    """다양성 점수를 계산합니다."""
    if variety_rate >= 80:
        score = 100.0
    elif variety_rate >= 60:
        score = 80.0 + (variety_rate - 60) * 1.0
    elif variety_rate >= 40:
        score = 60.0 + (variety_rate - 40) * 1.0
    else:
        score = max(0.0, variety_rate * 1.5)

    if max_repeat >= 4:
        score = max(0.0, score - (max_repeat - 3) * 10)

    return round(max(0.0, min(100.0, score)), 1)


def check_paragraph_opening_variety(content: str) -> dict:
    """문단 시작 패턴의 다양성을 점검합니다.

    Returns:
        openings, pattern_frequency, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {'openings': [], 'pattern_frequency': [],
                    'summary': dict(_EMPTY_SUMMARY), 'score': 100.0, 'suggestions': []}

        paragraph_openings = _extract_paragraphs(content)
        if len(paragraph_openings) < 2:
            return {
                'openings': [{'text': o, 'pattern': _get_opening_pattern(o)}
                             for o in paragraph_openings],
                'pattern_frequency': [],
                'summary': {**_EMPTY_SUMMARY, 'total_paragraphs': len(paragraph_openings),
                            'unique_patterns': len(paragraph_openings), 'variety_rate': 100.0},
                'score': 100.0, 'suggestions': [],
            }

        openings, pattern_frequency, pattern_counter = _build_opening_data(paragraph_openings)
        total = len(paragraph_openings)
        variety_rate = round((len(pattern_counter) / total * 100) if total > 0 else 0.0, 1)
        most_repeated = pattern_counter.most_common(1)[0][0] if pattern_counter else ''
        max_repeat = pattern_counter.most_common(1)[0][1] if pattern_counter else 0
        score = _compute_variety_score(variety_rate, max_repeat)

        return {
            'openings': openings,
            'pattern_frequency': pattern_frequency,
            'summary': {
                'total_paragraphs': total, 'unique_patterns': len(pattern_counter),
                'variety_rate': variety_rate, 'most_repeated': most_repeated,
            },
            'score': score,
            'suggestions': _generate_suggestions(
                variety_rate, pattern_frequency, most_repeated, max_repeat, total
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(
    rate: float, freq: List[Dict], most: str, max_count: int, total: int
) -> List[str]:
    suggestions = []
    if rate >= 80:
        suggestions.append('문단 시작 패턴이 다양합니다.')
    elif rate >= 50:
        suggestions.append(f'다양성 {rate}%로 양호하나 일부 반복이 있습니다.')
    else:
        suggestions.append(f'다양성 {rate}%로 낮습니다. 문단 시작을 다양하게 바꾸세요.')

    if max_count >= 3 and most:
        suggestions.append(
            f'"{most}" 패턴이 {max_count}회 반복됩니다. '
            f'질문, 인용, 통계 등 다른 시작 방식을 시도하세요.'
        )

    return suggestions
