"""문단별 주제문 정렬 분석 (topic_sentence_alignment)."""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

_WORD_SPLIT_RE = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}', re.IGNORECASE)
_PARA_SPLIT = re.compile(r'\n\s*\n')
_SENTENCE_SPLIT_PERIOD = re.compile(r'(?<=[.!?])\s+')

_WEAK_OPENERS = [
    re.compile(r'^(?:그리고|또한|그런데|한편|아무튼|어쨌든)\s', re.IGNORECASE),
    re.compile(r'^(?:Also|And|But|So|Well|Anyway)\s', re.IGNORECASE),
    re.compile(r'^(?:그래서|따라서|그러므로|결국)\s', re.IGNORECASE),
]

_STRONG_OPENERS = [
    re.compile(r'^(?:이\s*(?:글|섹션|장)|본\s*(?:장|절))', re.IGNORECASE),
    re.compile(r'^(?:핵심|요점|중요한\s*것|주요|첫\s*번째)', re.IGNORECASE),
    re.compile(r'^(?:In\s+this\s+section|The\s+(?:main|key|primary))\b', re.IGNORECASE),
    re.compile(r'^(?:Here|This\s+(?:section|chapter|part))\b', re.IGNORECASE),
]

_TOPIC_EMPTY = {
    'score': 100.0,
    'summary': {
        'total_paragraphs': 0, 'aligned_count': 0,
        'misaligned_count': 0, 'weak_opener_count': 0, 'level': 'none',
    },
    'paragraph_details': [],
    'suggestions': [],
}


def _topic_split_paragraphs(content: str) -> List[str]:
    paragraphs = _PARA_SPLIT.split(content)
    result = []
    for p in paragraphs:
        text = p.strip()
        if (text and
            not text.startswith('#') and
            not text.startswith('-') and
            not text.startswith('*') and
            not text.startswith('```') and
            not text.startswith('|') and
            len(text) >= 20):
            result.append(text)
    return result


def _topic_get_keywords(text: str) -> set:
    words = _WORD_SPLIT_RE.findall(text)
    stopwords = {'그것', '이것', '저것', '하는', '되는', '있는', '없는',
                 'the', 'this', 'that', 'with', 'from', 'have', 'been',
                 '하다', '되다', '있다', '없다', '것이', '것을', '것은'}
    return {w.lower() for w in words if w.lower() not in stopwords}


def _topic_analyze_paragraph(paragraph: str) -> Dict:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_PERIOD.split(paragraph)
                 if s.strip() and len(s.strip()) >= 5]

    if len(sentences) < 2:
        return {
            'first_sentence': paragraph[:60],
            'sentence_count': len(sentences),
            'alignment': 'too_short',
            'has_weak_opener': False,
            'has_strong_opener': False,
            'keyword_overlap': 1.0,
        }

    first = sentences[0]
    rest = ' '.join(sentences[1:])

    first_keywords = _topic_get_keywords(first)
    rest_keywords = _topic_get_keywords(rest)

    if not first_keywords:
        overlap = 0.0
    else:
        shared = first_keywords & rest_keywords
        overlap = len(shared) / len(first_keywords) if first_keywords else 0

    has_weak = any(p.search(first) for p in _WEAK_OPENERS)
    has_strong = any(p.search(first) for p in _STRONG_OPENERS)

    if has_strong and overlap >= 0.3:
        alignment = 'strong'
    elif overlap >= 0.3:
        alignment = 'aligned'
    elif has_weak:
        alignment = 'weak'
    elif overlap < 0.1 and len(sentences) >= 3:
        alignment = 'misaligned'
    else:
        alignment = 'neutral'

    return {
        'first_sentence': first[:60],
        'sentence_count': len(sentences),
        'alignment': alignment,
        'has_weak_opener': has_weak,
        'has_strong_opener': has_strong,
        'keyword_overlap': round(overlap, 2),
    }


def _topic_aggregate(details: list) -> tuple:
    aligned = sum(1 for d in details if d['alignment'] in ('strong', 'aligned'))
    misaligned = sum(1 for d in details if d['alignment'] == 'misaligned')
    weak = sum(1 for d in details if d['has_weak_opener'])
    analyzable = [d for d in details if d['alignment'] != 'too_short']
    return aligned, misaligned, weak, analyzable


def _topic_compute_score(aligned: int, misaligned: int, weak: int,
                         analyzable: list) -> tuple:
    if not analyzable:
        return 100.0, 'none'

    if misaligned == 0 and weak == 0:
        level = 'well_aligned'
    elif misaligned <= 1 and weak <= 1:
        level = 'mostly_aligned'
    elif misaligned <= 3:
        level = 'partial'
    else:
        level = 'misaligned'

    score = (aligned / len(analyzable)) * 85.0 + 15.0
    if misaligned > 0:
        score -= min(25.0, misaligned * 8.0)
    if weak > 0:
        score -= min(10.0, weak * 3.0)
    return round(max(0.0, min(100.0, score)), 1), level


def _topic_generate_suggestions(total: int, aligned: int, misaligned: int,
                                weak: int, level: str, details: List[Dict]) -> List[str]:
    suggestions = []
    level_labels = {
        'none': '해당 없음', 'well_aligned': '잘 정렬됨',
        'mostly_aligned': '대부분 정렬', 'partial': '부분적',
        'misaligned': '불일치',
    }
    suggestions.append(
        f'주제문 정렬: {level_labels.get(level, level)}. '
        f'{total}개 문단 중 {aligned}개 정렬, {misaligned}개 불일치.'
    )
    if weak > 0:
        suggestions.append(
            '"그리고", "또한" 같은 연결어로 시작하지 말고, '
            '문단의 핵심을 첫 문장에 담으세요.'
        )
    mis_details = [d for d in details if d['alignment'] == 'misaligned']
    for d in mis_details[:2]:
        suggestions.append(
            f'불일치 문단: "{d["first_sentence"][:40]}..." — '
            f'키워드 겹침 {d["keyword_overlap"]*100:.0f}%.'
        )
    return suggestions


def analyze_topic_sentence_alignment(content: str) -> dict:
    """문단별 주제문 정렬을 분석합니다."""
    try:
        if not content or not content.strip():
            return dict(_TOPIC_EMPTY)

        paragraphs = _topic_split_paragraphs(content)
        if not paragraphs:
            return dict(_TOPIC_EMPTY)

        details = [_topic_analyze_paragraph(p) for p in paragraphs]
        aligned, misaligned, weak, analyzable = _topic_aggregate(details)
        score, level = _topic_compute_score(aligned, misaligned, weak, analyzable)

        return {
            'score': score,
            'summary': {
                'total_paragraphs': len(details),
                'aligned_count': aligned,
                'misaligned_count': misaligned,
                'weak_opener_count': weak,
                'level': level,
            },
            'paragraph_details': [d for d in details[:10]
                                   if d['alignment'] != 'too_short'],
            'suggestions': _topic_generate_suggestions(
                len(details), aligned, misaligned, weak, level, details
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
