"""
파워워드 분석 서비스

콘텐츠에서 파워워드(감정/행동 유발 단어)를 감지하고,
카테고리별 분포와 추가 제안을 제공합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 파워워드 사전 (카테고리별)
_POWER_WORDS = {
    'urgency': {
        'label': '긴급성',
        'words': [
            '지금', '바로', '즉시', '오늘', '한정', '마감', '서둘러',
            '놓치지', '마지막', '긴급', '급히', '당장',
        ],
    },
    'emotion': {
        'label': '감정',
        'words': [
            '감동', '행복', '기쁨', '설렘', '두려움', '분노', '슬픔',
            '놀라운', '충격', '감격', '희열', '짜릿', '벅찬',
        ],
    },
    'trust': {
        'label': '신뢰',
        'words': [
            '검증된', '입증된', '공식', '인증', '전문가', '연구',
            '데이터', '통계', '사실', '보장', '안전', '신뢰',
        ],
    },
    'curiosity': {
        'label': '호기심',
        'words': [
            '비밀', '숨겨진', '알려지지', '미공개', '특별한', '독점',
            '처음', '유일', '신비', '궁금', '의외', '반전',
        ],
    },
    'value': {
        'label': '가치',
        'words': [
            '무료', '할인', '혜택', '보너스', '선물', '특가',
            '절약', '이득', '효율', '최적', '극대화', '핵심',
        ],
    },
    'authority': {
        'label': '권위',
        'words': [
            '최고', '최초', '유일', '1위', '선두', '대표',
            '세계적', '글로벌', '업계', '리더', '선도', '혁신',
        ],
    },
    'action': {
        'label': '행동 유도',
        'words': [
            '시작', '도전', '변화', '성장', '발전', '달성',
            '실현', '완성', '극복', '정복', '실천', '도약',
        ],
    },
}

# 전체 워드 매핑 (빠른 검색용)
_ALL_POWER_WORDS = {}
for category, data in _POWER_WORDS.items():
    for word in data['words']:
        _ALL_POWER_WORDS[word] = category


_EMPTY_RESULT = {
    'found': [],
    'summary': {'total_found': 0, 'unique_count': 0, 'density': 0, 'categories': {}},
    'score': 0,
    'suggestions': [],
}


def _scan_power_words(words: list) -> tuple:
    """단어 목록에서 파워워드를 감지합니다.

    Returns:
        (found_list, found_map, category_counts)
    """
    found_map = {}
    category_counts = {}

    for word in words:
        for pw, cat in _ALL_POWER_WORDS.items():
            if pw in word:
                found_map[pw] = found_map.get(pw, 0) + 1
                category_counts[cat] = category_counts.get(cat, 0) + 1
                break

    found_list = [
        {'word': pw, 'category': _ALL_POWER_WORDS[pw],
         'category_label': _POWER_WORDS[_ALL_POWER_WORDS[pw]]['label'], 'count': count}
        for pw, count in sorted(found_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return found_list, found_map, category_counts


def analyze_power_words(content: str) -> dict:
    """콘텐츠에서 파워워드를 분석합니다.

    Returns:
        found, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    words = re.findall(r'[가-힣]{2,}', content)
    total_words = len(words)
    found, found_map, category_counts = _scan_power_words(words)

    total_found = sum(found_map.values())
    unique_count = len(found_map)
    density = round((total_found / max(total_words, 1)) * 100, 2)

    cat_summary = {cat: {'label': _POWER_WORDS[cat]['label'], 'count': count}
                   for cat, count in category_counts.items()}

    return {
        'found': found,
        'summary': {'total_found': total_found, 'unique_count': unique_count,
                     'density': density, 'categories': cat_summary},
        'score': _calculate_score(density, unique_count, category_counts),
        'suggestions': _generate_suggestions(density, unique_count, category_counts, total_words),
    }


def suggest_power_words(content: str, goal: str = 'engagement') -> dict:
    """목표에 맞는 파워워드를 추천합니다.

    Args:
        content: 콘텐츠
        goal: 목표 (engagement, conversion, trust, viral)

    Returns:
        {"goal": str, "recommended_categories": list, "words": list[str]}
    """
    goal_map = {
        'engagement': ['emotion', 'curiosity', 'action'],
        'conversion': ['urgency', 'value', 'action'],
        'trust': ['trust', 'authority'],
        'viral': ['emotion', 'curiosity', 'urgency'],
    }

    if goal not in goal_map:
        goal = 'engagement'

    categories = goal_map[goal]
    recommended = []
    for cat in categories:
        recommended.extend(_POWER_WORDS[cat]['words'][:5])

    # 이미 사용 중인 단어 제외
    if content:
        recommended = [w for w in recommended if w not in content]

    return {
        'goal': goal,
        'recommended_categories': [
            {'id': c, 'label': _POWER_WORDS[c]['label']} for c in categories
        ],
        'words': recommended[:15],
    }


def get_power_word_categories() -> list:
    """파워워드 카테고리 목록을 반환합니다."""
    return [
        {'id': k, 'label': v['label'], 'count': len(v['words']), 'examples': v['words'][:4]}
        for k, v in _POWER_WORDS.items()
    ]


def _calculate_score(density: float, unique: int, categories: dict) -> int:
    """파워워드 활용 점수 (0~100)."""
    score = 30

    # 밀도: 2~5%가 적정
    if 2 <= density <= 5:
        score += 30
    elif 1 <= density < 2:
        score += 15
    elif 5 < density <= 8:
        score += 20
    elif density > 8:
        score += 10  # 과다

    # 다양성
    cat_count = len(categories)
    if cat_count >= 4:
        score += 25
    elif cat_count >= 3:
        score += 20
    elif cat_count >= 2:
        score += 10
    elif cat_count >= 1:
        score += 5

    # 고유 단어 수
    if unique >= 10:
        score += 15
    elif unique >= 5:
        score += 10
    elif unique >= 2:
        score += 5

    return max(0, min(100, score))


def _generate_suggestions(density: float, unique: int, categories: dict, total_words: int) -> list:
    """분석 결과에 따른 제안."""
    suggestions = []

    if total_words < 10:
        suggestions.append('콘텐츠가 너무 짧아 파워워드 분석이 제한적입니다.')
        return suggestions

    if density < 1:
        suggestions.append('파워워드가 거의 없습니다. 감정적/행동 유발 단어를 추가하면 참여율이 높아집니다.')
    elif density > 8:
        suggestions.append('파워워드가 과다합니다. 과장된 느낌을 줄 수 있으니 자연스럽게 줄여보세요.')

    present = set(categories.keys())
    if 'urgency' not in present and 'action' not in present:
        suggestions.append('긴급성/행동 유도 파워워드를 추가하면 CTA 효과가 높아집니다.')

    if 'trust' not in present:
        suggestions.append('신뢰 파워워드("검증된", "데이터", "연구")를 추가하면 설득력이 높아집니다.')

    if len(categories) == 1:
        suggestions.append('한 카테고리에 편중되어 있습니다. 다양한 유형의 파워워드를 사용해 보세요.')

    if not suggestions:
        suggestions.append('파워워드가 적절히 활용되고 있습니다.')

    return suggestions
