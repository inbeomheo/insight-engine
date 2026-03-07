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


def score_engagement(content: str) -> dict:
    """콘텐츠의 참여 유도력을 종합 평가합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            "score": int (0~100),
            "grade": str (A~F),
            "breakdown": {factor: {"score": int, "max": int, "details": str}},
            "strengths": list[str],
            "weaknesses": list[str],
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'score': 0,
            'grade': 'F',
            'breakdown': {},
            'strengths': [],
            'weaknesses': [],
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    breakdown = {}
    total = 0

    # 1. 질문 사용
    questions = re.findall(r'[?？]', content)
    q_score = min(len(questions) * 3, _WEIGHTS['questions'])
    breakdown['questions'] = {
        'score': q_score, 'max': _WEIGHTS['questions'],
        'details': f'질문 {len(questions)}개 감지',
    }
    total += q_score

    # 2. 감정 표현
    emo_count = sum(1 for w in _EMOTIONAL_WORDS if w in content)
    e_score = min(emo_count * 3, _WEIGHTS['emotional'])
    breakdown['emotional'] = {
        'score': e_score, 'max': _WEIGHTS['emotional'],
        'details': f'감정 표현 {emo_count}개',
    }
    total += e_score

    # 3. CTA
    cta_patterns = [r'하세요', r'해보세요', r'확인', r'클릭', r'구독', r'공유', r'시작']
    cta_count = sum(1 for p in cta_patterns if re.search(p, content))
    c_score = min(cta_count * 3, _WEIGHTS['cta'])
    breakdown['cta'] = {
        'score': c_score, 'max': _WEIGHTS['cta'],
        'details': f'CTA 패턴 {cta_count}개',
    }
    total += c_score

    # 4. 시각적 요소
    lists = len(re.findall(r'^\s*[-*•]\s', content, re.MULTILINE))
    code_blocks = len(re.findall(r'```', content))
    numbered = len(re.findall(r'^\s*\d+[.)]\s', content, re.MULTILINE))
    visual_count = lists + code_blocks + numbered
    v_score = min(visual_count * 2, _WEIGHTS['visuals'])
    breakdown['visuals'] = {
        'score': v_score, 'max': _WEIGHTS['visuals'],
        'details': f'리스트 {lists}개, 코드블록 {code_blocks // 2}개, 번호목록 {numbered}개',
    }
    total += v_score

    # 5. 구조
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))
    paragraphs = len([p for p in content.split('\n\n') if p.strip()])
    s_score = 0
    if headings >= 3:
        s_score += 8
    elif headings >= 1:
        s_score += 4
    if paragraphs >= 5:
        s_score += 7
    elif paragraphs >= 3:
        s_score += 4
    s_score = min(s_score, _WEIGHTS['structure'])
    breakdown['structure'] = {
        'score': s_score, 'max': _WEIGHTS['structure'],
        'details': f'헤딩 {headings}개, 문단 {paragraphs}개',
    }
    total += s_score

    # 6. 독자 참여 표현
    inter_count = sum(1 for p in _INTERACTION_PHRASES if p in content)
    i_score = min(inter_count * 2, _WEIGHTS['interaction'])
    breakdown['interaction'] = {
        'score': i_score, 'max': _WEIGHTS['interaction'],
        'details': f'참여 표현 {inter_count}개',
    }
    total += i_score

    # 7. 스토리텔링
    story_count = sum(1 for m in _STORY_MARKERS if m in content)
    st_score = min(story_count * 2, _WEIGHTS['storytelling'])
    breakdown['storytelling'] = {
        'score': st_score, 'max': _WEIGHTS['storytelling'],
        'details': f'스토리 마커 {story_count}개',
    }
    total += st_score

    # 8. 구체성 (숫자/통계)
    numbers = re.findall(r'\d+[%만억천개건]', content)
    spec_score = min(len(numbers) * 2, _WEIGHTS['specificity'])
    breakdown['specificity'] = {
        'score': spec_score, 'max': _WEIGHTS['specificity'],
        'details': f'구체적 수치 {len(numbers)}개',
    }
    total += spec_score

    # 등급
    grade = _score_to_grade(total)

    # 강점/약점
    strengths = [k for k, v in breakdown.items() if v['score'] >= v['max'] * 0.6]
    weaknesses = [k for k, v in breakdown.items() if v['score'] <= v['max'] * 0.2]

    # 제안
    suggestions = _generate_suggestions(breakdown, weaknesses)

    return {
        'score': total,
        'grade': grade,
        'breakdown': breakdown,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'suggestions': suggestions,
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
