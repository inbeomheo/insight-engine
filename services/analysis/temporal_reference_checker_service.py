"""
Temporal Reference Checker 서비스

콘텐츠 내 시제/시간 참조의 일관성을 검사합니다.
과거/현재/미래 시제 혼용, 모호한 시간 표현, 날짜 없는 시간 참조를 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from collections import Counter
import logging

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 시제 표지
_KO_PAST = re.compile(r'(?:했|였|었|했습니다|했다|되었|갔다|왔다|봤다|났다|됐다)', re.UNICODE)
_KO_PRESENT = re.compile(r'(?:합니다|합니다|한다|된다|간다|온다|본다|난다|있다|있습니다)', re.UNICODE)
_KO_FUTURE = re.compile(r'(?:할\s*것|하겠|될\s*것|할\s*예정|하게\s*될|할\s*계획)', re.UNICODE)

# 모호한 시간 표현 (구체적 날짜 없는 시간 참조)
_VAGUE_TIME = re.compile(
    r'(?:최근|요즘|얼마\s*전|며칠\s*전|지난번|다음에|나중에|곧|조만간|가까운\s*(?:시일|미래))',
    re.UNICODE
)

# 영어 시제 표지
_EN_PAST = re.compile(r'\b(?:was|were|had|did|went|came|made|said|took|gave)\b', re.IGNORECASE)
_EN_PRESENT = re.compile(r'\b(?:is|are|has|does|goes|comes|makes|says|takes|gives)\b', re.IGNORECASE)
_EN_FUTURE = re.compile(r'\b(?:will|shall|going\s+to|plan\s+to|expect\s+to)\b', re.IGNORECASE)

# 영어 모호한 시간
_EN_VAGUE_TIME = re.compile(
    r'\b(?:recently|lately|soon|eventually|someday|sometime|in\s+the\s+near\s+future)\b',
    re.IGNORECASE
)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _classify_tense(sentence: str) -> str:
    """문장의 주요 시제를 분류합니다."""
    past = len(_KO_PAST.findall(sentence)) + len(_EN_PAST.findall(sentence))
    present = len(_KO_PRESENT.findall(sentence)) + len(_EN_PRESENT.findall(sentence))
    future = len(_KO_FUTURE.findall(sentence)) + len(_EN_FUTURE.findall(sentence))

    scores = {'past': past, 'present': present, 'future': future}
    max_tense = max(scores, key=scores.get)
    if scores[max_tense] == 0:
        return 'neutral'
    return max_tense


_EMPTY_RESULT = {
    'tense_data': [],
    'vague_references': [],
    'summary': {
        'total_sentences': 0,
        'tense_distribution': {},
        'vague_count': 0,
        'consistency': 0.0,
        'level': 'none',
    },
    'score': 100.0,
    'suggestions': [],
}


def _classify_all_tenses(sentences: List[str]) -> tuple:
    """모든 문장의 시제를 분류합니다.

    Returns:
        (tense_data, tense_counter)
    """
    tense_data = []
    tense_counter = Counter()
    for sent in sentences:
        tense = _classify_tense(sent)
        tense_counter[tense] += 1
        tense_data.append({
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
            'tense': tense,
        })
    return tense_data, tense_counter


def _find_vague_references(content: str) -> List[Dict]:
    """모호한 시간 표현을 감지합니다."""
    cleaned = _HEADING_RE.sub('', content)
    vague_ko = _VAGUE_TIME.findall(cleaned)
    vague_en = _EN_VAGUE_TIME.findall(cleaned)
    refs = [{'text': v, 'language': 'ko'} for v in vague_ko]
    refs += [{'text': v, 'language': 'en'} for v in vague_en]
    return refs


def _compute_temporal_score(tense_counter: Counter, vague_count: int) -> tuple:
    """시제 일관성 점수와 레벨을 계산합니다.

    Returns:
        (score, level, consistency)
    """
    non_neutral = {k: v for k, v in tense_counter.items() if k != 'neutral'}
    total_tensed = sum(non_neutral.values())
    if total_tensed > 0:
        dominant_count = max(non_neutral.values())
        consistency = round(dominant_count / total_tensed * 100, 1)
    else:
        consistency = 100.0

    if consistency >= 80:
        level = 'consistent'
    elif consistency >= 60:
        level = 'mixed'
    else:
        level = 'inconsistent'

    score = consistency - min(20.0, vague_count * 3.0)
    score = round(max(0.0, min(100.0, score)), 1)

    return score, level, consistency


def check_temporal_references(content: str) -> dict:
    """시제/시간 참조 일관성을 검사합니다.

    Returns:
        tense_data, vague_references, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        sentences = _split_sentences(content)
        if not sentences:
            return dict(_EMPTY_RESULT)

        tense_data, tense_counter = _classify_all_tenses(sentences)
        vague_references = _find_vague_references(content)
        score, level, consistency = _compute_temporal_score(tense_counter, len(vague_references))

        suggestions = _generate_suggestions(
            tense_counter, consistency, level, len(vague_references), vague_references
        )

        return {
            'tense_data': tense_data[:30],
            'vague_references': vague_references[:15],
            'summary': {
                'total_sentences': len(sentences),
                'tense_distribution': dict(tense_counter),
                'vague_count': len(vague_references),
                'consistency': consistency,
                'level': level,
            },
            'score': score,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(tense_counter: Counter, consistency: float,
                           level: str, vague_count: int,
                           vague_refs: List[Dict]) -> List[str]:
    suggestions = []
    level_labels = {
        'consistent': '일관', 'mixed': '혼합', 'inconsistent': '불일관',
    }

    tense_labels = {'past': '과거', 'present': '현재', 'future': '미래', 'neutral': '중립'}
    dist_str = ', '.join([f'{tense_labels.get(k, k)} {v}개' for k, v in tense_counter.items() if k != 'neutral'])

    suggestions.append(
        f'시제 일관성 {consistency}% ({level_labels.get(level, level)}). '
        f'분포: {dist_str}.'
    )

    if level == 'inconsistent':
        suggestions.append(
            '시제가 불일관합니다. 하나의 주요 시제를 정하고 통일하세요.'
        )
    elif level == 'mixed':
        suggestions.append(
            '시제가 혼합되어 있습니다. 의도적 전환이 아니라면 통일을 권장합니다.'
        )

    if vague_count > 0:
        examples = [v['text'] for v in vague_refs[:2]]
        suggestions.append(
            f'모호한 시간 표현 {vague_count}개: {", ".join(examples)}. '
            f'구체적인 날짜/기간으로 대체하세요.'
        )

    return suggestions
