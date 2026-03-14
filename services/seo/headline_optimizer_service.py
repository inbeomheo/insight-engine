"""
스마트 헤드라인 최적화 서비스

규칙 기반으로 제목의 품질을 분석하고 개선 제안을 제공합니다.
감정어, 파워워드, 숫자, 질문 패턴, 길이 등을 종합 평가합니다.
AI 호출 없이 즉시 결과 반환.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 감정 유발 단어 (한국어)
_EMOTIONAL_WORDS = {
    'positive': [
        '완벽', '최고', '필수', '핵심', '비밀', '무료', '쉬운', '빠른',
        '강력', '효과적', '성공', '추천', '인기', '검증', '확실',
    ],
    'urgency': [
        '지금', '당장', '오늘', '마감', '한정', '급', '서둘러',
        '마지막', '놓치면', '기회',
    ],
    'curiosity': [
        '비밀', '진실', '실체', '이유', '방법', '비결', '숨겨진',
        '모르는', '반전', '충격',
    ],
}

# 파워워드 (클릭 유도력 높은 단어)
_POWER_WORDS = [
    '방법', '가이드', '팁', '비결', '전략', '노하우', '리뷰',
    '비교', '분석', '정리', '모음', '추천', '필독', '꿀팁',
    '실전', '실수', '주의', '함정', '차이', '변화',
]

# 숫자 패턴
_NUMBER_PATTERN = re.compile(r'\d+')

# 질문 패턴
_QUESTION_PATTERNS = [
    re.compile(r'[?？]$'),
    re.compile(r'^왜\s'),
    re.compile(r'^어떻게\s'),
    re.compile(r'^무엇이?\s'),
    re.compile(r'할까[?？]?$'),
    re.compile(r'일까[?？]?$'),
    re.compile(r'인가[?？]?$'),
]


_EMPTY_ANALYSIS = {
    'length_score': 0,
    'emotional_score': 0,
    'power_word_score': 0,
    'number_score': 0,
    'pattern_type': 'unknown',
}

_EMPTY_RESULT = {
    'score': 0,
    'grade': 'F',
    'analysis': dict(_EMPTY_ANALYSIS),
    'suggestions': ['제목이 비어 있습니다.'],
    'optimized_titles': [],
}


def _compute_headline_scores(title: str) -> tuple:
    """제목의 개별 점수와 종합 점수를 계산합니다.

    Returns:
        (analysis, total_score)
    """
    length_score = _score_length(title)
    emotional_score = _score_emotional(title)
    power_word_score = _score_power_words(title)
    number_score = _score_numbers(title)
    pattern_type = _detect_pattern(title)
    pattern_bonus = _pattern_bonus(pattern_type)

    total = round(
        length_score * 0.25
        + emotional_score * 0.25
        + power_word_score * 0.20
        + number_score * 0.15
        + pattern_bonus * 0.15
    )
    total = max(0, min(100, total))

    analysis = {
        'length_score': length_score,
        'emotional_score': emotional_score,
        'power_word_score': power_word_score,
        'number_score': number_score,
        'pattern_type': pattern_type,
    }
    return analysis, total


def optimize_headline(title: str, content: str = '') -> dict:
    """제목을 분석하고 최적화 제안을 제공합니다.

    Args:
        title: 분석할 제목
        content: 참고용 본문 (선택, 현재 미사용)

    Returns:
        score, grade, analysis, suggestions, optimized_titles를 포함하는 dict
    """
    if not title or not title.strip():
        return dict(_EMPTY_RESULT)

    title = title.strip()
    analysis, total = _compute_headline_scores(title)

    suggestions = _generate_suggestions(
        title, analysis['length_score'], analysis['emotional_score'],
        analysis['power_word_score'], analysis['number_score'],
        analysis['pattern_type'],
    )

    return {
        'score': total,
        'grade': _score_to_grade(total),
        'analysis': analysis,
        'suggestions': suggestions,
        'optimized_titles': _generate_optimized_titles(title, suggestions),
    }


def _score_to_grade(score: int) -> str:
    if score >= 80:
        return 'A'
    elif score >= 65:
        return 'B'
    elif score >= 50:
        return 'C'
    elif score >= 35:
        return 'D'
    else:
        return 'F'


def _score_length(title: str) -> int:
    """제목 길이 점수 (한국어 기준 15~30자 최적)."""
    length = len(title)
    if 15 <= length <= 30:
        return 100
    elif 10 <= length < 15 or 30 < length <= 40:
        return 70
    elif 5 <= length < 10 or 40 < length <= 50:
        return 40
    else:
        return 20


def _score_emotional(title: str) -> int:
    """감정 유발 단어 점수."""
    score = 30  # 기본
    for category, words in _EMOTIONAL_WORDS.items():
        found = [w for w in words if w in title]
        if found:
            score += min(35, len(found) * 15)
    return min(100, score)


def _score_power_words(title: str) -> int:
    """파워워드 포함 점수."""
    found = [w for w in _POWER_WORDS if w in title]
    if not found:
        return 30
    return min(100, 30 + len(found) * 20)


def _score_numbers(title: str) -> int:
    """숫자 포함 점수 (리스트형 제목 효과)."""
    numbers = _NUMBER_PATTERN.findall(title)
    if not numbers:
        return 40
    return 80


def _detect_pattern(title: str) -> str:
    """제목 패턴 유형 감지."""
    # 질문형
    for pat in _QUESTION_PATTERNS:
        if pat.search(title):
            return 'question'

    # 리스트형 (숫자로 시작)
    if re.match(r'^\d+', title):
        return 'list'

    # How-to형
    if re.match(r'^(방법|가이드|노하우|팁)', title) or '하는 법' in title or '하는 방법' in title:
        return 'how_to'

    # 비교형
    if 'vs' in title.lower() or '비교' in title or '차이' in title:
        return 'comparison'

    # 기본 서술형
    return 'statement'


def _pattern_bonus(pattern_type: str) -> int:
    """패턴별 보너스 점수."""
    bonuses = {
        'question': 80,
        'list': 90,
        'how_to': 85,
        'comparison': 75,
        'statement': 50,
    }
    return bonuses.get(pattern_type, 50)


def _generate_suggestions(
    title: str,
    length_score: int,
    emotional_score: int,
    power_word_score: int,
    number_score: int,
    pattern_type: str,
) -> list:
    suggestions = []

    if length_score < 70:
        length = len(title)
        if length < 15:
            suggestions.append('제목이 너무 짧습니다. 15~30자가 최적입니다.')
        else:
            suggestions.append('제목이 너무 깁니다. 30자 이내로 줄여보세요.')

    if emotional_score < 50:
        suggestions.append('감정을 자극하는 단어를 추가해보세요 (예: 필수, 핵심, 비결).')

    if power_word_score < 50:
        suggestions.append('파워워드를 포함하면 클릭률이 향상됩니다 (예: 가이드, 팁, 전략).')

    if number_score < 60:
        suggestions.append('숫자를 포함한 리스트형 제목은 CTR이 36% 높습니다.')

    if pattern_type == 'statement':
        suggestions.append('질문형이나 리스트형으로 변환하면 클릭률이 향상됩니다.')

    if not suggestions:
        suggestions.append('잘 최적화된 제목입니다.')

    return suggestions


def _generate_optimized_titles(title: str, suggestions: list) -> list:
    """규칙 기반 제목 변형 생성."""
    optimized = []

    # 질문형 변환
    if '?' not in title and '？' not in title:
        core = re.sub(r'[.!]$', '', title)
        optimized.append(f'{core}, 알고 계셨나요?')

    # 숫자 추가 (리스트형)
    if not _NUMBER_PATTERN.search(title):
        optimized.append(f'{title} — 5가지 핵심 포인트')

    # How-to 변환
    if '방법' not in title and '가이드' not in title:
        core = re.sub(r'[.!?？]$', '', title)
        optimized.append(f'{core} 완벽 가이드')

    return optimized[:3]
