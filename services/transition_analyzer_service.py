"""
연결어/전환 표현 분석 서비스

콘텐츠의 문단 간 연결어 사용을 분석하고,
부족한 곳에 적절한 전환 표현을 추천합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 한국어 연결어 사전 (유형별)
_TRANSITION_WORDS = {
    'addition': {
        'label': '추가/나열',
        'words': [
            '또한', '그리고', '아울러', '더불어', '뿐만 아니라', '게다가',
            '나아가', '더욱이', '이 외에도', '마찬가지로', '동시에',
            '첫째', '둘째', '셋째', '먼저', '다음으로',
        ],
    },
    'contrast': {
        'label': '대조/반전',
        'words': [
            '그러나', '하지만', '반면', '반대로', '그럼에도', '그런데',
            '오히려', '다만', '대신', '한편', '물론', '그렇지만',
            '에도 불구하고',
        ],
    },
    'cause': {
        'label': '인과/이유',
        'words': [
            '따라서', '그러므로', '그래서', '때문에', '덕분에', '결과적으로',
            '이로 인해', '왜냐하면', '그 결과', '이에 따라',
        ],
    },
    'example': {
        'label': '예시/설명',
        'words': [
            '예를 들어', '예컨대', '가령', '이를테면', '구체적으로',
            '특히', '실제로', '사실', '즉',
        ],
    },
    'conclusion': {
        'label': '결론/요약',
        'words': [
            '결론적으로', '요약하면', '정리하면', '결국', '마지막으로',
            '종합하면', '요컨대', '핵심은', '궁극적으로', '다시 말해',
        ],
    },
    'condition': {
        'label': '조건/가정',
        'words': [
            '만약', '만일', '가정하면', '경우에', '그렇다면', '그럴 때',
        ],
    },
    'time': {
        'label': '시간/순서',
        'words': [
            '이후', '그 후', '이전에', '동안', '현재', '최근',
            '과거에', '앞으로', '이때', '그때',
        ],
    },
}

# 전체 연결어 리스트 (빠른 검색용)
_ALL_TRANSITIONS = {}
for category, data in _TRANSITION_WORDS.items():
    for word in data['words']:
        _ALL_TRANSITIONS[word] = category


def analyze_transitions(content: str) -> dict:
    """콘텐츠의 연결어 사용을 분석합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            "transitions": [{"word": str, "category": str, "category_label": str, "paragraph": int}],
            "summary": {"total": int, "categories": dict, "density": float},
            "paragraph_analysis": [{"index": int, "has_transition": bool, "transitions": list}],
            "score": int (1~100),
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'transitions': [],
            'summary': {'total': 0, 'categories': {}, 'density': 0},
            'paragraph_analysis': [],
            'score': 0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) >= 5]
    if not paragraphs:
        return {
            'transitions': [],
            'summary': {'total': 0, 'categories': {}, 'density': 0},
            'paragraph_analysis': [],
            'score': 0,
            'suggestions': ['분석할 문단이 없습니다.'],
        }

    found_transitions = []
    category_counts = {}
    paragraph_analysis = []

    for idx, para in enumerate(paragraphs):
        para_transitions = []
        for word, category in _ALL_TRANSITIONS.items():
            if word in para:
                label = _TRANSITION_WORDS[category]['label']
                found_transitions.append({
                    'word': word,
                    'category': category,
                    'category_label': label,
                    'paragraph': idx,
                })
                para_transitions.append(word)
                category_counts[category] = category_counts.get(category, 0) + 1

        paragraph_analysis.append({
            'index': idx,
            'has_transition': len(para_transitions) > 0,
            'transitions': para_transitions,
        })

    total = len(found_transitions)
    # 문단 수 대비 연결어 밀도
    density = round(total / max(len(paragraphs), 1) * 100, 1)

    # 점수 계산 (0~100)
    score = _calculate_score(paragraphs, paragraph_analysis, category_counts)

    # 제안
    suggestions = _generate_suggestions(paragraphs, paragraph_analysis, category_counts, density)

    return {
        'transitions': found_transitions,
        'summary': {
            'total': total,
            'categories': {k: {'count': v, 'label': _TRANSITION_WORDS[k]['label']} for k, v in category_counts.items()},
            'density': density,
        },
        'paragraph_analysis': paragraph_analysis,
        'score': score,
        'suggestions': suggestions,
    }


def suggest_transitions(content: str) -> dict:
    """연결어가 부족한 문단에 전환 표현을 추천합니다.

    Args:
        content: 콘텐츠

    Returns:
        {
            "recommendations": [{"paragraph": int, "context": str, "suggested_words": list}],
            "general_tips": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'recommendations': [],
            'general_tips': ['콘텐츠가 비어 있습니다.'],
        }

    analysis = analyze_transitions(content)
    paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) >= 5]
    recommendations = []

    for pa in analysis['paragraph_analysis']:
        if pa['index'] == 0:
            continue  # 첫 문단은 연결어 불필요

        if not pa['has_transition']:
            para_text = paragraphs[pa['index']] if pa['index'] < len(paragraphs) else ''
            preview = para_text[:50] + '...' if len(para_text) > 50 else para_text

            # 이전 문단과의 관계를 추정하여 적절한 연결어 제안
            suggested = _suggest_for_context(paragraphs, pa['index'])
            recommendations.append({
                'paragraph': pa['index'],
                'context': preview,
                'suggested_words': suggested,
            })

    general_tips = [
        '매 문단 시작에 연결어를 넣을 필요는 없지만, 논리적 흐름이 끊기는 곳에는 추가하세요.',
        '같은 연결어를 반복하지 말고 다양한 표현을 사용하세요.',
        '인과(따라서), 대조(그러나), 예시(예를 들어) 연결어를 골고루 사용하면 글이 풍성해집니다.',
    ]

    return {
        'recommendations': recommendations,
        'general_tips': general_tips,
    }


def get_transition_categories() -> list:
    """사용 가능한 연결어 카테고리 목록을 반환합니다."""
    return [
        {'id': k, 'label': v['label'], 'count': len(v['words']), 'examples': v['words'][:3]}
        for k, v in _TRANSITION_WORDS.items()
    ]


def _calculate_score(paragraphs: list, para_analysis: list, categories: dict) -> int:
    """연결어 사용 점수를 계산합니다 (0~100)."""
    if len(paragraphs) <= 1:
        return 100  # 단일 문단은 연결어 불필요

    score = 50  # 기본 점수

    # 연결어 있는 문단 비율 (첫 문단 제외)
    paras_after_first = para_analysis[1:] if len(para_analysis) > 1 else []
    if paras_after_first:
        with_transition = sum(1 for p in paras_after_first if p['has_transition'])
        ratio = with_transition / len(paras_after_first)
        score += int(ratio * 30)  # 최대 +30

    # 카테고리 다양성
    if len(categories) >= 3:
        score += 15
    elif len(categories) >= 2:
        score += 10
    elif len(categories) >= 1:
        score += 5

    # 과다 사용 페널티
    total_transitions = sum(categories.values())
    if total_transitions > len(paragraphs) * 2:
        score -= 10  # 문단당 2개 초과 시 감점

    return max(0, min(100, score))


def _suggest_for_context(paragraphs: list, idx: int) -> list:
    """문맥에 따라 적절한 연결어를 추천합니다."""
    # 간단한 휴리스틱: 위치 기반 추천
    total = len(paragraphs)
    ratio = idx / max(total - 1, 1)

    if ratio >= 0.8:
        # 마지막 부근 → 결론 연결어
        return ['결론적으로', '정리하면', '마지막으로']
    elif ratio <= 0.3:
        # 초반 → 추가/나열
        return ['또한', '더불어', '아울러']
    else:
        # 중간 → 다양한 유형
        return ['한편', '또한', '예를 들어', '그러나']


def _generate_suggestions(paragraphs: list, para_analysis: list, categories: dict, density: float) -> list:
    """분석 결과에 따른 개선 제안을 생성합니다."""
    suggestions = []

    if len(paragraphs) <= 1:
        suggestions.append('문단이 1개뿐입니다. 연결어 분석이 의미 없습니다.')
        return suggestions

    # 연결어 없는 문단 비율
    paras_after_first = para_analysis[1:]
    without = [p for p in paras_after_first if not p['has_transition']]
    if len(without) > len(paras_after_first) * 0.6:
        suggestions.append(f'연결어가 부족합니다. {len(without)}개 문단에 연결어가 없습니다.')

    # 카테고리 편중
    if categories:
        max_cat = max(categories.values())
        total = sum(categories.values())
        if max_cat / total > 0.7 and total >= 3:
            dominant = max(categories, key=categories.get)
            label = _TRANSITION_WORDS[dominant]['label']
            suggestions.append(f'"{label}" 연결어에 편중되어 있습니다. 다양한 유형을 사용해 보세요.')

    # 특정 유형 부재
    important_types = {'cause', 'contrast', 'example'}
    present_types = set(categories.keys())
    missing = important_types - present_types
    if missing and len(paragraphs) >= 5:
        missing_labels = [_TRANSITION_WORDS[m]['label'] for m in missing]
        suggestions.append(f'{", ".join(missing_labels)} 유형의 연결어가 없습니다. 글의 논리성을 높이려면 추가해 보세요.')

    if not suggestions:
        suggestions.append('연결어가 적절히 사용되고 있습니다.')

    return suggestions
