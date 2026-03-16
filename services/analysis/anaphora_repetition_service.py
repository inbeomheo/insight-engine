"""
Anaphora Repetition Detector 서비스

콘텐츠에서 연속 문장의 동일 어구 반복(수사적 반복, anaphora)을 감지합니다.
의도적 수사법과 비의도적 반복을 구분합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 최소 반복 횟수
_MIN_REPEAT = 3
# 비교할 시작 단어 수
_PREFIX_WORDS = 1


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _get_prefix(sentence: str, n: int = _PREFIX_WORDS) -> str:
    """문장의 첫 n개 단어를 추출합니다."""
    # 한국어+영어 단어 추출
    words = re.findall(r'[가-힣]+|[A-Za-z]+', sentence)
    if len(words) < n:
        return ' '.join(words).lower() if words else ''
    return ' '.join(words[:n]).lower()


_EMPTY_RESULT = {
    'anaphora_groups': [],
    'summary': {'total_sentences': 0, 'groups_found': 0,
                'repeated_sentences': 0, 'intentional_count': 0},
    'score': 100.0,
    'suggestions': [],
}


def _scan_anaphora_groups(sentences: List[str]) -> List[Dict]:
    """연속 동일 접두사 그룹을 찾습니다."""
    groups = []
    i = 0
    while i < len(sentences):
        prefix = _get_prefix(sentences[i])
        if not prefix:
            i += 1
            continue

        group_sentences = [sentences[i]]
        j = i + 1
        while j < len(sentences):
            if _get_prefix(sentences[j]) == prefix:
                group_sentences.append(sentences[j])
                j += 1
            else:
                break

        if len(group_sentences) >= _MIN_REPEAT:
            groups.append({
                'prefix': prefix,
                'count': len(group_sentences),
                'sentences': [s if len(s) <= 60 else s[:57] + '...' for s in group_sentences],
                'is_intentional': _is_intentional_anaphora(group_sentences),
            })

        i = j if j > i + 1 else i + 1

    return groups


def _compute_anaphora_score(groups: List[Dict]) -> tuple:
    """반복 점수를 계산합니다.

    Returns:
        (score, intentional, unintentional)
    """
    intentional = sum(1 for g in groups if g['is_intentional'])
    unintentional = len(groups) - intentional

    if unintentional == 0:
        score = 100.0
    else:
        score = max(0.0, 100.0 - unintentional * 15.0)

    return round(min(100.0, score), 1), intentional, unintentional


def detect_anaphora_repetition(content: str) -> dict:
    """연속 문장 시작부 반복(anaphora)을 감지합니다.

    Returns:
        anaphora_groups, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        sentences = _split_sentences(content)
        if len(sentences) < _MIN_REPEAT:
            return {**_EMPTY_RESULT, 'summary': {**_EMPTY_RESULT['summary'],
                    'total_sentences': len(sentences)}}

        groups = _scan_anaphora_groups(sentences)
        total_repeated = sum(g['count'] for g in groups)
        score, intentional, unintentional = _compute_anaphora_score(groups)

        return {
            'anaphora_groups': groups,
            'summary': {
                'total_sentences': len(sentences),
                'groups_found': len(groups),
                'repeated_sentences': total_repeated,
                'intentional_count': intentional,
            },
            'score': score,
            'suggestions': _generate_suggestions(groups, intentional, unintentional),
        }
    except Exception as e:
        logger.error(f"수사 반복 감지 실패: {e}")
        return {"error": str(e)}


def _is_intentional_anaphora(sentences: List[str]) -> bool:
    """의도적 수사적 반복인지 판별합니다.
    기준: 문장 길이 유사 + 구조적 병렬성.
    """
    if len(sentences) < 3:
        return False
    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)
    # 길이 편차가 평균의 50% 이내면 의도적 가능성
    variance = all(abs(l - avg) / avg < 0.5 for l in lengths) if avg > 0 else False
    return variance


def _generate_suggestions(groups: List[Dict], intentional: int, unintentional: int) -> List[str]:
    suggestions = []

    if not groups:
        suggestions.append('반복 패턴(anaphora)이 감지되지 않았습니다.')
        return suggestions

    if intentional > 0:
        suggestions.append(
            f'의도적 수사 반복 {intentional}개: 강조 효과가 있습니다.'
        )

    if unintentional > 0:
        examples = [f'"{g["prefix"]}..." ({g["count"]}회)' for g in groups if not g['is_intentional']]
        if examples:
            suggestions.append(
                f'비의도적 반복 {unintentional}개: {", ".join(examples[:2])}. '
                f'문장 시작을 다양하게 바꾸세요.'
            )

    return suggestions
