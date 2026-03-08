"""
Adjacent Paragraph Cohesion Analyzer 서비스

인접 문단 사이의 엔티티·키워드 연결이 약해
읽는 흐름이 끊기는 지점을 표시합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_WORD_SPLIT = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}', re.IGNORECASE)

# 불용어
_STOPWORDS = {'그것', '이것', '저것', '하는', '되는', '있는', '없는', '것이',
              '때문', '위해', '통해', '대한', '하다', '되다', '있다', '없다',
              '수도', '같은', '이런', '그런', '저런', '아주', '매우', '정말',
              'the', 'this', 'that', 'with', 'from', 'have', 'been',
              'and', 'for', 'are', 'was', 'not', 'can', 'will', 'also',
              'but', 'when', 'how', 'what', 'which', 'where', 'who'}

# 전환어 (있으면 응집 보너스)
_TRANSITION_PATTERNS = [
    re.compile(r'^(?:따라서|그래서|그러므로|이처럼|이렇게|마찬가지로)', re.IGNORECASE),
    re.compile(r'^(?:또한|게다가|더불어|나아가|아울러)', re.IGNORECASE),
    re.compile(r'^(?:반면|하지만|그러나|그렇지만|다만)', re.IGNORECASE),
    re.compile(r'^(?:예를\s*들어|구체적으로|특히|즉)', re.IGNORECASE),
    re.compile(r'^\b(?:Therefore|Thus|Similarly|Furthermore|However|Moreover)\b', re.IGNORECASE),
    re.compile(r'^\b(?:For\s+example|In\s+contrast|Additionally|Specifically)\b', re.IGNORECASE),
]


def _split_paragraphs(content: str) -> List[str]:
    """빈 줄 기준으로 문단을 분리합니다."""
    paragraphs = re.split(r'\n\s*\n', content)
    result = []
    for p in paragraphs:
        text = p.strip()
        if (text and
            not text.startswith('#') and
            not text.startswith('```') and
            not text.startswith('|') and
            not text.startswith('-') and
            len(text) >= 20):
            result.append(text)
    return result


def _extract_keywords(text: str) -> set:
    """키워드를 추출합니다."""
    words = _WORD_SPLIT.findall(text)
    return {w.lower() for w in words
            if w.lower() not in _STOPWORDS and len(w) >= 2}


def _has_transition(text: str) -> bool:
    """문단 시작에 전환어가 있는지 확인합니다."""
    first_line = text.split('\n')[0].strip()
    return any(p.search(first_line) for p in _TRANSITION_PATTERNS)


def _calc_pair_cohesion(para_a: str, para_b: str) -> Dict:
    """인접 두 문단의 응집도를 계산합니다."""
    keywords_a = _extract_keywords(para_a)
    keywords_b = _extract_keywords(para_b)

    union = keywords_a | keywords_b
    if not union:
        overlap = 0.0
    else:
        shared = keywords_a & keywords_b
        overlap = len(shared) / len(union)

    has_trans = _has_transition(para_b)

    # 전환어가 있으면 응집 보너스
    effective_cohesion = overlap
    if has_trans:
        effective_cohesion = min(1.0, overlap + 0.1)

    return {
        'overlap': round(overlap, 3),
        'has_transition': has_trans,
        'effective_cohesion': round(effective_cohesion, 3),
        'shared_keywords': list((keywords_a & keywords_b))[:5],
    }


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'total_pairs': 0, 'weak_pairs': 0,
        'avg_cohesion': 0.0, 'level': 'none',
    },
    'pair_details': [],
    'suggestions': [],
}


def _analyze_pairs(paragraphs: List[str]) -> tuple:
    """인접 문단 쌍의 응집도를 분석합니다.

    Returns:
        (pair_details, weak_count)
    """
    pair_details = []
    weak_count = 0

    for i in range(len(paragraphs) - 1):
        cohesion = _calc_pair_cohesion(paragraphs[i], paragraphs[i + 1])
        is_weak = cohesion['effective_cohesion'] < 0.05

        pair_details.append({
            'pair_index': i,
            'para_a_preview': paragraphs[i][:40],
            'para_b_preview': paragraphs[i + 1][:40],
            'is_weak': is_weak,
            **cohesion,
        })

        if is_weak:
            weak_count += 1

    return pair_details, weak_count


def _compute_cohesion_score(pair_details: list, weak_count: int) -> tuple:
    """응집도 점수와 레벨을 계산합니다.

    Returns:
        (score, level, avg_cohesion)
    """
    total_pairs = len(pair_details)
    cohesion_values = [p['effective_cohesion'] for p in pair_details]
    avg_cohesion = sum(cohesion_values) / len(cohesion_values) if cohesion_values else 0

    if weak_count == 0:
        level = 'cohesive'
    elif weak_count / total_pairs <= 0.2:
        level = 'mostly_cohesive'
    elif weak_count / total_pairs <= 0.5:
        level = 'mixed'
    else:
        level = 'fragmented'

    weak_ratio = weak_count / total_pairs if total_pairs > 0 else 0
    score = (avg_cohesion * 70.0) + ((1.0 - weak_ratio) * 30.0)

    return round(max(0.0, min(100.0, score)), 1), level, round(avg_cohesion, 3)


def analyze_adjacent_cohesion(content: str) -> dict:
    """인접 문단 간 응집도를 분석합니다.

    Returns:
        score, summary, pair_details, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    paragraphs = _split_paragraphs(content)
    if len(paragraphs) < 2:
        return dict(_EMPTY_RESULT)

    pair_details, weak_count = _analyze_pairs(paragraphs)
    score, level, avg_cohesion = _compute_cohesion_score(pair_details, weak_count)

    return {
        'score': score,
        'summary': {
            'total_pairs': len(pair_details),
            'weak_pairs': weak_count,
            'avg_cohesion': avg_cohesion,
            'level': level,
        },
        'pair_details': pair_details[:10],
        'suggestions': _generate_suggestions(
            len(pair_details), weak_count, avg_cohesion, level, pair_details
        ),
    }


def _generate_suggestions(total: int, weak: int, avg: float,
                           level: str, details: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'cohesive': '응집적',
        'mostly_cohesive': '대부분 응집', 'mixed': '혼재',
        'fragmented': '단절됨',
    }
    suggestions.append(
        f'문단 간 응집도: {level_labels.get(level, level)}. '
        f'{total}쌍 중 {weak}쌍 약함 (평균 응집도 {avg:.1%}).'
    )

    if weak > 0:
        suggestions.append(
            '인접 문단 사이에 전환어("따라서", "또한", "반면")를 추가하거나 '
            '공통 키워드로 연결하세요.'
        )

    weak_pairs = [d for d in details if d['is_weak']]
    for d in weak_pairs[:2]:
        suggestions.append(
            f'약한 연결: "{d["para_a_preview"]}..." ↔ '
            f'"{d["para_b_preview"]}..." (응집도 {d["effective_cohesion"]:.1%}).'
        )

    return suggestions
