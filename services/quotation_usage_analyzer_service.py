"""
Quotation Usage Analyzer 서비스

콘텐츠에서 인용문/따옴표 사용 패턴을 분석합니다.
직접 인용, 간접 인용, 강조 따옴표의 빈도와 적절성을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 큰따옴표 인용 (한국어/영어)
_DOUBLE_QUOTE = re.compile(r'["""]([^"""]{3,200})["""]')

# 작은따옴표 강조
_SINGLE_QUOTE = re.compile(r"[''']([^''']{2,50})[''']")

# 한국어 겹따옴표
_KO_QUOTE = re.compile(r'「([^」]{3,200})」|『([^』]{3,200})』')

# 인용 출처 패턴 (인용문 뒤 출처 표시)
_ATTRIBUTION = re.compile(
    r'(?:라고|하고|라며|고\s+말|에\s+따르면|의\s+말|said|according\s+to|noted|stated)',
    re.IGNORECASE | re.UNICODE
)

# 블록 인용 (마크다운)
_BLOCKQUOTE = re.compile(r'^\s*>\s+(.+)$', re.MULTILINE)


def analyze_quotation_usage(content: str) -> dict:
    """인용문 사용 패턴을 분석합니다.

    Returns:
        quotations, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'quotations': [],
            'summary': {
                'total_quotes': 0,
                'direct_quotes': 0,
                'emphasis_quotes': 0,
                'block_quotes': 0,
                'with_attribution': 0,
                'level': 'none',
            },
            'score': 50.0,
            'suggestions': [],
        }

    cleaned = _HEADING_RE.sub('', content)
    word_count = len(cleaned.split())

    quotations = []

    # 큰따옴표 (직접 인용 또는 강조)
    direct_quotes = 0
    emphasis_quotes = 0

    for match in _DOUBLE_QUOTE.finditer(cleaned):
        text = match.group(1)
        # 10단어 이상이면 직접 인용으로 분류
        if len(text.split()) >= 5:
            q_type = 'direct'
            direct_quotes += 1
        else:
            q_type = 'emphasis'
            emphasis_quotes += 1
        quotations.append({
            'text': text if len(text) <= 60 else text[:57] + '...',
            'type': q_type,
        })

    # 작은따옴표 (강조)
    for match in _SINGLE_QUOTE.finditer(cleaned):
        text = match.group(1)
        emphasis_quotes += 1
        quotations.append({
            'text': text if len(text) <= 60 else text[:57] + '...',
            'type': 'emphasis',
        })

    # 한국어 겹따옴표
    for match in _KO_QUOTE.finditer(cleaned):
        text = match.group(1) or match.group(2)
        if text:
            direct_quotes += 1
            quotations.append({
                'text': text if len(text) <= 60 else text[:57] + '...',
                'type': 'direct',
            })

    # 블록 인용
    block_matches = _BLOCKQUOTE.findall(content)
    block_quotes = len(block_matches)
    for bq in block_matches[:5]:
        quotations.append({
            'text': bq.strip()[:60],
            'type': 'block',
        })

    # 출처 표시 여부
    attribution_count = len(_ATTRIBUTION.findall(cleaned))

    total = direct_quotes + emphasis_quotes + block_quotes

    # 레벨
    if total == 0:
        level = 'none'
    elif total <= 3:
        level = 'minimal'
    elif total <= 8:
        level = 'moderate'
    else:
        level = 'heavy'

    # 점수 (적절한 인용 사용이 좋음)
    if total == 0:
        score = 50.0  # 중립
    elif 2 <= total <= 8:
        score = 90.0
        # 출처 있으면 보너스
        if attribution_count > 0:
            score += 10.0
    elif total == 1:
        score = 70.0
    else:
        score = max(40.0, 90.0 - (total - 8) * 5.0)

    # 강조 따옴표 과다 감점
    if emphasis_quotes > 10:
        score -= min(20.0, (emphasis_quotes - 10) * 3.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        direct_quotes, emphasis_quotes, block_quotes,
        attribution_count, total, level
    )

    return {
        'quotations': quotations[:20],
        'summary': {
            'total_quotes': total,
            'direct_quotes': direct_quotes,
            'emphasis_quotes': emphasis_quotes,
            'block_quotes': block_quotes,
            'with_attribution': attribution_count,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(direct: int, emphasis: int, block: int,
                           attr: int, total: int, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'none': '없음', 'minimal': '최소',
        'moderate': '적정', 'heavy': '과다',
    }

    suggestions.append(
        f'인용 {total}개 ({level_labels.get(level, level)}): '
        f'직접 {direct}, 강조 {emphasis}, 블록 {block}.'
    )

    if level == 'none':
        suggestions.append(
            '인용문이 없습니다. 전문가 의견이나 데이터를 인용하면 신뢰도가 높아집니다.'
        )

    if direct > 0 and attr == 0:
        suggestions.append(
            '직접 인용에 출처가 없습니다. "~라고 OOO이 말했다" 형식으로 출처를 밝히세요.'
        )

    if emphasis > 10:
        suggestions.append(
            f'강조 따옴표가 {emphasis}개로 많습니다. 꼭 필요한 곳에만 사용하세요.'
        )

    return suggestions
