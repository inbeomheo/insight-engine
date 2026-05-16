"""
용어집(Glossary) 추출 서비스

콘텐츠에서 전문 용어와 그 정의를 규칙 기반으로 추출합니다.
"A란 B이다", "A(B)", "A: B" 같은 정의 패턴을 감지합니다.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 정의 패턴 (한국어)
_DEFINITION_PATTERNS = [
    # "A란 B이다/입니다"
    re.compile(r'([가-힣A-Za-z]{2,20})(?:이)?란\s+(.{10,100}?)(?:[.!?]|$)'),
    # "A은/는 B을/를 의미한다/말한다"
    re.compile(r'([가-힣A-Za-z]{2,20})(?:은|는)\s+(.{10,80}?)(?:을|를)\s*(?:의미|뜻)'),
    # "A(B)" — 괄호 안 설명
    re.compile(r'([가-힣]{2,15})\(([A-Za-z\s]{2,40})\)'),
    # "A(B)" — 영문 용어(한국어 설명)
    re.compile(r'([A-Za-z]{2,30})\(([가-힣\s]{2,40})\)'),
    # "A: B" 형태 (리스트에서)
    re.compile(r'^\s*[-*•]\s*\*?\*?([가-힣A-Za-z\s]{2,25})\*?\*?\s*[:：]\s+(.{10,100})', re.MULTILINE),
]

# 볼드+설명 패턴: **용어** — 설명
_BOLD_DEF_PATTERN = re.compile(
    r'\*\*([가-힣A-Za-z\s]{2,25})\*\*\s*[-—:：]\s*(.{10,100}?)(?:[.!?]|$)'
)

# 약어 패턴: AI(Artificial Intelligence)
_ACRONYM_PATTERN = re.compile(r'\b([A-Z]{2,8})\s*\(([A-Za-z\s]{5,60})\)')


def extract_glossary(content: str) -> dict:
    """콘텐츠에서 용어집을 추출합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            'terms': [{'term': str, 'definition': str, 'pattern': str}],
            'acronyms': [{'acronym': str, 'expansion': str}],
            'total': int,
        }
    """
    if not content or not content.strip():
        return {'terms': [], 'acronyms': [], 'total': 0}

    text = content.strip()
    terms = []
    seen_terms = set()

    # 정의 패턴 매칭
    for pattern in _DEFINITION_PATTERNS:
        for match in pattern.finditer(text):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            term_key = term.lower()
            if term_key not in seen_terms and len(term) >= 2:
                seen_terms.add(term_key)
                terms.append({
                    'term': term,
                    'definition': _clean_definition(definition),
                    'pattern': 'definition',
                })

    # 볼드 정의 패턴
    for match in _BOLD_DEF_PATTERN.finditer(text):
        term = match.group(1).strip()
        definition = match.group(2).strip()
        term_key = term.lower()
        if term_key not in seen_terms and len(term) >= 2:
            seen_terms.add(term_key)
            terms.append({
                'term': term,
                'definition': _clean_definition(definition),
                'pattern': 'bold',
            })

    # 약어 추출
    acronyms = []
    seen_acronyms = set()
    for match in _ACRONYM_PATTERN.finditer(text):
        acronym = match.group(1)
        expansion = match.group(2).strip()
        if acronym not in seen_acronyms:
            seen_acronyms.add(acronym)
            acronyms.append({
                'acronym': acronym,
                'expansion': expansion,
            })

    return {
        'terms': terms,
        'acronyms': acronyms,
        'total': len(terms) + len(acronyms),
    }


def _clean_definition(text: str) -> str:
    """정의 텍스트를 정리합니다."""
    cleaned = text.strip()
    # 끝 마크다운 제거
    cleaned = re.sub(r'\*+$', '', cleaned)
    # 괄호 닫기 누락 보정
    if cleaned.count('(') > cleaned.count(')'):
        cleaned += ')'
    return cleaned.strip()
