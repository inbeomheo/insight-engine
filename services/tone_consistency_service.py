"""
Tone Consistency Checker 서비스

콘텐츠에서 문체(격식/비격식) 일관성을 점검합니다.
한국어 반말/존댓말 혼용, 영어 격식/비격식 혼용을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# ── 한국어 존댓말 패턴 ──
_FORMAL_KO = [
    re.compile(r'(?:합니다|입니다|됩니다|있습니다|없습니다|됐습니다)'),
    re.compile(r'(?:하십시오|주십시오|바랍니다)'),
    re.compile(r'(?:하겠습니다|드리겠습니다)'),
]

# ── 한국어 해요체 패턴 ──
_POLITE_KO = [
    re.compile(r'(?:해요|이에요|이래요|인데요|거든요|잖아요|네요|군요)'),
    re.compile(r'(?:하세요|주세요|보세요)'),
    re.compile(r'(?:할게요|할까요|인가요)'),
]

# ── 한국어 반말 패턴 ──
_CASUAL_KO = [
    re.compile(r'(?:좋아|싫어|맞아|아닌데|그래|몰라|해봐|해줘)(?:\s|[.!?]|$)'),
    re.compile(r'(?:하자|보자|가자|알지|맞지)(?:\s|[.!?]|$)'),
    re.compile(r'(?:했어|됐어|봤어|갔어|왔어)(?:\s|[.!?]|$)'),
    re.compile(r'(?:거야|잖아|건데|인데|이야)(?:\s|[.!?]|$)'),
]

# ── 영어 격식 패턴 ──
_FORMAL_EN = [
    re.compile(r'\b(?:Furthermore|Moreover|Nevertheless|Consequently|Therefore)\b'),
    re.compile(r'\b(?:It is|One should|It has been)\b'),
    re.compile(r'\b(?:hereby|herein|aforementioned|pursuant)\b', re.IGNORECASE),
]

# ── 영어 비격식 패턴 ──
_CASUAL_EN = [
    re.compile(r"\b(?:gonna|wanna|gotta|ain't|y'all)\b", re.IGNORECASE),
    re.compile(r'\b(?:pretty much|kind of|sort of|a lot of|tons of)\b', re.IGNORECASE),
    re.compile(r'\b(?:awesome|cool|stuff|things|guys)\b', re.IGNORECASE),
    re.compile(r'(?:!{2,}|\?{2,})'),  # !! or ??
]

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 3]


def _classify_tone(sentence: str) -> str:
    """문장의 톤을 분류합니다: formal, polite, casual, neutral."""
    # 한국어 체크
    for p in _FORMAL_KO:
        if p.search(sentence):
            return 'formal'
    for p in _POLITE_KO:
        if p.search(sentence):
            return 'polite'
    for p in _CASUAL_KO:
        if p.search(sentence):
            return 'casual'
    # 영어 체크
    for p in _FORMAL_EN:
        if p.search(sentence):
            return 'formal'
    for p in _CASUAL_EN:
        if p.search(sentence):
            return 'casual'
    return 'neutral'


_EMPTY_RESULT = {
    'tone_analysis': [],
    'inconsistencies': [],
    'summary': {'total_sentences': 0, 'dominant_tone': '',
                'consistency_rate': 0.0, 'tone_distribution': {}},
    'score': 100.0,
    'suggestions': [],
}


def _classify_sentences(sentences: List[str]) -> tuple:
    """문장별 톤을 분류하고 지배적 톤을 결정합니다.

    Returns:
        (tone_analysis, tone_counts, dominant)
    """
    tone_analysis = []
    tone_counts = {'formal': 0, 'polite': 0, 'casual': 0, 'neutral': 0}

    for sent in sentences:
        tone = _classify_tone(sent)
        tone_counts[tone] += 1
        tone_analysis.append({
            'text': sent if len(sent) <= 80 else sent[:77] + '...',
            'tone': tone,
        })

    non_neutral = {k: v for k, v in tone_counts.items() if k != 'neutral'}
    dominant = max(non_neutral, key=non_neutral.get) if non_neutral else 'neutral'

    return tone_analysis, tone_counts, dominant


def _find_inconsistencies(tone_analysis: List[Dict], dominant: str,
                           tone_counts: Dict) -> tuple:
    """비일관 문장을 감지하고 일관성 비율을 계산합니다.

    Returns:
        (inconsistencies, consistency_rate)
    """
    inconsistencies = []
    if dominant != 'neutral':
        for ta in tone_analysis:
            if ta['tone'] != 'neutral' and ta['tone'] != dominant:
                inconsistencies.append({
                    'text': ta['text'], 'expected': dominant,
                    'actual': ta['tone'],
                })

    total_toned = sum(v for k, v in tone_counts.items() if k != 'neutral')
    dominant_count = tone_counts.get(dominant, 0) if dominant != 'neutral' else 0
    consistency_rate = round(
        (dominant_count / total_toned * 100) if total_toned > 0 else 100.0, 1
    )
    return inconsistencies, consistency_rate


def check_tone_consistency(content: str) -> dict:
    """문체 일관성을 점검합니다.

    Returns:
        tone_analysis, inconsistencies, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_EMPTY_RESULT)

    tone_analysis, tone_counts, dominant = _classify_sentences(sentences)
    inconsistencies, consistency_rate = _find_inconsistencies(
        tone_analysis, dominant, tone_counts
    )

    total_toned = sum(v for k, v in tone_counts.items() if k != 'neutral')
    score = 100.0 if total_toned == 0 else round(min(100.0, consistency_rate), 1)
    distribution = {k: v for k, v in tone_counts.items() if v > 0}

    return {
        'tone_analysis': tone_analysis,
        'inconsistencies': inconsistencies,
        'summary': {
            'total_sentences': len(sentences), 'dominant_tone': dominant,
            'consistency_rate': consistency_rate, 'tone_distribution': distribution,
        },
        'score': score,
        'suggestions': _generate_suggestions(
            dominant, inconsistencies, consistency_rate, distribution
        ),
    }


def _generate_suggestions(
    dominant: str, incons: List[Dict], rate: float, dist: Dict
) -> List[str]:
    tone_labels = {
        'formal': '격식체(합니다)',
        'polite': '해요체',
        'casual': '반말/비격식',
        'neutral': '중립',
    }
    suggestions = []

    if not incons:
        if dominant != 'neutral':
            suggestions.append(f'문체가 {tone_labels.get(dominant, dominant)}로 일관적입니다.')
        return suggestions

    suggestions.append(
        f'지배적 문체: {tone_labels.get(dominant, dominant)} (일관성 {rate}%). '
        f'비일관 문장 {len(incons)}개를 확인하세요.'
    )

    if 'formal' in dist and 'casual' in dist:
        suggestions.append(
            '격식체와 반말이 혼용되어 있습니다. 독자에 맞는 하나의 문체로 통일하세요.'
        )

    if len(incons) > 3:
        examples = ', '.join(f'"{i["text"][:30]}..."' for i in incons[:2])
        suggestions.append(f'주요 비일관 문장: {examples}')

    return suggestions
