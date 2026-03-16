"""
Concept Load Analyzer 서비스

짧은 구간에 새 개념·약어·엔티티가 과도하게 몰려
독자 인지부하가 커지는 부분을 찾습니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 새 개념 신호 패턴
_CONCEPT_PATTERNS = [
    re.compile(r'\b[A-Z]{2,6}\b'),  # 약어
    re.compile(r'(?:레이턴시|스루풋|미들웨어|프레임워크|리팩토링|오케스트레이션|'
               r'프로비저닝|컨테이너|클러스터|파이프라인|웹훅|폴링|소켓|'
               r'시리얼라이제이션|디커플링|마이크로서비스)', re.IGNORECASE),
    re.compile(r'\b(?:latency|throughput|middleware|framework|refactoring|'
               r'orchestration|provisioning|containerization|serialization|'
               r'webhook|polling|sharding|partitioning|replication|'
               r'idempotent|polymorphism|encapsulation)\b', re.IGNORECASE),
]

# 정의/설명 패턴 (있으면 부하 완화)
_EXPLANATION_PATTERNS = [
    re.compile(r'(?:이란|란|이라\s*함은|뜻하|의미합|의미하|즉,|다시\s*말해)', re.IGNORECASE),
    re.compile(r'\b(?:means?|i\.e\.|refers?\s+to|defined?\s+as)\b', re.IGNORECASE),
    re.compile(r'\([^)]{5,}\)', re.IGNORECASE),  # 괄호 설명
]

# 흔한 약어 (인지부하 낮음)
_COMMON = {
    'API', 'URL', 'HTML', 'CSS', 'JS', 'JSON', 'HTTP', 'HTTPS',
    'SQL', 'DB', 'UI', 'UX', 'OS', 'CPU', 'RAM', 'GPU',
    'ID', 'IP', 'DNS', 'SSH', 'CI', 'CD', 'PR', 'QA',
    'AI', 'ML', 'OK', 'FAQ', 'TODO', 'PDF', 'CSV',
}

# 윈도우 크기 (문장 수)
_WINDOW_SIZE = 3
# 과부하 임계값 (윈도우당 새 개념 수)
_OVERLOAD_THRESHOLD = 4


def _extract_concepts(sentence: str) -> Set[str]:
    """문장에서 개념/약어를 추출합니다."""
    concepts = set()
    for pat in _CONCEPT_PATTERNS:
        for m in pat.finditer(sentence):
            text = m.group().strip()
            if text.upper() not in _COMMON and len(text) >= 2:
                concepts.add(text.lower())
    return concepts


def _has_explanation(sentence: str) -> bool:
    """설명/정의가 포함되어 있는지 확인합니다."""
    return any(p.search(sentence) for p in _EXPLANATION_PATTERNS)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'total_sentences': 0, 'max_concepts_in_window': 0,
        'overloaded_windows': 0, 'level': 'none',
    },
    'overloaded_segments': [],
    'suggestions': [],
}


def _detect_overloaded_windows(sentences: List[str],
                                sentence_concepts: List[Set],
                                sentence_explanations: List[bool]) -> tuple:
    """슬라이딩 윈도우로 과부하 구간을 탐지합니다.

    Returns:
        (overloaded, max_concepts)
    """
    overloaded = []
    max_concepts = 0

    for i in range(len(sentences) - _WINDOW_SIZE + 1):
        window_concepts = set()
        has_expl = False
        for j in range(i, i + _WINDOW_SIZE):
            window_concepts |= sentence_concepts[j]
            if sentence_explanations[j]:
                has_expl = True

        threshold = _OVERLOAD_THRESHOLD + (2 if has_expl else 0)
        concept_count = len(window_concepts)
        max_concepts = max(max_concepts, concept_count)

        if concept_count >= threshold:
            overloaded.append({
                'start_sentence': i,
                'end_sentence': i + _WINDOW_SIZE - 1,
                'concept_count': concept_count,
                'concepts': sorted(list(window_concepts))[:6],
                'preview': sentences[i][:50],
                'has_explanation': has_expl,
            })

    return overloaded, max_concepts


def _compute_load_score(overloaded_count: int, max_concepts: int,
                         sentence_count: int) -> tuple:
    """과부하 비율로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if overloaded_count == 0:
        level = 'manageable'
    elif overloaded_count <= 2:
        level = 'minor_overload'
    elif overloaded_count <= 5:
        level = 'moderate_overload'
    else:
        level = 'heavy_overload'

    if overloaded_count == 0:
        score = 100.0
    else:
        total_windows = max(1, sentence_count - _WINDOW_SIZE + 1)
        overload_ratio = overloaded_count / total_windows
        score = max(10.0, 100.0 - (overload_ratio * 80.0) - (min(max_concepts, 15) * 1.5))

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_concept_load(content: str) -> dict:
    """구간별 인지부하를 분석합니다.

    Returns:
        score, summary, overloaded_segments, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content)
                     if s.strip() and len(s.strip()) >= 5]
        if not sentences:
            return dict(_EMPTY_RESULT)

        sentence_concepts = [_extract_concepts(s) for s in sentences]
        sentence_explanations = [_has_explanation(s) for s in sentences]

        overloaded, max_concepts = _detect_overloaded_windows(
            sentences, sentence_concepts, sentence_explanations
        )
        score, level = _compute_load_score(len(overloaded), max_concepts, len(sentences))

        suggestions = _generate_suggestions(
            len(sentences), max_concepts, len(overloaded), level, overloaded
        )

        return {
            'score': score,
            'summary': {
                'total_sentences': len(sentences),
                'max_concepts_in_window': max_concepts,
                'overloaded_windows': len(overloaded),
                'level': level,
            },
            'overloaded_segments': overloaded[:10],
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(total: int, max_concepts: int,
                           overloaded: int, level: str,
                           segments: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'manageable': '적절',
        'minor_overload': '경미한 과부하',
        'moderate_overload': '보통 과부하',
        'heavy_overload': '심한 과부하',
    }
    suggestions.append(
        f'인지부하: {level_labels.get(level, level)}. '
        f'최대 {max_concepts}개 개념/윈도우, 과부하 구간 {overloaded}건.'
    )

    if overloaded > 0:
        suggestions.append(
            '새 개념이 밀집된 구간에 정의나 예시를 추가하거나, '
            '개념을 여러 문단에 분산시키세요.'
        )

    for seg in segments[:2]:
        concepts = ', '.join(seg['concepts'][:4])
        suggestions.append(
            f'과부하 구간: "{seg["preview"]}..." — '
            f'{seg["concept_count"]}개 개념 ({concepts}).'
        )

    return suggestions
