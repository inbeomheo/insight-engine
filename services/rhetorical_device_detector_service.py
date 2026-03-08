"""
Rhetorical Device Detector 서비스

콘텐츠에서 수사법(비유, 대구, 반복, 열거 등)을 감지합니다.
한국어/영어 수사적 장치의 사용 빈도와 다양성을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List
from collections import Counter

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 직유 (simile) — "~처럼", "~같이", "~듯이", "like", "as if"
_KO_SIMILE = re.compile(r'(?:처럼|같이|듯이|듯한|마냥|마치)', re.UNICODE)
_EN_SIMILE = re.compile(r'\b(?:like\s+a|as\s+if|as\s+though|just\s+like|as\s+\w+\s+as)\b', re.IGNORECASE)

# 은유 (metaphor) — "~은/는 ~이다" (A는 B다 형태)
_KO_METAPHOR = re.compile(r'(?:은|는)\s+.{2,15}(?:이다|입니다|였다)', re.UNICODE)

# 과장 (hyperbole)
_KO_HYPERBOLE = re.compile(r'(?:천만|억만|무한|끝없는|영원한|세상에서\s*가장|역사상\s*최대|전무후무)', re.UNICODE)
_EN_HYPERBOLE = re.compile(r'\b(?:million\s+times|never\s+ever|absolutely\s+impossible|literally\s+dying)\b', re.IGNORECASE)

# 반복 (repetition) — 같은 구절이 2회 이상 나타남
# 실제 감지는 함수에서 처리

# 대구/병렬 (parallelism) — "~고, ~고, ~고" 또는 "~하며, ~하며"
_KO_PARALLEL = re.compile(r'(?:고,?\s+.{2,20}고,?\s+.{2,20}고)|(?:하며,?\s+.{2,20}하며)', re.UNICODE)

# 열거 (enumeration) — "첫째, 둘째, 셋째" 또는 "1), 2), 3)"
_KO_ENUM = re.compile(r'(?:첫째|둘째|셋째|넷째|다섯째)|(?:\d\)\s)', re.UNICODE)

# 설의법 (rhetorical question) — 물음표로 끝나는 문장
_RHETORICAL_Q = re.compile(r'[가-힣\w\s]{5,}\?')

# 대조 (antithesis) — "~이 아니라 ~이다", "not A but B"
_KO_ANTITHESIS = re.compile(r'(?:이\s*아니라|가\s*아닌|것이\s*아니라|아닌)', re.UNICODE)
_EN_ANTITHESIS = re.compile(r'\bnot\s+\w+\s+but\s+\w+\b', re.IGNORECASE)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _detect_repetition(sentences: List[str]) -> int:
    """연속 문장에서 반복 구절을 감지합니다."""
    if len(sentences) < 2:
        return 0
    count = 0
    for i in range(len(sentences) - 1):
        words_a = set(sentences[i].split()[:3])
        words_b = set(sentences[i + 1].split()[:3])
        if len(words_a & words_b) >= 2 and len(words_a) >= 2:
            count += 1
    return count


_EMPTY_RESULT = {
    'devices': [],
    'summary': {
        'total_devices': 0, 'device_types': 0,
        'density': 0.0, 'level': 'none',
    },
    'score': 50.0,
    'suggestions': [],
}

# 패턴 매핑: (장치 이름, 패턴 리스트)
_DEVICE_CHECKS = [
    ('simile', [_KO_SIMILE, _EN_SIMILE]),
    ('metaphor', [_KO_METAPHOR]),
    ('hyperbole', [_KO_HYPERBOLE, _EN_HYPERBOLE]),
    ('parallelism', [_KO_PARALLEL]),
    ('enumeration', [_KO_ENUM]),
    ('antithesis', [_KO_ANTITHESIS, _EN_ANTITHESIS]),
]


def _scan_devices(sentences: List[str]) -> tuple:
    """문장별 수사 장치를 스캔합니다.

    Returns:
        (devices, type_counter)
    """
    devices = []
    type_counter = Counter()

    for sent in sentences:
        for device_name, patterns in _DEVICE_CHECKS:
            if any(p.search(sent) for p in patterns):
                devices.append({'type': device_name, 'text': sent[:60]})
                type_counter[device_name] += 1

        if _RHETORICAL_Q.search(sent) and sent.strip().endswith('?'):
            devices.append({'type': 'rhetorical_question', 'text': sent[:60]})
            type_counter['rhetorical_question'] += 1

    rep_count = _detect_repetition(sentences)
    if rep_count > 0:
        type_counter['repetition'] = rep_count

    return devices, type_counter


def _compute_rhetoric_score(type_counter: Counter, sentence_count: int) -> tuple:
    """수사 장치 다양성으로 점수와 레벨을 계산합니다.

    Returns:
        (score, level, device_types, total_devices, density)
    """
    total_devices = sum(type_counter.values())
    device_types = len(type_counter)
    density = round(total_devices / max(sentence_count, 1) * 100, 1)

    if device_types >= 4:
        level = 'rich'
    elif device_types >= 2:
        level = 'moderate'
    elif device_types >= 1:
        level = 'minimal'
    else:
        level = 'none'

    score = min(100.0, device_types * 20.0 + total_devices * 3.0)
    for _t, c in type_counter.items():
        if c > sentence_count * 0.4:
            score -= 10.0

    score = round(max(0.0, min(100.0, score)), 1)
    return score, level, device_types, total_devices, density


def detect_rhetorical_devices(content: str) -> dict:
    """수사법을 감지합니다.

    Returns:
        devices, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_EMPTY_RESULT)

    devices, type_counter = _scan_devices(sentences)
    score, level, device_types, total_devices, density = (
        _compute_rhetoric_score(type_counter, len(sentences))
    )
    suggestions = _generate_suggestions(type_counter, device_types, density, level)

    return {
        'devices': devices[:30],
        'summary': {
            'total_devices': total_devices,
            'device_types': device_types,
            'device_breakdown': dict(type_counter),
            'density': density,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(type_counter: Counter, types: int,
                           density: float, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'rich': '풍부', 'moderate': '보통',
        'minimal': '최소', 'none': '없음',
    }
    suggestions.append(
        f'수사법 다양성: {level_labels.get(level, level)} '
        f'({types}종, 밀도 {density}%).'
    )

    if level == 'none':
        suggestions.append(
            '수사법이 감지되지 않았습니다. '
            '비유, 대조, 열거 등을 활용하면 글의 설득력이 높아집니다.'
        )

    type_labels = {
        'simile': '직유', 'metaphor': '은유', 'hyperbole': '과장',
        'parallelism': '대구', 'enumeration': '열거',
        'rhetorical_question': '설의법', 'antithesis': '대조',
        'repetition': '반복',
    }
    missing = set(type_labels.keys()) - set(type_counter.keys())
    if missing and types >= 1:
        missing_labels = [type_labels[m] for m in list(missing)[:3]]
        suggestions.append(
            f'시도해 볼 수사법: {", ".join(missing_labels)}.'
        )

    return suggestions
