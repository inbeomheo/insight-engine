"""
음성 적합성 분석 서비스 (Speakability Analyzer)

콘텐츠가 음성 재생(TTS/팟캐스트/음성 검색)에
적합한지 5가지 요소로 평가합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 약어/두문자어 패턴 (2~6자 연속 대문자 또는 마침표 포함 약어)
# 한국어 문자 옆에 붙은 약어도 감지하기 위해 \b 대신 룩어라운드 사용
_ABBREVIATION_RE = re.compile(r'(?<![A-Za-z])[A-Z]{2,6}(?![A-Za-z])|[A-Z](?:\.[A-Z])+\.?')

# 숫자/통계 패턴 (소수, 퍼센트, 화폐, 범위 등 포함)
_NUMBER_RE = re.compile(
    r'\d+(?:\.\d+)?(?:%|원|달러|만|억|천|kg|km|MB|GB|TB)?'
    r'|\d+[,\.]\d+'
    r'|\d+~\d+'
)

# 괄호 표현 패턴
_PAREN_RE = re.compile(r'[\(（\[【][^)）\]】]*[\)）\]】]')

# 복잡한 구조 패턴
_NESTED_PAREN_RE = re.compile(r'[\(（\[【][^)）\]】]*[\(（\[【]')  # 중첩 괄호
_LONG_LIST_RE = re.compile(r'(?:[^,，、]+[,，、]){4,}')  # 5개 이상 나열
_TABLE_RE = re.compile(r'^\|.+\|$', re.MULTILINE)  # 마크다운 표
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```|`[^`]+`')  # 코드 블록

# 문장 분리 패턴 (한국어 + 영어)
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?。])\s+|\n+')

_EMPTY_RESULT = {
    'factors': {
        'sentence_length': {'score': 100.0, 'avg_length': 0.0},
        'abbreviation_density': {'score': 100.0, 'count': 0, 'density': 0.0},
        'number_density': {'score': 100.0, 'count': 0, 'density': 0.0},
        'parenthetical_density': {'score': 100.0, 'count': 0},
        'complex_structure': {'score': 100.0, 'issues': []},
    },
    'speakability_score': 100.0,
    'problem_sentences': [],
    'suggestions': ['콘텐츠가 비어 있습니다.'],
}

_FACTOR_WEIGHTS = {
    'sentence_length': 0.25,
    'abbreviation_density': 0.20,
    'number_density': 0.20,
    'parenthetical_density': 0.15,
    'complex_structure': 0.20,
}


def _compute_speakability_score(factors: dict) -> float:
    """요소별 점수의 가중 평균으로 종합 점수를 계산합니다."""
    score = sum(factors[k]['score'] * _FACTOR_WEIGHTS[k] for k in _FACTOR_WEIGHTS)
    return round(max(0.0, min(100.0, score)), 1)


def _collect_factors(content: str, sentences: list) -> dict:
    """5가지 음성 적합성 요소를 수집합니다."""
    total_chars = len(content.strip())
    return {
        'sentence_length': _analyze_sentence_length(sentences),
        'abbreviation_density': _analyze_abbreviations(content, total_chars),
        'number_density': _analyze_numbers(content, total_chars),
        'parenthetical_density': _analyze_parentheticals(content, sentences),
        'complex_structure': _analyze_complex_structure(content, sentences),
    }


def analyze_speakability(content: str) -> dict:
    """콘텐츠의 음성 적합성을 분석합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        factors, speakability_score, problem_sentences, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(content) if len(s.strip()) >= 5]
    if not sentences:
        sentences = [content.strip()]

    factors = _collect_factors(content, sentences)
    problem_sentences = _identify_problem_sentences(sentences, content)

    return {
        'factors': factors,
        'speakability_score': _compute_speakability_score(factors),
        'problem_sentences': problem_sentences,
        'suggestions': _generate_suggestions(factors, problem_sentences),
    }


def _analyze_sentence_length(sentences: list) -> dict:
    """문장 평균 길이 분석. 40자 이하가 이상적."""
    lengths = [len(s) for s in sentences]
    avg_length = sum(lengths) / len(lengths) if lengths else 0.0

    # 점수 계산: 20자 이하 → 100점, 40자 → 80점, 80자 → 40점, 120자+ → 0점
    if avg_length <= 20:
        score = 100.0
    elif avg_length <= 40:
        score = 100.0 - (avg_length - 20) * 1.0  # 20~40자: 100→80
    elif avg_length <= 80:
        score = 80.0 - (avg_length - 40) * 1.0  # 40~80자: 80→40
    elif avg_length <= 120:
        score = 40.0 - (avg_length - 80) * 1.0  # 80~120자: 40→0
    else:
        score = 0.0

    return {
        'score': round(max(0.0, min(100.0, score)), 1),
        'avg_length': round(avg_length, 1),
    }


def _analyze_abbreviations(content: str, total_chars: int) -> dict:
    """약어/두문자어 밀도 분석."""
    matches = _ABBREVIATION_RE.findall(content)
    count = len(matches)
    density = count / max(total_chars, 1) * 1000  # 1000자당 약어 수

    # 점수 계산: 밀도 0 → 100점, 5개/1000자 → 50점, 10개+ → 0점
    if density <= 1:
        score = 100.0
    elif density <= 5:
        score = 100.0 - (density - 1) * 12.5  # 1~5: 100→50
    elif density <= 10:
        score = 50.0 - (density - 5) * 10.0  # 5~10: 50→0
    else:
        score = 0.0

    return {
        'score': round(max(0.0, min(100.0, score)), 1),
        'count': count,
        'density': round(density, 2),
    }


def _analyze_numbers(content: str, total_chars: int) -> dict:
    """숫자/통계 밀도 분석."""
    matches = _NUMBER_RE.findall(content)
    count = len(matches)
    density = count / max(total_chars, 1) * 1000  # 1000자당 숫자 수

    # 점수 계산: 밀도 0~2 → 100점, 5 → 70점, 10 → 40점, 20+ → 0점
    if density <= 2:
        score = 100.0
    elif density <= 5:
        score = 100.0 - (density - 2) * 10.0  # 2~5: 100→70
    elif density <= 10:
        score = 70.0 - (density - 5) * 6.0  # 5~10: 70→40
    elif density <= 20:
        score = 40.0 - (density - 10) * 4.0  # 10~20: 40→0
    else:
        score = 0.0

    return {
        'score': round(max(0.0, min(100.0, score)), 1),
        'count': count,
        'density': round(density, 2),
    }


def _analyze_parentheticals(content: str, sentences: list) -> dict:
    """괄호 표현 밀도 분석."""
    matches = _PAREN_RE.findall(content)
    count = len(matches)
    sentence_count = max(len(sentences), 1)

    # 점수 계산: 문장 대비 괄호 비율
    ratio = count / sentence_count
    if ratio <= 0.1:
        score = 100.0
    elif ratio <= 0.3:
        score = 100.0 - (ratio - 0.1) * 150.0  # 0.1~0.3: 100→70
    elif ratio <= 0.5:
        score = 70.0 - (ratio - 0.3) * 150.0  # 0.3~0.5: 70→40
    elif ratio <= 1.0:
        score = 40.0 - (ratio - 0.5) * 80.0  # 0.5~1.0: 40→0
    else:
        score = 0.0

    return {
        'score': round(max(0.0, min(100.0, score)), 1),
        'count': count,
    }


def _analyze_complex_structure(content: str, sentences: list) -> dict:
    """복잡한 구조 탐지 (중첩 괄호, 긴 나열, 표, 코드 블록)."""
    issues = []

    # 중첩 괄호
    if _NESTED_PAREN_RE.search(content):
        issues.append('중첩 괄호가 포함되어 있습니다')

    # 긴 나열 (콤마 5개 이상)
    if _LONG_LIST_RE.search(content):
        issues.append('5개 이상의 항목이 나열되어 있습니다')

    # 마크다운 표
    if _TABLE_RE.search(content):
        issues.append('표 형식이 포함되어 있습니다')

    # 코드 블록
    if _CODE_BLOCK_RE.search(content):
        issues.append('코드 블록이 포함되어 있습니다')

    # 매우 긴 문장 (80자 초과)
    long_sentences = [s for s in sentences if len(s) > 80]
    if long_sentences:
        issues.append(f'{len(long_sentences)}개의 매우 긴 문장이 있습니다 (80자 초과)')

    # 점수 계산: 이슈 0개 → 100점, 각 이슈마다 -20점
    score = max(0.0, 100.0 - len(issues) * 20.0)

    return {
        'score': round(score, 1),
        'issues': issues,
    }


def _identify_problem_sentences(sentences: list, content: str) -> list:
    """음성에 부적합한 문장을 식별합니다."""
    problems = []

    for sentence in sentences:
        reasons = []

        # 긴 문장 (60자 초과)
        if len(sentence) > 60:
            reasons.append(f'문장이 {len(sentence)}자로 너무 깁니다 (40자 이하 권장)')

        # 약어 다수 포함
        abbrevs = _ABBREVIATION_RE.findall(sentence)
        if len(abbrevs) >= 2:
            reasons.append(f'약어가 {len(abbrevs)}개 포함되어 있습니다: {", ".join(abbrevs[:3])}')

        # 숫자 과다
        numbers = _NUMBER_RE.findall(sentence)
        if len(numbers) >= 3:
            reasons.append(f'숫자/통계가 {len(numbers)}개로 청취 시 혼란을 줄 수 있습니다')

        # 괄호 포함
        parens = _PAREN_RE.findall(sentence)
        if parens:
            reasons.append('괄호 표현이 포함되어 음성으로 전달하기 어렵습니다')

        if reasons:
            problems.append({
                'sentence': sentence[:100] + ('...' if len(sentence) > 100 else ''),
                'reason': '; '.join(reasons),
            })

    return problems


def _generate_suggestions(factors: dict, problem_sentences: list) -> list:
    """분석 결과 기반 개선 제안을 생성합니다."""
    suggestions = []

    # 문장 길이 관련
    avg_len = factors['sentence_length']['avg_length']
    if avg_len > 40:
        suggestions.append(
            f'평균 문장 길이가 {avg_len:.0f}자입니다. '
            f'40자 이하로 줄이면 음성 전달력이 향상됩니다.'
        )

    # 약어 관련
    if factors['abbreviation_density']['count'] > 0:
        suggestions.append(
            f"약어가 {factors['abbreviation_density']['count']}개 발견되었습니다. "
            f"첫 등장 시 풀어서 표기하면 TTS 품질이 개선됩니다."
        )

    # 숫자 관련
    if factors['number_density']['count'] > 3:
        suggestions.append(
            '숫자가 많습니다. 핵심 수치만 남기고 나머지는 '
            '"약 ~", "대략 ~" 등으로 표현하면 청취가 편합니다.'
        )

    # 괄호 관련
    if factors['parenthetical_density']['count'] > 0:
        suggestions.append(
            '괄호 표현을 별도 문장으로 풀어 쓰면 음성 재생 시 자연스럽습니다.'
        )

    # 복잡 구조 관련
    if factors['complex_structure']['issues']:
        suggestions.append(
            '복잡한 구조(표, 코드, 긴 나열 등)를 텍스트 설명으로 변환하세요.'
        )

    # 문제 문장이 많은 경우
    if len(problem_sentences) > 5:
        suggestions.append(
            f'{len(problem_sentences)}개 문장에서 문제가 발견되었습니다. '
            f'전반적인 문체 개선이 필요합니다.'
        )

    # 좋은 결과일 때
    if not suggestions:
        suggestions.append('콘텐츠가 음성 재생에 적합합니다.')

    return suggestions
