"""
Paragraph Unity Checker 서비스

한 문단 안에 서로 다른 주제가 과도하게 섞여
중심이 흐려지는 구간을 찾습니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from collections import Counter

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')
_WORD_SPLIT = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}', re.IGNORECASE)
_PARA_SPLIT = re.compile(r'\n\s*\n')

# 주제 전환 신호
_TOPIC_SHIFT_SIGNALS = [
    re.compile(r'(?:한편|반면|그런데|그리고|또한|다른\s*한편)', re.IGNORECASE),
    re.compile(r'(?:별도로|추가로|참고로|덧붙여)', re.IGNORECASE),
    re.compile(r'\b(?:However|On\s+the\s+other\s+hand|Meanwhile|Additionally|Moreover)\b', re.IGNORECASE),
    re.compile(r'\b(?:By\s+the\s+way|Speaking\s+of|As\s+for|Regarding)\b', re.IGNORECASE),
]

# 불용어
_STOPWORDS = {'그것', '이것', '저것', '하는', '되는', '있는', '없는', '것이',
              '때문', '위해', '통해', '대한', '하다', '되다', '있다', '없다',
              'the', 'this', 'that', 'with', 'from', 'have', 'been',
              'and', 'for', 'are', 'was', 'not', 'can', 'will'}

_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'total_paragraphs': 0, 'unified_count': 0,
        'fragmented_count': 0, 'avg_coherence': 0.0, 'level': 'none',
    },
    'paragraph_details': [],
    'suggestions': [],
}


def _split_paragraphs(content: str) -> List[str]:
    """빈 줄 기준으로 문단을 분리합니다."""
    paragraphs = _PARA_SPLIT.split(content)
    result = []
    for p in paragraphs:
        text = p.strip()
        if (text and
            not text.startswith('#') and
            not text.startswith('```') and
            not text.startswith('|') and
            len(text) >= 30):
            result.append(text)
    return result


def _extract_keywords(text: str) -> Counter:
    """텍스트에서 키워드 빈도를 추출합니다."""
    words = _WORD_SPLIT.findall(text)
    return Counter(w.lower() for w in words
                   if w.lower() not in _STOPWORDS and len(w) >= 2)


def _analyze_unity(paragraph: str) -> Dict:
    """문단의 주제 통일성을 분석합니다."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(paragraph)
                 if s.strip() and len(s.strip()) >= 5]

    if len(sentences) < 3:
        return {
            'preview': paragraph[:60],
            'sentence_count': len(sentences),
            'unity': 'too_short',
            'topic_shift_count': 0,
            'coherence_score': 1.0,
        }

    # 문장별 키워드 추출
    sentence_keywords = [_extract_keywords(s) for s in sentences]

    # 인접 문장 간 키워드 겹침
    overlaps = []
    for i in range(len(sentence_keywords) - 1):
        keys_a = set(sentence_keywords[i].keys())
        keys_b = set(sentence_keywords[i + 1].keys())
        union = keys_a | keys_b
        if union:
            overlap = len(keys_a & keys_b) / len(union)
        else:
            overlap = 0.0
        overlaps.append(overlap)

    avg_coherence = sum(overlaps) / len(overlaps) if overlaps else 0

    # 주제 전환 신호 카운트
    shift_count = 0
    for s in sentences[1:]:  # 첫 문장 제외
        if any(p.match(s) for p in _TOPIC_SHIFT_SIGNALS):
            shift_count += 1

    # 통일성 판정
    if avg_coherence >= 0.15 and shift_count <= 1:
        unity = 'unified'
    elif avg_coherence >= 0.08 or shift_count <= 2:
        unity = 'mostly_unified'
    elif shift_count >= 3 or avg_coherence < 0.05:
        unity = 'fragmented'
    else:
        unity = 'mixed'

    return {
        'preview': paragraph[:60],
        'sentence_count': len(sentences),
        'unity': unity,
        'topic_shift_count': shift_count,
        'coherence_score': round(avg_coherence, 3),
    }


def _aggregate_unity_stats(details: List[Dict]) -> tuple:
    """문단 분석 결과를 집계합니다.

    Returns:
        (analyzable, unified, fragmented, avg_coherence)
    """
    analyzable = [d for d in details if d['unity'] != 'too_short']
    unified = sum(1 for d in analyzable if d['unity'] in ('unified', 'mostly_unified'))
    fragmented = sum(1 for d in analyzable if d['unity'] == 'fragmented')
    coherence_scores = [d['coherence_score'] for d in analyzable]
    avg_coherence = (sum(coherence_scores) / len(coherence_scores)
                     if coherence_scores else 0)
    return analyzable, unified, fragmented, avg_coherence


def _compute_unity_score(analyzable: List[Dict], unified: int,
                          fragmented: int, avg_coherence: float) -> tuple:
    """통일성 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if not analyzable:
        return 100.0, 'none'

    if fragmented == 0:
        level = 'unified'
    elif fragmented <= 1:
        level = 'mostly_unified'
    elif fragmented <= 3:
        level = 'mixed'
    else:
        level = 'fragmented'

    unified_ratio = unified / len(analyzable) if analyzable else 1.0
    score = (unified_ratio * 60.0) + (min(avg_coherence, 0.3) / 0.3 * 40.0)
    if fragmented > 0:
        score -= min(20.0, fragmented * 6.0)
    score = round(max(0.0, min(100.0, score)), 1)

    return score, level


def check_paragraph_unity(content: str) -> dict:
    """문단별 주제 통일성을 검사합니다.

    Returns:
        score, summary, paragraph_details, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return dict(_EMPTY_RESULT)

    details = [_analyze_unity(p) for p in paragraphs]
    analyzable, unified, fragmented, avg_coherence = _aggregate_unity_stats(details)
    score, level = _compute_unity_score(analyzable, unified, fragmented, avg_coherence)

    total = len(paragraphs)
    suggestions = _generate_suggestions(
        total, unified, fragmented, avg_coherence, level, details
    )

    return {
        'score': score,
        'summary': {
            'total_paragraphs': total, 'unified_count': unified,
            'fragmented_count': fragmented,
            'avg_coherence': round(avg_coherence, 3), 'level': level,
        },
        'paragraph_details': [d for d in details[:10]
                               if d['unity'] != 'too_short'],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, unified: int, fragmented: int,
                           avg_coherence: float, level: str,
                           details: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'unified': '통일적',
        'mostly_unified': '대부분 통일', 'mixed': '혼재',
        'fragmented': '분산됨',
    }
    suggestions.append(
        f'문단 통일성: {level_labels.get(level, level)}. '
        f'{total}개 문단, 통일 {unified}개, 분산 {fragmented}개.'
    )

    if fragmented > 0:
        suggestions.append(
            '하나의 문단에는 하나의 주제만 다루세요. '
            '주제가 바뀌면 새 문단으로 분리하세요.'
        )

    frag_details = [d for d in details if d['unity'] == 'fragmented']
    for d in frag_details[:2]:
        suggestions.append(
            f'분산 문단: "{d["preview"][:40]}..." — '
            f'주제 전환 {d["topic_shift_count"]}회, '
            f'응집도 {d["coherence_score"]:.1%}.'
        )

    return suggestions
