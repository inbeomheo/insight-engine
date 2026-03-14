"""
CTA(Call-to-Action) 최적화 서비스

콘텐츠에서 CTA를 감지하고, 위치/유형/강도를 분석하며,
목표에 맞는 CTA를 제안합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# CTA 패턴 (유형별)
_CTA_PATTERNS = {
    'subscribe': [
        r'구독', r'팔로우', r'뉴스레터', r'알림\s*설정',
        r'subscribe', r'follow',
    ],
    'share': [
        r'공유', r'퍼뜨려', r'알려\s*주', r'전달',
        r'share', r'spread',
    ],
    'comment': [
        r'댓글', r'의견.*남겨', r'생각.*알려', r'어떻게\s*생각',
        r'comment', r'let\s+me\s+know',
    ],
    'click': [
        r'클릭', r'확인.*해\s*보', r'링크', r'자세히\s*보',
        r'click', r'check\s+out', r'read\s+more',
    ],
    'purchase': [
        r'구매', r'구입', r'결제', r'주문', r'신청',
        r'buy', r'purchase', r'order',
    ],
    'download': [
        r'다운로드', r'내려받', r'받아\s*보',
        r'download', r'get\s+it',
    ],
    'signup': [
        r'가입', r'등록', r'회원', r'시작하',
        r'sign\s*up', r'register', r'join',
    ],
}

# CTA 강도 키워드
_URGENCY_WORDS = [
    '지금', '바로', '즉시', '오늘', '한정', '무료', '특별',
    '놓치지', '서두르', '마감', '마지막',
    'now', 'today', 'free', 'limited', 'hurry', 'last',
]

_ACTION_VERBS = [
    '해보세요', '하세요', '해주세요', '시작하세요', '만들어보세요',
    '경험해보세요', '확인하세요', '받으세요', '참여하세요',
]

# 목표별 CTA 템플릿
_CTA_TEMPLATES = {
    'awareness': [
        '이 글이 도움이 되셨다면 공유해 주세요.',
        '더 많은 콘텐츠를 보려면 구독하세요.',
        '관련 글도 함께 확인해 보세요.',
    ],
    'engagement': [
        '여러분의 생각을 댓글로 남겨 주세요.',
        '이 주제에 대해 어떻게 생각하시나요?',
        '경험을 공유해 주시면 다른 독자들에게도 도움이 됩니다.',
    ],
    'conversion': [
        '지금 바로 시작해 보세요.',
        '무료 체험을 신청하세요.',
        '한정 혜택을 놓치지 마세요.',
    ],
}


_EMPTY_RESULT = {
    'ctas': [],
    'summary': {'total': 0, 'types': {}, 'avg_strength': 0},
    'position_distribution': {'top': 0, 'middle': 0, 'bottom': 0},
    'suggestions': [],
}


def _scan_ctas(sentences: list) -> tuple:
    """문장 목록에서 CTA를 스캔합니다.

    Returns:
        (ctas, type_counts, position_counts)
    """
    ctas = []
    type_counts = {}
    position_counts = {'top': 0, 'middle': 0, 'bottom': 0}
    total = len(sentences)

    for idx, sentence in enumerate(sentences):
        cta_type = _detect_cta_type(sentence)
        if cta_type:
            position = _get_position(idx, total)
            ctas.append({
                'text': sentence,
                'type': cta_type,
                'position': position,
                'strength': _calculate_strength(sentence),
            })
            type_counts[cta_type] = type_counts.get(cta_type, 0) + 1
            position_counts[position] += 1

    return ctas, type_counts, position_counts


def analyze_ctas(content: str) -> dict:
    """콘텐츠에서 CTA를 감지하고 분석합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        ctas, summary, position_distribution, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', content) if len(s.strip()) >= 3]
    if not sentences:
        return {**_EMPTY_RESULT, 'suggestions': ['분석할 문장이 없습니다.']}

    ctas, type_counts, position_counts = _scan_ctas(sentences)
    avg_strength = sum(c['strength'] for c in ctas) / max(len(ctas), 1)

    return {
        'ctas': ctas,
        'summary': {
            'total': len(ctas),
            'types': type_counts,
            'avg_strength': round(avg_strength, 1),
        },
        'position_distribution': position_counts,
        'suggestions': _generate_suggestions(ctas, position_counts, len(sentences)),
    }


def suggest_ctas(content: str, goal: str = 'engagement') -> dict:
    """목표에 맞는 CTA를 제안합니다.

    Args:
        content: 콘텐츠
        goal: 목표 (awareness, engagement, conversion)

    Returns:
        {"goal": str, "suggestions": list[str], "placement_tips": list[str]}
    """
    if goal not in _CTA_TEMPLATES:
        goal = 'engagement'

    suggestions = list(_CTA_TEMPLATES[goal])

    # 콘텐츠에서 주제 추출하여 맞춤 제안
    if content and content.strip():
        topic_words = _extract_topic_words(content)
        if topic_words:
            topic = topic_words[0]
            if goal == 'engagement':
                suggestions.append(f'{topic}에 대한 여러분의 경험을 댓글로 공유해 주세요.')
            elif goal == 'awareness':
                suggestions.append(f'{topic} 관련 최신 소식을 받아보세요.')

    placement_tips = [
        '글 상단(도입부 직후)에 1개 배치하면 초기 이탈을 줄일 수 있습니다.',
        '글 하단(결론)에 반드시 CTA를 배치하세요.',
        '긴 글(2000자+)은 중간에 추가 CTA를 넣으면 효과적입니다.',
    ]

    return {
        'goal': goal,
        'goal_label': {'awareness': '인지도', 'engagement': '참여', 'conversion': '전환'}[goal],
        'suggestions': suggestions,
        'placement_tips': placement_tips,
    }


def _detect_cta_type(sentence: str) -> str | None:
    """문장에서 CTA 유형을 감지합니다."""
    lower = sentence.lower()
    for cta_type, patterns in _CTA_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                return cta_type
    # 액션 동사로 끝나는 문장도 CTA로 간주
    for verb in _ACTION_VERBS:
        if verb in sentence:
            return 'action'
    return None


def _get_position(idx: int, total: int) -> str:
    """문장 위치를 상/중/하로 분류합니다."""
    ratio = idx / max(total - 1, 1)
    if ratio <= 0.25:
        return 'top'
    elif ratio >= 0.75:
        return 'bottom'
    return 'middle'


def _calculate_strength(sentence: str) -> int:
    """CTA 강도를 1~10으로 계산합니다."""
    score = 3  # 기본 점수

    # 긴급성 단어
    urgency_count = sum(1 for w in _URGENCY_WORDS if w in sentence.lower())
    score += min(urgency_count * 2, 4)

    # 느낌표
    if '!' in sentence:
        score += 1

    # 직접 호칭 (여러분, 당신)
    if re.search(r'여러분|당신|독자', sentence):
        score += 1

    return max(1, min(10, score))


def _extract_topic_words(content: str) -> list:
    """콘텐츠에서 주요 주제어를 추출합니다."""
    # 한국어 명사 패턴 (2~6자 한글 단어)
    words = re.findall(r'[가-힣]{2,6}', content)
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    # 빈도 상위
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    # 불용어 제외
    stopwords = {'있습니다', '합니다', '입니다', '됩니다', '것입니다', '위해', '통해', '대한', '하는', '이는'}
    return [w for w, _ in sorted_words if w not in stopwords][:5]


def _generate_suggestions(ctas: list, positions: dict, total_sentences: int) -> list:
    """CTA 분석 결과에 따른 개선 제안을 생성합니다."""
    suggestions = []

    if len(ctas) == 0:
        suggestions.append('CTA가 감지되지 않았습니다. 독자의 행동을 유도하는 문구를 추가하세요.')
        return suggestions

    if positions['bottom'] == 0:
        suggestions.append('글 마지막에 CTA가 없습니다. 결론부에 CTA를 추가하세요.')

    if positions['top'] == 0 and total_sentences > 10:
        suggestions.append('글 상단에 CTA가 없습니다. 도입부에 가벼운 CTA를 배치하면 참여율이 높아집니다.')

    avg_strength = sum(c['strength'] for c in ctas) / len(ctas)
    if avg_strength < 4:
        suggestions.append('CTA 강도가 약합니다. "지금", "바로" 같은 긴급성 단어를 추가해 보세요.')

    types = set(c['type'] for c in ctas)
    if len(types) == 1:
        suggestions.append('CTA 유형이 단일합니다. 다양한 유형(공유, 댓글, 구독)을 혼합해 보세요.')

    if not suggestions:
        suggestions.append('CTA가 적절히 배치되어 있습니다.')

    return suggestions
