"""
콘텐츠 참여 점수 서비스

콘텐츠의 참여 유도력을 종합적으로 평가합니다.
질문, CTA, 감정, 시각적 요소, 구조 등을 분석하여 점수화합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 참여 유도 요소 가중치
_WEIGHTS = {
    'questions': 15,       # 질문 사용
    'emotional': 15,       # 감정 표현
    'cta': 15,             # 행동 유도
    'visuals': 10,         # 시각적 요소 (리스트, 코드 등)
    'structure': 15,       # 구조 (헤딩, 문단)
    'interaction': 10,     # 독자 참여 유도 표현
    'storytelling': 10,    # 스토리텔링 요소
    'specificity': 10,     # 구체적 수치/예시
}

# 감정 단어
_EMOTIONAL_WORDS = [
    '놀라', '충격', '감동', '기쁨', '흥미', '재미', '신기', '대박',
    '최고', '완벽', '필수', '중요', '핵심', '비밀', '숨겨진',
]

# 독자 참여 표현
_INTERACTION_PHRASES = [
    '여러분', '당신', '우리', '함께', '생각해', '경험',
    '어떠신가요', '어떻게 생각', '공감', '댓글', '의견',
]

# 스토리텔링 마커
_STORY_MARKERS = [
    '경험', '사례', '이야기', '사연', '에피소드', '계기',
    '처음에', '그때', '결국', '알고 보니', '사실은',
]


def _score_questions(content: str) -> tuple:
    """질문 사용 점수."""
    count = len(re.findall(r'[?？]', content))
    score = min(count * 3, _WEIGHTS['questions'])
    return score, f'질문 {count}개 감지'


def _score_emotional(content: str) -> tuple:
    """감정 표현 점수."""
    count = sum(1 for w in _EMOTIONAL_WORDS if w in content)
    score = min(count * 3, _WEIGHTS['emotional'])
    return score, f'감정 표현 {count}개'


def _score_cta(content: str) -> tuple:
    """행동 유도(CTA) 점수."""
    patterns = [r'하세요', r'해보세요', r'확인', r'클릭', r'구독', r'공유', r'시작']
    count = sum(1 for p in patterns if re.search(p, content))
    score = min(count * 3, _WEIGHTS['cta'])
    return score, f'CTA 패턴 {count}개'


def _score_visuals(content: str) -> tuple:
    """시각적 요소 점수."""
    lists = len(re.findall(r'^\s*[-*•]\s', content, re.MULTILINE))
    code_blocks = len(re.findall(r'```', content))
    numbered = len(re.findall(r'^\s*\d+[.)]\s', content, re.MULTILINE))
    total = lists + code_blocks + numbered
    score = min(total * 2, _WEIGHTS['visuals'])
    return score, f'리스트 {lists}개, 코드블록 {code_blocks // 2}개, 번호목록 {numbered}개'


def _score_structure(content: str) -> tuple:
    """구조(헤딩, 문단) 점수."""
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))
    paragraphs = len([p for p in content.split('\n\n') if p.strip()])
    score = 0
    if headings >= 3:
        score += 8
    elif headings >= 1:
        score += 4
    if paragraphs >= 5:
        score += 7
    elif paragraphs >= 3:
        score += 4
    score = min(score, _WEIGHTS['structure'])
    return score, f'헤딩 {headings}개, 문단 {paragraphs}개'


def _score_interaction(content: str) -> tuple:
    """독자 참여 표현 점수."""
    count = sum(1 for p in _INTERACTION_PHRASES if p in content)
    score = min(count * 2, _WEIGHTS['interaction'])
    return score, f'참여 표현 {count}개'


def _score_storytelling(content: str) -> tuple:
    """스토리텔링 요소 점수."""
    count = sum(1 for m in _STORY_MARKERS if m in content)
    score = min(count * 2, _WEIGHTS['storytelling'])
    return score, f'스토리 마커 {count}개'


def _score_specificity(content: str) -> tuple:
    """구체성(숫자/통계) 점수."""
    numbers = re.findall(r'\d+[%만억천개건]', content)
    score = min(len(numbers) * 2, _WEIGHTS['specificity'])
    return score, f'구체적 수치 {len(numbers)}개'


# 채점 함수 디스패치 테이블
_SCORERS = [
    ('questions', _score_questions),
    ('emotional', _score_emotional),
    ('cta', _score_cta),
    ('visuals', _score_visuals),
    ('structure', _score_structure),
    ('interaction', _score_interaction),
    ('storytelling', _score_storytelling),
    ('specificity', _score_specificity),
]


_EMPTY_RESULT = {
    'score': 0,
    'grade': 'F',
    'breakdown': {},
    'strengths': [],
    'weaknesses': [],
    'suggestions': ['콘텐츠가 비어 있습니다.'],
}


def _evaluate_factors(content: str) -> tuple:
    """모든 참여 요소를 평가합니다.

    Returns:
        (breakdown, total_score)
    """
    breakdown = {}
    total = 0
    for factor, scorer in _SCORERS:
        factor_score, details = scorer(content)
        breakdown[factor] = {
            'score': factor_score, 'max': _WEIGHTS[factor], 'details': details,
        }
        total += factor_score
    return breakdown, total


def score_engagement(content: str) -> dict:
    """콘텐츠의 참여 유도력을 종합 평가합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        score, grade, breakdown, strengths, weaknesses, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    breakdown, total = _evaluate_factors(content)
    strengths = [k for k, v in breakdown.items() if v['score'] >= v['max'] * 0.6]
    weaknesses = [k for k, v in breakdown.items() if v['score'] <= v['max'] * 0.2]

    return {
        'score': total,
        'grade': _score_to_grade(total),
        'breakdown': breakdown,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'suggestions': _generate_suggestions(breakdown, weaknesses),
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
    return 'F'


def _generate_suggestions(breakdown: dict, weaknesses: list) -> list:
    suggestions = []
    tips = {
        'questions': '독자에게 질문을 던져보세요. "어떻게 생각하시나요?" 같은 표현이 참여를 유도합니다.',
        'emotional': '감정적 표현을 추가하세요. 독자가 공감할 수 있는 단어를 사용해 보세요.',
        'cta': '행동 유도 문구(CTA)를 추가하세요. "시작해 보세요", "확인해 보세요" 등.',
        'visuals': '리스트나 번호 목록을 활용하면 시각적 가독성이 높아집니다.',
        'structure': '헤딩(##)과 문단 구분을 활용하면 구조가 명확해집니다.',
        'interaction': '"여러분", "함께" 같은 표현으로 독자와의 연결감을 높이세요.',
        'storytelling': '구체적 사례나 경험담을 추가하면 몰입도가 높아집니다.',
        'specificity': '구체적 수치(%, 건수)를 포함하면 신뢰도가 높아집니다.',
    }

    for w in weaknesses[:3]:
        if w in tips:
            suggestions.append(tips[w])

    if not suggestions:
        suggestions.append('전반적으로 참여 유도력이 좋습니다.')

    return suggestions
