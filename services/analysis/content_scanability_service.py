"""
Content Scanability Score 서비스

콘텐츠의 스캔 가독성(훑어보기 용이성)을 평가합니다.
헤딩, 목록, 굵은 글씨, 짧은 단락, 시각적 요소 등을 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
_BOLD_RE = re.compile(r'\*\*[^*]+\*\*|__[^_]+__')
_LIST_RE = re.compile(r'^\s*[-*+]\s+.+$|^\s*\d+\.\s+.+$', re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```')
_IMAGE_RE = re.compile(r'!\[.*?\]\(.*?\)')
_TABLE_RE = re.compile(r'^\|.+\|$', re.MULTILINE)
_PARAGRAPH_SPLIT = re.compile(r'\n\s*\n')
_BLOCKQUOTE_RE = re.compile(r'^\s*>\s+.+$', re.MULTILINE)


def _detect_elements(content: str) -> Dict:
    """콘텐츠에서 스캔 가독성 요소를 감지합니다."""
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(content) if p.strip()]
    total_paras = max(len(paragraphs), 1)
    short_paras = sum(1 for p in paragraphs if len(p.split()) <= 50)

    return {
        'headings': len(_HEADING_RE.findall(content)),
        'bold_texts': len(_BOLD_RE.findall(content)),
        'list_items': len(_LIST_RE.findall(content)),
        'code_blocks': len(_CODE_BLOCK_RE.findall(content)),
        'images': len(_IMAGE_RE.findall(content)),
        'tables': len(_TABLE_RE.findall(content)),
        'blockquotes': len(_BLOCKQUOTE_RE.findall(content)),
        'short_paragraphs': short_paras,
        'total_paragraphs': total_paras,
    }


def _compute_scanability_score(elements: Dict, word_count: int) -> tuple:
    """요소 기반으로 스캔 가독성 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    short_para_ratio = elements['short_paragraphs'] / max(elements['total_paragraphs'], 1) * 100
    expected_headings = max(1, word_count // 200)

    score = min(25.0, (elements['headings'] / max(expected_headings, 1)) * 25.0)
    if elements['list_items'] > 0:
        score += min(20.0, elements['list_items'] * 4.0)
    if elements['bold_texts'] > 0:
        score += min(15.0, elements['bold_texts'] * 3.0)
    score += min(20.0, short_para_ratio * 0.3)
    visual = elements['images'] + elements['tables'] + elements['code_blocks']
    if visual > 0:
        score += min(10.0, visual * 5.0)
    if elements['blockquotes'] > 0:
        score += min(10.0, elements['blockquotes'] * 3.0)

    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 70:
        level = 'excellent'
    elif score >= 50:
        level = 'good'
    elif score >= 30:
        level = 'fair'
    else:
        level = 'poor'

    return score, level


_ZERO_ELEMENTS = {
    'headings': 0, 'bold_texts': 0, 'list_items': 0,
    'code_blocks': 0, 'images': 0, 'tables': 0,
    'blockquotes': 0, 'short_paragraphs': 0, 'total_paragraphs': 0,
}


def score_content_scanability(content: str) -> dict:
    """콘텐츠의 스캔 가독성을 평가합니다.

    Returns:
        elements, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {
                'elements': {}, 'score': 0.0,
                'summary': {'total_elements': 0, 'scanability_score': 0.0, 'level': 'none'},
                'suggestions': ['콘텐츠가 비어 있습니다.'],
            }

        word_count = len(content.split())
        if word_count < 10:
            return {
                'elements': dict(_ZERO_ELEMENTS), 'score': 50.0,
                'summary': {'total_elements': 0, 'scanability_score': 0.0, 'level': 'none'},
                'suggestions': [],
            }

        elements = _detect_elements(content)
        total_elements = sum(elements[k] for k in ('headings', 'bold_texts', 'list_items',
                                                     'code_blocks', 'images', 'tables', 'blockquotes'))
        score, level = _compute_scanability_score(elements, word_count)
        suggestions = _generate_suggestions(elements, score, level, word_count)

        return {
            'elements': elements,
            'summary': {'total_elements': total_elements, 'scanability_score': score, 'level': level},
            'score': score,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(elements: Dict, score: float,
                           level: str, word_count: int) -> List[str]:
    suggestions = []
    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡',
    }

    suggestions.append(
        f'스캔 가독성 {score}점 ({level_labels.get(level, level)}). '
        f'헤딩 {elements["headings"]}개, 목록 {elements["list_items"]}개, '
        f'강조 {elements["bold_texts"]}개.'
    )

    if elements['headings'] == 0:
        suggestions.append('헤딩(H1~H6)을 추가하여 구조를 명확히 하세요.')

    if elements['list_items'] == 0 and word_count > 200:
        suggestions.append('목록(bullet/numbered)을 활용하면 스캔하기 쉬워집니다.')

    if elements['bold_texts'] == 0 and word_count > 100:
        suggestions.append('핵심 포인트를 **굵은 글씨**로 강조하세요.')

    short_ratio = elements['short_paragraphs'] / max(elements['total_paragraphs'], 1)
    if short_ratio < 0.4 and word_count > 200:
        suggestions.append('단락이 길어 스캔이 어렵습니다. 3-5 문장 단위로 나누세요.')

    return suggestions
