"""
Linking Verb Overuse Detector 서비스

be동사(이다/입니다) 과다 사용을 감지하여
능동적이고 구체적인 동사 사용을 권장합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 한국어 이다/입니다 패턴 (연결 동사)
_LINKING_KO = [
    re.compile(r'(?:입니다|이다|이에요|예요)(?:\s|[.!?]|$)'),
    re.compile(r'(?:있습니다|있다|있어요)(?:\s|[.!?]|$)'),
    re.compile(r'(?:됩니다|된다|돼요)(?:\s|[.!?]|$)'),
    re.compile(r'(?:아닙니다|아니다|아니에요)(?:\s|[.!?]|$)'),
]

# 영어 be동사 패턴
_LINKING_EN = [
    re.compile(r'\b(?:is|are|was|were|am|been|being)\b', re.IGNORECASE),
    re.compile(r'\b(?:become|became|seem|seemed|appear|appeared)\b', re.IGNORECASE),
    re.compile(r"\b(?:there\s+(?:is|are|was|were))\b", re.IGNORECASE),
]

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _count_words(content: str) -> int:
    english = re.findall(r'[A-Za-z]+(?:[-/][A-Za-z]+)*', content)
    korean = re.findall(r'[가-힣]+', content)
    return len(english) + len(korean)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _count_linking_verbs(sentence: str) -> Dict[str, int]:
    counts = {'korean': 0, 'english': 0}
    for p in _LINKING_KO:
        counts['korean'] += len(p.findall(sentence))
    for p in _LINKING_EN:
        counts['english'] += len(p.findall(sentence))
    return counts


def detect_linking_verb_overuse(content: str) -> dict:
    """연결 동사 과다 사용을 감지합니다.

    Returns:
        sentences, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'sentences': [],
            'summary': {'total_linking_verbs': 0, 'total_sentences': 0,
                        'linking_verb_ratio': 0.0, 'density': 0.0},
            'score': 100.0,
            'suggestions': [],
        }

    sentences = _split_sentences(content)
    if not sentences:
        return {
            'sentences': [],
            'summary': {'total_linking_verbs': 0, 'total_sentences': 0,
                        'linking_verb_ratio': 0.0, 'density': 0.0},
            'score': 100.0,
            'suggestions': [],
        }

    total_linking = 0
    sentences_with_linking = 0
    result_sentences = []

    for sent in sentences:
        counts = _count_linking_verbs(sent)
        total = counts['korean'] + counts['english']
        total_linking += total
        has_linking = total > 0
        if has_linking:
            sentences_with_linking += 1

        if has_linking:
            result_sentences.append({
                'text': sent if len(sent) <= 100 else sent[:97] + '...',
                'linking_count': total,
                'types': {k: v for k, v in counts.items() if v > 0},
            })

    total_sents = len(sentences)
    ratio = round((sentences_with_linking / total_sents * 100) if total_sents > 0 else 0.0, 1)

    word_count = _count_words(content)
    density = round((total_linking / word_count * 100) if word_count > 0 else 0.0, 2)

    # 점수: 연결 동사 비율 기반 (적정: 30-50%)
    if ratio <= 40:
        score = 100.0
    elif ratio <= 60:
        score = 100.0 - (ratio - 40) * 1.5
    elif ratio <= 80:
        score = 70.0 - (ratio - 60) * 1.5
    else:
        score = max(0.0, 40.0 - (ratio - 80) * 2.0)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(ratio, density, total_linking, sentences_with_linking)

    return {
        'sentences': result_sentences,
        'summary': {
            'total_linking_verbs': total_linking,
            'total_sentences': total_sents,
            'linking_verb_ratio': ratio,
            'density': density,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(ratio: float, density: float, total: int, with_lv: int) -> List[str]:
    suggestions = []
    if total == 0:
        return suggestions
    if ratio > 60:
        suggestions.append(
            f'연결 동사 사용 비율 {ratio}% (적정: 40% 이하). '
            f'"~입니다/is" 대신 구체적 동사를 사용하세요.'
        )
    elif ratio > 40:
        suggestions.append(f'연결 동사 비율 {ratio}%로 양호합니다.')
    else:
        suggestions.append(f'연결 동사 비율 {ratio}%로 적정합니다. 동사 사용이 활발합니다.')

    if ratio > 50:
        suggestions.append(
            '대체 팁: "X는 Y이다" → "X가 Y를 한다", '
            '"There is X" → "X exists/occurs"'
        )
    return suggestions
