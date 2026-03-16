"""
Thesis Frontload Checker 서비스

핵심 주장/결론이 콘텐츠 도입부(첫 20%)에 배치됐는지 점검합니다.
역피라미드 구조를 권장합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


# ── 핵심 주장/결론 신호 패턴 ──
_THESIS_PATTERNS_KO = [
    re.compile(r'핵심은\s'),
    re.compile(r'결론(?:은|적으로)'),
    re.compile(r'요약하(?:면|자면)'),
    re.compile(r'가장\s+중요한'),
    re.compile(r'본\s*(?:글|문서|기사)(?:에서는|의\s*핵심|의\s*목적)'),
    re.compile(r'(?:이|가)\s*(?:핵심|요점|결론)'),
    re.compile(r'한마디로'),
    re.compile(r'즉[,\s]'),
    re.compile(r'다시\s*말해'),
    re.compile(r'명확(?:하게|히)\s'),
]

_THESIS_PATTERNS_EN = [
    re.compile(r'\bthe\s+key\s+(?:point|takeaway|finding)\b', re.IGNORECASE),
    re.compile(r'\bin\s+(?:conclusion|summary|short)\b', re.IGNORECASE),
    re.compile(r'\bthe\s+(?:main|primary|central)\s+(?:point|argument|thesis)\b', re.IGNORECASE),
    re.compile(r'\bmost\s+important(?:ly)?\b', re.IGNORECASE),
    re.compile(r'\bthis\s+(?:article|post|guide)\s+(?:shows|explains|covers)\b', re.IGNORECASE),
    re.compile(r'\bbottom\s+line\b', re.IGNORECASE),
    re.compile(r'\btl;?\s*dr\b', re.IGNORECASE),
]

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _is_thesis_signal(sentence: str) -> bool:
    for p in _THESIS_PATTERNS_KO + _THESIS_PATTERNS_EN:
        if p.search(sentence):
            return True
    return False


_EMPTY_RESULT = {
    'thesis_sentences': [],
    'position_analysis': {'frontloaded': 0, 'mid_section': 0, 'back_loaded': 0},
    'summary': {'total_thesis': 0, 'frontload_rate': 0.0},
    'score': 100.0,
    'suggestions': [],
}


def _scan_thesis_positions(sentences: List[str]) -> tuple:
    """문장에서 핵심 주장 신호를 찾고 위치를 분류합니다.

    Returns:
        (thesis_sentences, frontloaded, mid_section, back_loaded)
    """
    total = len(sentences)
    front_boundary = max(1, int(total * 0.2))
    mid_boundary = max(1, int(total * 0.6))

    thesis_sentences = []
    frontloaded = 0
    mid_section = 0
    back_loaded = 0

    for i, sentence in enumerate(sentences):
        if _is_thesis_signal(sentence):
            if i < front_boundary:
                position = 'front'
                frontloaded += 1
            elif i < mid_boundary:
                position = 'middle'
                mid_section += 1
            else:
                position = 'back'
                back_loaded += 1

            thesis_sentences.append({
                'text': sentence if len(sentence) <= 150 else sentence[:147] + '...',
                'position': position,
                'sentence_index': i,
                'relative_position': round(i / total * 100, 1),
            })

    return thesis_sentences, frontloaded, mid_section, back_loaded


def check_thesis_frontload(content: str) -> dict:
    """핵심 주장이 도입부에 배치됐는지 점검합니다.

    Returns:
        thesis_sentences, position_analysis, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        sentences = _split_sentences(content)
        if not sentences:
            return dict(_EMPTY_RESULT)

        thesis_sentences, frontloaded, mid_section, back_loaded = \
            _scan_thesis_positions(sentences)

        total_thesis = len(thesis_sentences)
        frontload_rate = round((frontloaded / total_thesis * 100) if total_thesis > 0 else 0.0, 1)
        score = 50.0 if total_thesis == 0 else round(min(100.0, frontload_rate), 1)

        return {
            'thesis_sentences': thesis_sentences,
            'position_analysis': {
                'frontloaded': frontloaded,
                'mid_section': mid_section,
                'back_loaded': back_loaded,
            },
            'summary': {
                'total_thesis': total_thesis,
                'frontload_rate': frontload_rate,
            },
            'score': score,
            'suggestions': _generate_suggestions(thesis_sentences, total_thesis,
                                                  frontloaded, back_loaded, frontload_rate),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(
    thesis: List[Dict], total: int, front: int, back: int, rate: float
) -> List[str]:
    suggestions = []

    if total == 0:
        suggestions.append('핵심 주장 신호가 감지되지 않았습니다. "핵심은~", "결론적으로~" 등 명확한 주장 문장을 추가하세요.')
        return suggestions

    if rate >= 80:
        suggestions.append('핵심 주장이 도입부에 잘 배치되어 있습니다 (역피라미드 구조).')
    elif rate >= 50:
        suggestions.append(f'프론트로드 비율 {rate}%입니다. 핵심 주장을 더 앞으로 이동하면 좋습니다.')
    else:
        suggestions.append(f'프론트로드 비율 {rate}%로 낮습니다. 핵심 주장을 첫 문단에 배치하세요.')

    if back > 0:
        suggestions.append(f'뒷부분에 핵심 주장 {back}개가 있습니다. 도입부에 요약을 추가하거나 앞으로 이동하세요.')

    return suggestions
