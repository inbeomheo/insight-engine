"""
Quotation Usage Analyzer 서비스

콘텐츠에서 인용문/따옴표 사용 패턴을 분석합니다.
직접 인용, 간접 인용, 강조 따옴표의 빈도와 적절성을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List
import logging

logger = logging.getLogger(__name__)

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


_EMPTY_RESULT = {
    'quotations': [],
    'summary': {
        'total_quotes': 0, 'direct_quotes': 0, 'emphasis_quotes': 0,
        'block_quotes': 0, 'with_attribution': 0, 'level': 'none',
    },
    'score': 50.0,
    'suggestions': [],
}


def _collect_quotations(cleaned: str, raw_content: str) -> tuple:
    """텍스트에서 인용문을 수집하고 유형별 카운트를 반환합니다.

    Returns:
        (quotations, direct_quotes, emphasis_quotes, block_quotes)
    """
    quotations = []
    direct_quotes = 0
    emphasis_quotes = 0

    def _truncate(text: str) -> str:
        return text if len(text) <= 60 else text[:57] + '...'

    for match in _DOUBLE_QUOTE.finditer(cleaned):
        text = match.group(1)
        if len(text.split()) >= 5:
            direct_quotes += 1
            quotations.append({'text': _truncate(text), 'type': 'direct'})
        else:
            emphasis_quotes += 1
            quotations.append({'text': _truncate(text), 'type': 'emphasis'})

    for match in _SINGLE_QUOTE.finditer(cleaned):
        text = match.group(1)
        emphasis_quotes += 1
        quotations.append({'text': _truncate(text), 'type': 'emphasis'})

    for match in _KO_QUOTE.finditer(cleaned):
        text = match.group(1) or match.group(2)
        if text:
            direct_quotes += 1
            quotations.append({'text': _truncate(text), 'type': 'direct'})

    block_matches = _BLOCKQUOTE.findall(raw_content)
    block_quotes = len(block_matches)
    for bq in block_matches[:5]:
        quotations.append({'text': bq.strip()[:60], 'type': 'block'})

    return quotations, direct_quotes, emphasis_quotes, block_quotes


def _calculate_score(direct: int, emphasis: int, block: int, attribution: int) -> tuple:
    """인용 카운트로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    total = direct + emphasis + block

    if total == 0:
        level = 'none'
    elif total <= 3:
        level = 'minimal'
    elif total <= 8:
        level = 'moderate'
    else:
        level = 'heavy'

    if total == 0:
        score = 50.0
    elif 2 <= total <= 8:
        score = 90.0
        if attribution > 0:
            score += 10.0
    elif total == 1:
        score = 70.0
    else:
        score = max(40.0, 90.0 - (total - 8) * 5.0)

    if emphasis > 10:
        score -= min(20.0, (emphasis - 10) * 3.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_quotation_usage(content: str) -> dict:
    """인용문 사용 패턴을 분석합니다.

    Returns:
        quotations, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        cleaned = _HEADING_RE.sub('', content)
        quotations, direct, emphasis, block = _collect_quotations(cleaned, content)
        attribution = len(_ATTRIBUTION.findall(cleaned))
        total = direct + emphasis + block
        score, level = _calculate_score(direct, emphasis, block, attribution)
        suggestions = _generate_suggestions(direct, emphasis, block, attribution, total, level)

        return {
            'quotations': quotations[:20],
            'summary': {
                'total_quotes': total, 'direct_quotes': direct,
                'emphasis_quotes': emphasis, 'block_quotes': block,
                'with_attribution': attribution, 'level': level,
            },
            'score': score,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


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
