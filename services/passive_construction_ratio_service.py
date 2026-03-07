"""
Passive Construction Ratio 서비스

콘텐츠에서 피동/수동 구문의 비율을 분석합니다.
한국어 피동 접미사(-되다, -받다, -당하다)와 영어 수동태(be + past participle)를 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 피동 표현
_KO_PASSIVE = [
    re.compile(r'(?:되었|되어|되고|되는|되면|되지|된다|됩니다|됐습니다)'),
    re.compile(r'(?:받았|받고|받는|받게|받을|받습니다)'),
    re.compile(r'(?:당했|당하|당한|당하는|당합니다)'),
    re.compile(r'(?:지어|지게|지는|져서|졌습니다)'),  # ~아/어지다
    re.compile(r'(?:시키|시킨|시켜|시킵니다)'),  # ~시키다 (사동이지만 수동적 맥락)
]

# 영어 수동태 (be + past participle 근사)
_EN_PASSIVE = [
    re.compile(r'\b(?:is|are|was|were|been|being)\s+(?:\w+ed|written|done|made|taken|given|shown|known|found|built|sent|told|seen|held|kept|left|brought|set|run|put)\b', re.IGNORECASE),
    re.compile(r'\b(?:is|are|was|were)\s+(?:being\s+)?\w+ed\b', re.IGNORECASE),
]


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _is_passive(sentence: str) -> bool:
    """문장이 피동/수동 구문인지 판별합니다."""
    for p in _KO_PASSIVE:
        if p.search(sentence):
            return True
    for p in _EN_PASSIVE:
        if p.search(sentence):
            return True
    return False


def analyze_passive_ratio(content: str) -> dict:
    """피동/수동 구문 비율을 분석합니다.

    Returns:
        passive_sentences, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'passive_sentences': [],
            'summary': {'total_sentences': 0, 'passive_count': 0,
                        'passive_ratio': 0.0, 'level': 'none'},
            'score': 100.0,
            'suggestions': [],
        }

    sentences = _split_sentences(content)
    if not sentences:
        return {
            'passive_sentences': [],
            'summary': {'total_sentences': 0, 'passive_count': 0,
                        'passive_ratio': 0.0, 'level': 'none'},
            'score': 100.0,
            'suggestions': [],
        }

    passive_list = []
    for sent in sentences:
        if _is_passive(sent):
            passive_list.append({
                'text': sent if len(sent) <= 60 else sent[:57] + '...',
            })

    total = len(sentences)
    passive_count = len(passive_list)
    ratio = round(passive_count / total * 100, 1) if total > 0 else 0.0

    # 레벨
    if ratio <= 15:
        level = 'low'
    elif ratio <= 30:
        level = 'moderate'
    elif ratio <= 50:
        level = 'high'
    else:
        level = 'excessive'

    # 점수
    if ratio <= 20:
        score = 100.0
    elif ratio <= 35:
        score = 100.0 - (ratio - 20) * 2.0
    else:
        score = max(0.0, 70.0 - (ratio - 35) * 2.0)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(ratio, passive_count, level)

    return {
        'passive_sentences': passive_list[:20],
        'summary': {
            'total_sentences': total,
            'passive_count': passive_count,
            'passive_ratio': ratio,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(ratio: float, count: int, level: str) -> List[str]:
    suggestions = []
    level_labels = {'low': '적정', 'moderate': '보통', 'high': '높음', 'excessive': '과다'}

    suggestions.append(f'피동 구문 비율 {ratio}% ({level_labels.get(level, level)}).')

    if level in ('high', 'excessive'):
        suggestions.append(
            '피동 구문이 많습니다. 능동형으로 바꾸면 글이 더 직접적이고 힘이 생깁니다.'
        )
        suggestions.append(
            '예: "결정이 내려졌다" → "팀이 결정했다", '
            '"문제가 발견되었다" → "우리가 문제를 발견했다"'
        )

    return suggestions
