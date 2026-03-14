"""
Content Symmetry Analyzer 서비스

콘텐츠의 구조적 대칭성을 분석합니다.
섹션 간 길이 균형, 도입-본문-결론 비율, 단락 크기 편차를 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
import math
from typing import List, Dict

_HEADING_RE = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
_SECTION_SPLIT_RE = re.compile(r'^#{1,3}\s+', re.MULTILINE)


def _split_sections(content: str) -> List[Dict]:
    """콘텐츠를 섹션별로 분할합니다."""
    lines = content.split('\n')
    sections = []
    current_title = '(서론)'
    current_lines = []

    for line in lines:
        if re.match(r'^#{1,3}\s+', line):
            if current_lines:
                text = '\n'.join(current_lines).strip()
                if text:
                    sections.append({
                        'title': current_title,
                        'text': text,
                        'word_count': len(text.split()),
                        'char_count': len(text),
                    })
            current_title = re.sub(r'^#{1,3}\s+', '', line).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        text = '\n'.join(current_lines).strip()
        if text:
            sections.append({
                'title': current_title,
                'text': text,
                'word_count': len(text.split()),
                'char_count': len(text),
            })

    return sections


def _calc_std_dev(values: List[float]) -> float:
    """표준편차를 계산합니다."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _calc_cv(values: List[float]) -> float:
    """변동계수 (CV)를 계산합니다. 0에 가까울수록 균일."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    std = _calc_std_dev(values)
    return round(std / mean, 3)


_EMPTY_RESULT = {
    'sections': [],
    'balance': {},
    'summary': {
        'total_sections': 0, 'symmetry_score': 0.0,
        'cv': 0.0, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _compute_balance(sections: List[Dict]) -> tuple:
    """섹션별 비율과 밸런스 정보를 계산합니다.

    Returns:
        (section_data, balance, cv)
    """
    word_counts = [s['word_count'] for s in sections]
    total_words = sum(word_counts)
    mean_words = total_words / len(sections)
    cv = _calc_cv([float(w) for w in word_counts])

    section_data = []
    for s in sections:
        ratio = round(s['word_count'] / max(total_words, 1) * 100, 1)
        section_data.append({
            'title': s['title'] if len(s['title']) <= 30 else s['title'][:27] + '...',
            'word_count': s['word_count'],
            'ratio': ratio,
        })

    balance = {
        'mean_words': round(mean_words, 1),
        'min_words': min(word_counts),
        'max_words': max(word_counts),
        'range_ratio': round(max(word_counts) / max(min(word_counts), 1), 1),
        'cv': cv,
    }

    return section_data, balance, cv


def _compute_symmetry_score(cv: float) -> tuple:
    """변동계수로 대칭성 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if cv <= 0.3:
        level = 'symmetric'
        score = 100.0
    elif cv <= 0.5:
        level = 'moderate'
        score = 100.0 - (cv - 0.3) * 100.0
    elif cv <= 0.8:
        level = 'asymmetric'
        score = 80.0 - (cv - 0.5) * 60.0
    else:
        level = 'very_asymmetric'
        score = max(0.0, 50.0 - (cv - 1.0) * 30.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_content_symmetry(content: str) -> dict:
    """콘텐츠의 구조적 대칭성을 분석합니다.

    Returns:
        sections, balance, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sections = _split_sections(content)

    if len(sections) < 2:
        return {
            'sections': [{'title': s['title'],
                          'word_count': s['word_count'],
                          'char_count': s['char_count']} for s in sections],
            'balance': {},
            'summary': {
                'total_sections': len(sections), 'symmetry_score': 0.0,
                'cv': 0.0, 'level': 'single',
            },
            'score': 50.0,
            'suggestions': ['섹션이 1개뿐입니다. 구조적 분석을 위해 헤딩으로 섹션을 나누세요.'],
        }

    section_data, balance, cv = _compute_balance(sections)
    score, level = _compute_symmetry_score(cv)

    suggestions = _generate_suggestions(
        cv, level, section_data, balance['min_words'], balance['max_words'],
        balance['mean_words']
    )

    return {
        'sections': section_data[:20],
        'balance': balance,
        'summary': {
            'total_sections': len(sections),
            'symmetry_score': round(100.0 - cv * 100.0, 1) if cv <= 1.0 else 0.0,
            'cv': cv,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(cv: float, level: str,
                           sections: List[Dict], shortest: int,
                           longest: int, mean: float) -> List[str]:
    suggestions = []
    level_labels = {
        'symmetric': '대칭적', 'moderate': '보통',
        'asymmetric': '비대칭', 'very_asymmetric': '매우 비대칭',
        'single': '단일 섹션', 'none': '없음',
    }
    suggestions.append(
        f'구조 대칭성: {level_labels.get(level, level)} '
        f'(변동계수 {cv:.2f}). '
        f'섹션 {len(sections)}개, 평균 {mean:.0f} 단어.'
    )

    if level in ('asymmetric', 'very_asymmetric'):
        # 가장 짧은/긴 섹션 찾기
        short_sections = [s for s in sections if s['word_count'] == shortest]
        long_sections = [s for s in sections if s['word_count'] == longest]

        if short_sections:
            suggestions.append(
                f'가장 짧은 섹션 "{short_sections[0]["title"]}" ({shortest} 단어): '
                f'내용을 보강하세요.'
            )
        if long_sections:
            suggestions.append(
                f'가장 긴 섹션 "{long_sections[0]["title"]}" ({longest} 단어): '
                f'하위 섹션으로 분할을 고려하세요.'
            )

    return suggestions
