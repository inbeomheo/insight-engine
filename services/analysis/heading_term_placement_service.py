"""
Heading Term Placement Auditor 서비스

핵심 토픽/엔터티가 H2/H3 헤딩에 적절히 배치됐는지 확인하여
주제 신호와 스캔 가능성을 점검합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List, Dict


# 마크다운 헤딩 패턴
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 불용어 (한국어)
_KO_STOPWORDS = {
    '의', '가', '이', '은', '는', '을', '를', '에', '에서', '와', '과',
    '로', '으로', '도', '만', '까지', '부터', '에게', '한테', '께',
    '대한', '위한', '통한', '관한', '및', '또는', '그리고', '하지만',
    '그러나', '그래서', '따라서', '때문에', '이런', '그런', '저런',
    '이것', '그것', '저것', '무엇', '어떤', '모든', '각', '매',
}

# 불용어 (영어)
_EN_STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'shall',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'and', 'or', 'but', 'not', 'so', 'if', 'than', 'as', 'that',
    'this', 'these', 'those', 'it', 'its', 'how', 'what', 'why',
    'when', 'where', 'who', 'which', 'your', 'you', 'we', 'our',
}

# 마크다운 서식 제거
_MD_CLEANUP = re.compile(r'[*_`\[\]()#]')


def _extract_terms(text: str) -> List[str]:
    """텍스트에서 의미 있는 용어를 추출합니다."""
    cleaned = _MD_CLEANUP.sub(' ', text)
    # 영문 단어 (한글 뒤 \b 미동작 우회)
    en_words = re.findall(r'(?<![A-Za-z])[A-Za-z]{2,}(?![A-Za-z])', cleaned)
    # 한국어 어절
    ko_words = re.findall(r'[가-힣]{2,}', cleaned)

    terms = []
    for w in en_words:
        if w.lower() not in _EN_STOPWORDS:
            terms.append(w.lower())
    for w in ko_words:
        if w not in _KO_STOPWORDS:
            terms.append(w)
    return terms


def _extract_key_terms(content: str, top_n: int = 10) -> List[str]:
    """본문에서 빈도 기반 핵심 용어를 추출합니다."""
    # 헤딩 제거한 본문
    body = _HEADING_RE.sub('', content)
    terms = _extract_terms(body)
    counter = Counter(terms)
    # 최소 2회 이상 등장하는 용어만
    return [term for term, count in counter.most_common(top_n) if count >= 2]


_EMPTY_RESULT = {
    'key_terms': [],
    'heading_analysis': [],
    'summary': {'total_headings': 0, 'terms_in_headings': 0,
                'total_key_terms': 0, 'placement_rate': 0.0},
    'score': 0.0,
    'suggestions': [],
}


def _analyze_heading_terms(headings: List[Dict], key_terms: List[str]) -> tuple:
    """각 헤딩에서 핵심 용어 매칭을 분석합니다.

    Returns:
        (heading_analysis, terms_found_set)
    """
    analysis = []
    terms_found = set()
    for h in headings:
        heading_terms = _extract_terms(h['text'])
        matched = [t for t in key_terms if t in heading_terms or t in h['text'].lower()]
        terms_found.update(matched)
        analysis.append({
            'heading': h['text'], 'level': h['level'],
            'matched_terms': matched, 'has_key_term': len(matched) > 0,
        })
    return analysis, terms_found


def audit_heading_term_placement(content: str) -> dict:
    """핵심 용어의 헤딩 배치를 점검합니다.

    Args:
        content: 분석할 마크다운 콘텐츠

    Returns:
        key_terms, heading_analysis, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    headings = [{'level': len(m.group(1)), 'text': m.group(2).strip()}
                for m in _HEADING_RE.finditer(content)]

    if not headings:
        return {**_EMPTY_RESULT, 'score': 50.0,
                'suggestions': ['헤딩이 없습니다. 마크다운 헤딩을 추가하여 구조를 개선하세요.']}

    key_terms = _extract_key_terms(content)
    if not key_terms:
        no_term_analysis = [{'heading': h['text'], 'level': h['level'],
                             'matched_terms': [], 'has_key_term': False} for h in headings]
        return {**_EMPTY_RESULT, 'heading_analysis': no_term_analysis,
                'summary': {**_EMPTY_RESULT['summary'], 'total_headings': len(headings)},
                'score': 50.0, 'suggestions': ['반복되는 핵심 용어가 없습니다. 주제를 명확히 하세요.']}

    analysis, terms_found = _analyze_heading_terms(headings, key_terms)
    terms_in_headings = len(terms_found)
    total_key_terms = len(key_terms)
    placement_rate = round((terms_in_headings / total_key_terms * 100)
                           if total_key_terms > 0 else 0.0, 1)

    return {
        'key_terms': key_terms,
        'heading_analysis': analysis,
        'summary': {'total_headings': len(headings), 'terms_in_headings': terms_in_headings,
                    'total_key_terms': total_key_terms, 'placement_rate': placement_rate},
        'score': round(min(100.0, placement_rate), 1),
        'suggestions': _generate_suggestions(key_terms, terms_found, analysis, placement_rate),
    }


def _generate_suggestions(
    key_terms: List[str], found: set,
    analysis: List[Dict], rate: float,
) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []
    missing = [t for t in key_terms if t not in found]

    if rate >= 80:
        suggestions.append('핵심 용어가 헤딩에 잘 배치되어 있습니다.')
    elif rate >= 50:
        suggestions.append(f'배치율 {rate}%로 양호하나 일부 핵심 용어가 헤딩에 누락되어 있습니다.')
    else:
        suggestions.append(f'배치율 {rate}%로 낮습니다. 핵심 용어를 헤딩에 포함하세요.')

    if missing:
        names = ', '.join(f'"{t}"' for t in missing[:5])
        suggestions.append(f'헤딩에 없는 핵심 용어: {names}. H2/H3에 포함을 고려하세요.')

    empty_headings = [a for a in analysis if not a['has_key_term']]
    if empty_headings and len(empty_headings) > len(analysis) * 0.5:
        suggestions.append('절반 이상의 헤딩에 핵심 용어가 없습니다. 헤딩을 더 구체적으로 작성하세요.')

    return suggestions
