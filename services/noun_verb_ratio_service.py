"""
Noun-to-Verb Ratio 서비스

콘텐츠의 명사/동사 비율을 분석합니다.
명사 과다 → 딱딱한 글, 동사 과다 → 산만한 글. 균형이 중요합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 동사 어미 패턴
_KO_VERB_ENDINGS = re.compile(
    r'(?:합니다|합니까|하세요|합시다|한다|했다|하고|하며|하면|하는|할|해서|하여|되다|된다|됩니다|갑니다|옵니다|봅니다|먹다|간다|온다|본다|쓴다|읽다|잔다|난다|든다|싶다|있다|없다|겠다|렵다|싸다|크다|작다|좋다|나쁘다|높다|낮다)$',
    re.UNICODE
)

# 한국어 명사 접미 패턴 (체언 + 조사)
_KO_NOUN_PARTICLES = re.compile(
    r'(?:[가-힣]{2,})(?:은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|까지|부터|에게|한테|께)$',
    re.UNICODE
)

# 영어 동사 (기본형)
_EN_VERBS = {
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did',
    'make', 'take', 'give', 'get', 'go', 'come', 'see', 'know',
    'think', 'say', 'tell', 'find', 'use', 'work', 'call', 'try',
    'need', 'feel', 'become', 'leave', 'put', 'mean', 'keep', 'let',
    'begin', 'seem', 'help', 'show', 'hear', 'play', 'run', 'move',
    'create', 'build', 'write', 'read', 'learn', 'change', 'follow',
    'start', 'stop', 'open', 'close', 'turn', 'hold', 'bring',
}

# 영어 관사/전치사 (명사 앞 표지)
_EN_NOUN_INDICATORS = {'the', 'a', 'an', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}


def _classify_tokens(content: str) -> Dict[str, int]:
    """토큰을 명사/동사/기타로 분류합니다."""
    cleaned = _HEADING_RE.sub('', content)
    tokens = cleaned.split()

    nouns = 0
    verbs = 0

    for token in tokens:
        t = token.strip('.,!?;:()[]{}"\'-')
        if not t:
            continue

        lower = t.lower()

        # 영어 판별
        if re.match(r'^[A-Za-z]+$', t):
            if lower in _EN_VERBS or lower.endswith(('ing', 'ed', 'ize', 'ise', 'ify', 'ate')):
                verbs += 1
            elif lower not in _EN_NOUN_INDICATORS and len(lower) >= 3:
                nouns += 1
        # 한국어 판별
        elif re.match(r'^[가-힣]+$', t):
            if _KO_VERB_ENDINGS.search(t):
                verbs += 1
            elif _KO_NOUN_PARTICLES.search(t) or len(t) >= 2:
                nouns += 1

    return {'nouns': nouns, 'verbs': verbs}


def analyze_noun_verb_ratio(content: str) -> dict:
    """명사/동사 비율을 분석합니다.

    Returns:
        counts, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'counts': {'nouns': 0, 'verbs': 0},
            'summary': {
                'noun_ratio': 0.0,
                'verb_ratio': 0.0,
                'nv_ratio': 0.0,
                'level': 'none',
            },
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    counts = _classify_tokens(content)
    nouns = counts['nouns']
    verbs = counts['verbs']
    total = nouns + verbs

    if total == 0:
        return {
            'counts': counts,
            'summary': {
                'noun_ratio': 0.0,
                'verb_ratio': 0.0,
                'nv_ratio': 0.0,
                'level': 'none',
            },
            'score': 50.0,
            'suggestions': [],
        }

    noun_ratio = round(nouns / total * 100, 1)
    verb_ratio = round(verbs / total * 100, 1)
    nv_ratio = round(nouns / max(verbs, 1), 2)

    # 레벨 (이상적 비율: 명사 60-70%, 동사 30-40%)
    if 1.2 <= nv_ratio <= 3.0:
        level = 'balanced'
    elif nv_ratio > 3.0:
        level = 'noun_heavy'
    elif nv_ratio < 1.2 and nv_ratio >= 0.5:
        level = 'verb_heavy'
    else:
        level = 'very_verb_heavy'

    # 점수
    if 1.5 <= nv_ratio <= 2.5:
        score = 100.0
    elif 1.2 <= nv_ratio < 1.5 or 2.5 < nv_ratio <= 3.0:
        score = 85.0
    elif 0.8 <= nv_ratio < 1.2 or 3.0 < nv_ratio <= 4.0:
        score = 70.0
    else:
        score = max(30.0, 70.0 - abs(nv_ratio - 2.0) * 10.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(noun_ratio, verb_ratio, nv_ratio, level)

    return {
        'counts': counts,
        'summary': {
            'noun_ratio': noun_ratio,
            'verb_ratio': verb_ratio,
            'nv_ratio': nv_ratio,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(n_ratio: float, v_ratio: float,
                           nv: float, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'balanced': '균형', 'noun_heavy': '명사 과다',
        'verb_heavy': '동사 과다', 'very_verb_heavy': '동사 매우 과다',
    }

    suggestions.append(
        f'명사 {n_ratio}%, 동사 {v_ratio}% '
        f'(비율 {nv}:1, {level_labels.get(level, level)}). '
        f'권장 비율: 1.5~2.5:1.'
    )

    if level == 'noun_heavy':
        suggestions.append(
            '명사가 많아 딱딱한 글입니다. '
            '능동적 동사를 추가하여 문장에 활력을 주세요.'
        )
    elif level in ('verb_heavy', 'very_verb_heavy'):
        suggestions.append(
            '동사가 많아 산만할 수 있습니다. '
            '구체적 명사를 사용하여 내용을 명확히 하세요.'
        )

    return suggestions
