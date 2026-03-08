"""
Clause Overload Detector 서비스

문장 내 절(clause)이 과도하게 겹친 복잡한 문장을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# ── 한국어 절 표지 패턴 ──
_KO_CLAUSE_MARKERS = [
    re.compile(r'(?<=[가-힣])고\s'),
    re.compile(r'(?<=[가-힣])며\s'),
    re.compile(r'면서\s'),
    re.compile(r'지만\s'),
    re.compile(r'는데\s'),
    re.compile(r'때문에\s'),
    re.compile(r'므로\s'),
    re.compile(r'라서\s'),
    re.compile(r'니까\s'),
    re.compile(r'거나\s'),
    re.compile(r'든지\s'),
]

# ── 영어 접속사/종속절 표지 ──
_EN_CLAUSE_MARKERS = re.compile(
    r'\b(and|but|or|because|although|while|when|if|since|'
    r'unless|whereas|however|therefore|moreover|furthermore|'
    r'nevertheless|nonetheless|consequently|additionally)\b',
    re.IGNORECASE,
)

# ── 쉼표 기반 절 분리 ──
_COMMA_PATTERN = re.compile(r',\s')

# ── 문장 분리 ──
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# ── 마크다운 헤딩 ──
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str) -> List[str]:
    """콘텐츠를 문장 단위로 분리합니다."""
    cleaned = _HEADING_RE.sub('', content)
    cleaned = re.sub(r'^\s*[-*]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 8]


def _count_clauses(sentence: str) -> tuple:
    """문장의 절 수와 감지된 마커를 반환합니다."""
    markers_found = []

    for pattern in _KO_CLAUSE_MARKERS:
        for match in pattern.finditer(sentence):
            markers_found.append(match.group(0).strip())

    for match in _EN_CLAUSE_MARKERS.finditer(sentence):
        markers_found.append(match.group(0))

    comma_count = len(_COMMA_PATTERN.findall(sentence))
    if comma_count >= 2:
        for _ in range(comma_count - 1):
            markers_found.append(',')

    clause_count = len(markers_found) + 1
    return clause_count, markers_found


def _determine_severity(clause_count: int) -> str:
    """절 수에 따라 심각도를 결정합니다."""
    if clause_count >= 4:
        return 'high'
    elif clause_count >= 3:
        return 'medium'
    return 'low'


_EMPTY_RESULT = {
    'overloaded_sentences': [],
    'summary': {'total_sentences': 0, 'overloaded': 0, 'avg_clauses': 0.0},
    'score': 100.0,
    'suggestions': [],
}


def _scan_overloaded(sentences: List[str]) -> tuple:
    """문장 목록에서 과부하 문장을 스캔합니다.

    Returns:
        (overloaded, total_clauses)
    """
    overloaded = []
    total_clauses = 0

    for sentence in sentences:
        clause_count, markers = _count_clauses(sentence)
        total_clauses += clause_count

        if clause_count >= 3:
            overloaded.append({
                'sentence': sentence if len(sentence) <= 200 else sentence[:197] + '...',
                'clause_count': clause_count,
                'severity': _determine_severity(clause_count),
                'markers': markers,
            })

    return overloaded, total_clauses


def detect_clause_overload(content: str) -> dict:
    """문장 내 절 과부하를 감지합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        overloaded_sentences, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_EMPTY_RESULT)

    overloaded, total_clauses = _scan_overloaded(sentences)

    total_sentences = len(sentences)
    avg_clauses = round(total_clauses / total_sentences, 2) if total_sentences > 0 else 0.0
    overloaded_count = len(overloaded)
    overload_ratio = (overloaded_count / total_sentences) if total_sentences > 0 else 0.0
    score = round(max(0.0, min(100.0, (1.0 - overload_ratio) * 100.0)), 1)

    return {
        'overloaded_sentences': overloaded,
        'summary': {
            'total_sentences': total_sentences,
            'overloaded': overloaded_count,
            'avg_clauses': avg_clauses,
        },
        'score': score,
        'suggestions': _generate_suggestions(overloaded_count, total_sentences, avg_clauses, overloaded),
    }


def _generate_suggestions(
    overloaded_count: int, total: int, avg: float, overloaded: List[Dict]
) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []
    if overloaded_count == 0:
        if total > 0:
            suggestions.append('문장 구조가 간결합니다. 과부하 문장이 없습니다.')
        return suggestions

    ratio = overloaded_count / total * 100 if total > 0 else 0
    suggestions.append(
        f'복잡한 문장이 {overloaded_count}개 ({ratio:.0f}%) 있습니다. '
        f'절을 분리하여 가독성을 높이세요.'
    )

    high_severity = [s for s in overloaded if s['severity'] == 'high']
    if high_severity:
        suggestions.append(
            f'심각도 높음(4절+) 문장이 {len(high_severity)}개 있습니다. '
            f'우선 분할을 권장합니다.'
        )

    if avg > 2.5:
        suggestions.append(
            f'평균 절 수 {avg}로 전반적으로 문장이 복잡합니다. '
            f'핵심 내용을 먼저 전달하는 구조로 개선하세요.'
        )
    return suggestions
