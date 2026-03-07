"""
Parenthetical Overuse Checker 서비스

콘텐츠에서 괄호 표현의 과다 사용을 감지합니다.
과도한 괄호는 가독성을 저하시키고 독자의 흐름을 방해합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 괄호 패턴
_PAREN_RE = re.compile(r'\(([^)]+)\)')
_BRACKET_RE = re.compile(r'\[([^\]]+)\]')  # 마크다운 링크 제외
_MD_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)')  # 마크다운 링크

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 긴 괄호 임계값
_LONG_PAREN_THRESHOLD = 30


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def check_parenthetical_overuse(content: str) -> dict:
    """괄호 과다 사용을 점검합니다.

    Returns:
        parentheticals, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'parentheticals': [],
            'summary': {'total_parentheticals': 0, 'total_sentences': 0,
                        'paren_ratio': 0.0, 'long_parens': 0, 'nested_parens': 0},
            'score': 100.0,
            'suggestions': [],
        }

    # 마크다운 링크 제거 (괄호 오탐 방지)
    clean_content = _MD_LINK_RE.sub('LINK', content)

    sentences = _split_sentences(content)
    total_sentences = len(sentences)

    # 괄호 추출
    parentheticals = []
    for match in _PAREN_RE.finditer(clean_content):
        text = match.group(1).strip()
        if len(text) >= 2:  # 최소 2자
            is_long = len(text) > _LONG_PAREN_THRESHOLD
            parentheticals.append({
                'text': text if len(text) <= 60 else text[:57] + '...',
                'length': len(text),
                'is_long': is_long,
            })

    total_parens = len(parentheticals)
    long_parens = sum(1 for p in parentheticals if p['is_long'])

    # 중첩 괄호 감지
    nested = len(re.findall(r'\([^)]*\([^)]*\)[^)]*\)', clean_content))

    # 비율
    paren_ratio = round((total_parens / total_sentences * 100) if total_sentences > 0 else 0.0, 1)

    # 점수: 비율 기반 (적정: 문장당 0-20%)
    if paren_ratio <= 15:
        score = 100.0
    elif paren_ratio <= 30:
        score = 100.0 - (paren_ratio - 15) * 2.0
    elif paren_ratio <= 50:
        score = 70.0 - (paren_ratio - 30) * 1.5
    else:
        score = max(0.0, 40.0 - (paren_ratio - 50) * 1.0)

    # 긴 괄호 페널티
    score = max(0.0, score - long_parens * 5.0)
    # 중첩 괄호 페널티
    score = max(0.0, score - nested * 10.0)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(total_parens, paren_ratio, long_parens, nested)

    return {
        'parentheticals': parentheticals,
        'summary': {
            'total_parentheticals': total_parens,
            'total_sentences': total_sentences,
            'paren_ratio': paren_ratio,
            'long_parens': long_parens,
            'nested_parens': nested,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, ratio: float, long: int, nested: int) -> List[str]:
    suggestions = []
    if total == 0:
        suggestions.append('괄호 사용이 없습니다. 필요 시 보충 설명에 활용하세요.')
        return suggestions

    if ratio > 30:
        suggestions.append(
            f'괄호 비율 {ratio}%로 과다합니다 (적정: 15% 이하). '
            f'괄호 내용을 본문에 통합하거나 삭제하세요.'
        )
    elif ratio > 15:
        suggestions.append(f'괄호 비율 {ratio}%로 다소 높습니다.')
    else:
        suggestions.append(f'괄호 사용 비율 {ratio}%로 적정합니다.')

    if long > 0:
        suggestions.append(
            f'긴 괄호({_LONG_PAREN_THRESHOLD}자 초과) {long}개: '
            f'별도 문장이나 각주로 분리하세요.'
        )
    if nested > 0:
        suggestions.append(f'중첩 괄호 {nested}개: 가독성을 위해 풀어서 작성하세요.')
    return suggestions
