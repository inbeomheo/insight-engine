"""
대명사/지시어 명확성 검사 서비스

콘텐츠에서 선행어 없이 모호하게 사용된 지시어를 감지하고,
심각도별 분류 및 개선 제안을 제공합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# --- 지시어 목록 ---

# 한국어 지시어
_KO_PRONOUNS = ['이것', '그것', '저것', '이들', '그들', '이런', '그런', '이러한', '그러한']

# 영어 지시어 (소문자 매칭용)
_EN_PRONOUNS = ['it', 'this', 'that', 'they', 'them', 'these', 'those']

# 사전 컴파일된 영어 지시어 패턴 (루프 내 re.compile 반복 방지)
_EN_PRONOUN_PATTERNS = {
    p: re.compile(r'\b' + re.escape(p) + r'\b', re.IGNORECASE)
    for p in _EN_PRONOUNS
}

# 사전 컴파일된 영어 지시어+명사 패턴
_EN_PRONOUN_NOUN_PATTERNS = {
    p: re.compile(r'\b' + re.escape(p) + r'\s+(\w+)', re.IGNORECASE)
    for p in _EN_PRONOUNS
}

# 한국어 명사 패턴 (2자 이상 한글, 조사 제외)
_KO_NOUN_PATTERN = re.compile(r'[가-힣]{2,}')
_KO_PARTICLE = re.compile(r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서|까지|부터|만|라)$')

# 영어 명사 패턴 (대문자 시작 또는 일반 명사 — 간이 판정)
_EN_NOUN_PATTERN = re.compile(r'\b[A-Z][a-z]{2,}\b|\b[a-z]{3,}\b')

# 영어 비명사 단어 (동사/부사/전치사 등 — 명사 판정에서 제외)
_EN_NON_NOUNS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'must', 'need',
    'not', 'no', 'nor', 'but', 'and', 'or', 'if', 'then', 'else',
    'very', 'really', 'also', 'just', 'only', 'even', 'still',
    'in', 'on', 'at', 'to', 'for', 'with', 'from', 'by', 'of',
    'about', 'into', 'through', 'during', 'before', 'after',
    'it', 'this', 'that', 'they', 'them', 'these', 'those',
    'he', 'she', 'we', 'you', 'me', 'him', 'her', 'us',
    'my', 'your', 'his', 'its', 'our', 'their',
    'what', 'which', 'who', 'whom', 'how', 'when', 'where', 'why',
    'here', 'there', 'now', 'then', 'so', 'too', 'more', 'most',
}

# 한국어 지시어 + 명사 결합 패턴 (예: "이것은", "그들이" 등은 모호, "이런 방법" 등은 명확)
_KO_PRONOUN_WITH_NOUN = re.compile(
    r'(?:이것|그것|저것|이들|그들|이런|그런|이러한|그러한)\s+[가-힣]{2,}'
)

# 영어 지시어 + 명사 결합 패턴 (예: "this method", "these results")
_EN_PRONOUN_WITH_NOUN = re.compile(
    r'\b(?:this|that|these|those)\s+[a-zA-Z]{2,}\b', re.IGNORECASE
)

# 심각도별 제안 템플릿
_SUGGESTIONS = {
    'high': '문장 시작의 "{pronoun}"을(를) 구체적인 명사로 교체하세요.',
    'medium': '"{pronoun}"이(가) 가리키는 대상이 불분명합니다. 선행 문장에 명확한 명사를 추가하세요.',
}


def check_pronoun_clarity(content: str) -> dict:
    """콘텐츠의 지시어 모호성을 검사합니다.

    Args:
        content: 검사할 텍스트

    Returns:
        {
            "issues": [{"pronoun": str, "sentence": str, "position": str, "severity": str, "suggestion": str}],
            "summary": {"total": int, "by_severity": dict},
            "clarity_score": float,
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'issues': [],
            'summary': {'total': 0, 'by_severity': {}},
            'clarity_score': 100.0,
            'suggestions': ['검사할 콘텐츠가 비어 있습니다.'],
        }

    # 문장 분리
    sentences = _split_sentences(content)
    if not sentences:
        return {
            'issues': [],
            'summary': {'total': 0, 'by_severity': {}},
            'clarity_score': 100.0,
            'suggestions': [],
        }

    issues = []
    for i, sentence in enumerate(sentences):
        prev_sentence = sentences[i - 1] if i > 0 else ''
        found = _check_sentence(sentence, prev_sentence)
        issues.extend(found)

    # 요약 생성
    by_severity = {}
    for issue in issues:
        sev = issue['severity']
        by_severity[sev] = by_severity.get(sev, 0) + 1

    summary = {
        'total': len(issues),
        'by_severity': by_severity,
    }

    # 명확성 점수 (100점 기준, 이슈당 감점)
    clarity_score = _calculate_score(issues, len(sentences))

    # 전체 제안
    suggestions = _generate_suggestions(issues, len(sentences))

    return {
        'issues': issues,
        'summary': summary,
        'clarity_score': clarity_score,
        'suggestions': suggestions,
    }


def _split_sentences(content: str) -> list:
    """텍스트를 문장 단위로 분리합니다."""
    # 한국어 + 영어 문장 부호 기준
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content.strip())
    return [s.strip() for s in raw if len(s.strip()) >= 3]


def _check_sentence(sentence: str, prev_sentence: str) -> list:
    """단일 문장에서 모호한 지시어를 찾습니다."""
    issues = []

    # 문장의 단어 목록 (공백 기준)
    words = sentence.split()
    if not words:
        return issues

    # --- 한국어 지시어 검사 ---
    for pronoun in _KO_PRONOUNS:
        if pronoun not in sentence:
            continue

        # 지시어 + 명사 결합 확인 (예: "이런 방법" → 명확)
        if _has_following_noun_ko(sentence, pronoun):
            continue

        position = _get_position(sentence, pronoun)
        severity = _determine_severity(position, prev_sentence, is_korean=True)
        suggestion = _SUGGESTIONS[severity].format(pronoun=pronoun)

        issues.append({
            'pronoun': pronoun,
            'sentence': sentence,
            'position': position,
            'severity': severity,
            'suggestion': suggestion,
        })

    # --- 영어 지시어 검사 (사전 컴파일 패턴 사용) ---
    for pronoun in _EN_PRONOUNS:
        if not _EN_PRONOUN_PATTERNS[pronoun].search(sentence):
            continue

        # "this/that/these/those + 명사" 패턴은 명확 → 건너뜀
        if pronoun in ('this', 'that', 'these', 'those') and _has_following_noun_en(sentence, pronoun):
            continue

        position = _get_position_en(words, pronoun)
        severity = _determine_severity(position, prev_sentence, is_korean=False)
        suggestion = _SUGGESTIONS[severity].format(pronoun=pronoun)

        issues.append({
            'pronoun': pronoun,
            'sentence': sentence,
            'position': position,
            'severity': severity,
            'suggestion': suggestion,
        })

    return issues


def _has_following_noun_ko(sentence: str, pronoun: str) -> bool:
    """한국어 지시어 뒤에 명사가 바로 오는지 확인합니다."""
    # "이런 방법", "그러한 결과" 등 — 수식어형 지시어 + 명사
    pattern = re.compile(re.escape(pronoun) + r'\s+([가-힣]{2,})')
    match = pattern.search(sentence)
    if match:
        following = match.group(1)
        # 조사를 제거한 뒤 2자 이상이면 명사로 판정
        stem = _KO_PARTICLE.sub('', following)
        if len(stem) >= 2:
            return True
    return False


def _has_following_noun_en(sentence: str, pronoun: str) -> bool:
    """영어 지시어(this/that/these/those) 뒤에 명사가 오는지 확인합니다."""
    match = _EN_PRONOUN_NOUN_PATTERNS[pronoun].search(sentence)
    if match:
        following = match.group(1).lower()
        # 비명사 단어가 아니면 명사로 간주
        if following not in _EN_NON_NOUNS:
            return True
    return False


def _get_position(sentence: str, pronoun: str) -> str:
    """한국어 지시어의 문장 내 위치를 반환합니다."""
    stripped = sentence.strip()
    # 문장 시작 부분(첫 10자 이내)에 지시어가 있으면 start
    idx = stripped.find(pronoun)
    if idx >= 0 and idx <= 10:
        return 'start'
    return 'middle'


def _get_position_en(words: list, pronoun: str) -> str:
    """영어 지시어의 문장 내 위치를 반환합니다."""
    for i, w in enumerate(words):
        # 구두점 제거 후 비교
        cleaned = re.sub(r'[^\w]', '', w).lower()
        if cleaned == pronoun.lower():
            if i <= 1:
                return 'start'
            return 'middle'
    return 'middle'


def _determine_severity(position: str, prev_sentence: str, is_korean: bool) -> str:
    """지시어의 모호성 심각도를 결정합니다."""
    # 문장 시작 위치 → high
    if position == 'start':
        return 'high'

    # 중간 위치 + 이전 문장에 명사 없음 → medium
    if prev_sentence:
        has_noun = _has_nouns(prev_sentence, is_korean)
        if not has_noun:
            return 'medium'

    # 중간 위치 + 이전 문장에 명사 있음 → 그래도 medium (명사가 있어도 어떤 명사를 가리키는지 불명확)
    return 'medium'


def _has_nouns(sentence: str, is_korean: bool) -> bool:
    """문장에 명사가 포함되어 있는지 확인합니다."""
    if is_korean:
        nouns = _KO_NOUN_PATTERN.findall(sentence)
        # 조사 제거 후 2자 이상
        for n in nouns:
            stem = _KO_PARTICLE.sub('', n)
            if len(stem) >= 2:
                return True
        return False
    else:
        words = _EN_NOUN_PATTERN.findall(sentence)
        for w in words:
            if w.lower() not in _EN_NON_NOUNS:
                return True
        return False


def _calculate_score(issues: list, sentence_count: int) -> float:
    """명확성 점수를 계산합니다 (0-100)."""
    if sentence_count == 0:
        return 100.0

    # 이슈별 감점: high = 15점, medium = 8점
    penalty = 0
    for issue in issues:
        if issue['severity'] == 'high':
            penalty += 15
        else:
            penalty += 8

    score = max(0.0, min(100.0, 100.0 - penalty))
    return round(score, 1)


def _generate_suggestions(issues: list, sentence_count: int) -> list:
    """전체적인 개선 제안을 생성합니다."""
    suggestions = []

    if not issues:
        suggestions.append('모호한 지시어가 발견되지 않았습니다. 명확한 글입니다.')
        return suggestions

    high_count = sum(1 for i in issues if i['severity'] == 'high')
    medium_count = sum(1 for i in issues if i['severity'] == 'medium')

    if high_count > 0:
        suggestions.append(
            f'문장 시작에 모호한 지시어가 {high_count}건 발견되었습니다. '
            f'구체적인 명사로 교체하면 가독성이 향상됩니다.'
        )

    if medium_count > 0:
        suggestions.append(
            f'중간 심각도 지시어가 {medium_count}건 발견되었습니다. '
            f'선행 문장에서 가리키는 대상을 명확히 하세요.'
        )

    if len(issues) > 3:
        suggestions.append('지시어 사용이 많습니다. 핵심 주어를 반복하여 독자의 이해를 돕는 것이 좋습니다.')

    return suggestions
