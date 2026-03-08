"""
콘텐츠 톤 분석 서비스

어휘/문장 패턴 기반 톤 분류 (AI 호출 없이 규칙 기반).
전문적, 캐주얼, 유머, 학술, 감성 5가지 톤을 점수화.
"""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# 톤별 지표 패턴 (한국어 + 영어)
_TONE_PATTERNS = {
    'professional': {
        'keywords': [
            '분석', '결과', '전략', '효율', '최적화', '프로세스', '시스템', '데이터',
            '성과', '목표', '구현', '설계', '관리', '평가', '보고', '기준',
            'analysis', 'strategy', 'optimize', 'implement', 'evaluate',
        ],
        'patterns': [
            r'~입니다', r'~합니다', r'~됩니다', r'~하였', r'~되었',
        ],
    },
    'casual': {
        'keywords': [
            '진짜', '완전', '대박', '꿀팁', '솔직히', '개인적으로', '사실',
            '근데', '좀', '엄청', '되게', '넘', '짱', '맞죠',
        ],
        'patterns': [
            r'~요!', r'ㅋㅋ', r'ㅎㅎ', r'~죠\?', r'~잖아',
        ],
    },
    'humor': {
        'keywords': [
            '웃긴', '재밌', '빵', '꿀잼', '반전', '충격', 'ㅋ', 'ㅎ',
            '농담', '코미디', '웃음',
        ],
        'patterns': [
            r'ㅋ{2,}', r'ㅎ{2,}', r'!{2,}', r'\?\!', r'~ㅋ',
        ],
    },
    'academic': {
        'keywords': [
            '연구', '논문', '이론', '가설', '실험', '통계', '변수', '상관관계',
            '방법론', '문헌', '인용', '결론', '고찰', '선행', '학술',
            'research', 'study', 'hypothesis', 'methodology', 'conclusion',
        ],
        'patterns': [
            r'\(\d{4}\)', r'et al\.', r'pp\.\s*\d+', r'참고문헌', r'각주',
        ],
    },
    'emotional': {
        'keywords': [
            '감동', '눈물', '가슴', '마음', '따뜻', '소중', '행복', '슬프',
            '그리움', '사랑', '위로', '공감', '감사', '희망', '꿈',
        ],
        'patterns': [
            r'\.{3,}', r'~$', r'♥', r'♡', r'❤',
        ],
    },
}

_EMPTY_RESULT = {
    'primary_tone': 'neutral',
    'scores': {tone: 0.0 for tone in _TONE_PATTERNS},
    'suggestions': [],
}


def analyze_tone(text: str) -> Dict:
    """텍스트의 톤을 분석합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        {
            "primary_tone": str,       # 가장 높은 점수의 톤
            "scores": dict,            # 각 톤별 0.0~1.0 점수
            "suggestions": list,       # 톤 개선 제안
        }
    """
    if not text or not text.strip():
        return dict(_EMPTY_RESULT)

    text_lower = text.lower()
    word_count = max(len(text.split()), 1)
    scores = _compute_tone_scores(text, text_lower, word_count)

    # 주요 톤 결정
    primary = max(scores, key=scores.get)
    if scores[primary] < 0.05:
        primary = 'neutral'

    return {
        'primary_tone': primary,
        'scores': scores,
        'suggestions': _generate_suggestions(primary, scores),
    }


def _compute_tone_scores(text: str, text_lower: str, word_count: int) -> Dict[str, float]:
    """톤별 점수를 계산합니다."""
    scores = {}
    for tone, indicators in _TONE_PATTERNS.items():
        keyword_hits = sum(1 for kw in indicators['keywords'] if kw in text_lower)
        keyword_score = min(keyword_hits / (word_count * 0.05 + 1), 1.0)

        pattern_hits = sum(
            len(re.findall(pat, text)) for pat in indicators['patterns']
        )
        pattern_score = min(pattern_hits / (word_count * 0.02 + 1), 1.0)

        scores[tone] = round(keyword_score * 0.6 + pattern_score * 0.4, 3)
    return scores


def _generate_suggestions(primary: str, scores: Dict[str, float]) -> List[str]:
    """톤 분석 결과에 따른 개선 제안을 생성합니다."""
    suggestions = []

    suggestion_map = {
        'professional': '전문적 톤이 강합니다. 독자 친화성을 높이려면 일상적 표현을 추가해 보세요.',
        'casual': '캐주얼한 톤입니다. 신뢰성을 높이려면 구체적 데이터나 사례를 추가해 보세요.',
        'humor': '유머러스한 톤입니다. 핵심 메시지가 희석되지 않도록 주의하세요.',
        'academic': '학술적 톤입니다. 일반 독자를 위해 핵심을 쉬운 말로 요약하는 단락을 추가해 보세요.',
        'emotional': '감성적 톤입니다. 설득력을 높이려면 객관적 근거를 함께 제시해 보세요.',
        'neutral': '톤이 명확하지 않습니다. 목표 독자에 맞는 어조를 선택해 보세요.',
    }

    if primary in suggestion_map:
        suggestions.append(suggestion_map[primary])

    # 점수가 균등하게 분산된 경우 (톤 일관성 부족)
    values = list(scores.values())
    if values and max(values) - min(values) < 0.1 and max(values) > 0:
        suggestions.append('톤이 여러 스타일에 걸쳐 있습니다. 하나의 톤으로 통일하면 가독성이 올라갑니다.')

    return suggestions
