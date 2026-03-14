"""
Promotional Tone Saturation Checker 서비스

콘텐츠에서 과도한 세일즈/홍보 표현 밀도를 측정하여
신뢰도 저하 구간을 식별합니다.
AI API 호출 없이 규칙 기반으로 동작합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── 4가지 프로모션 표현 카테고리 ──

_PROMO_PATTERNS = {
    'superlative': {
        'phrases': [
            '최고의', '최초의', '유일한', '세계 최고', '업계 최초',
            '최상의', '최적의', '최강', '넘버원', '독보적',
        ],
        'phrases_en': [
            'best', 'greatest', 'ultimate', '#1', 'number one',
            'top-rated', 'world-class', 'unmatched', 'unrivaled',
        ],
    },
    'hype': {
        'phrases': [
            '혁신적', '혁명적', '놀라운', '압도적', '게임체인저',
            '획기적', '경이로운', '파격적', '센세이셔널', '충격적',
        ],
        'phrases_en': [
            'incredible', 'revolutionary', 'amazing', 'mind-blowing',
            'game-changer', 'groundbreaking', 'unbelievable', 'jaw-dropping',
            'insane', 'epic',
        ],
    },
    'urgency': {
        'phrases': [
            '지금 바로', '한정', '마감 임박', '놓치면', '서두르세요',
            '오늘만', '선착순', '품절 임박', '긴급', '즉시',
        ],
        'phrases_en': [
            'limited time', 'act now', "don't miss", 'hurry',
            'last chance', 'expires soon', 'only today', 'rush',
            'before it\'s gone', 'while supplies last',
        ],
    },
    'guarantee': {
        'phrases': [
            '보장', '확실', '무조건', '100%', '틀림없',
            '반드시', '절대적', '완벽한',
        ],
        'phrases_en': [
            'guaranteed', 'proven', 'risk-free', 'no-risk',
            'money-back', 'foolproof', 'surefire', 'fail-proof',
        ],
    },
}

# 카테고리별 기본 impact 레벨
_CATEGORY_IMPACT = {
    'superlative': 'medium',
    'hype': 'high',
    'urgency': 'high',
    'guarantee': 'medium',
}

# 핫스팟 판정 밀도 임계값 (단락 내 프로모션 표현 / 총 단어 수)
_HOTSPOT_DENSITY_THRESHOLD = 0.05


_EMPTY_RESULT = {
    'detections': [],
    'summary': {'total': 0, 'by_category': {}, 'promo_density': 0.0},
    'hotspots': [],
    'trust_score': 100.0,
    'suggestions': [],
}


def check_promotional_tone(content: str) -> dict:
    """콘텐츠의 프로모션 표현 밀도를 분석합니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        {
            "detections": [{"phrase": str, "category": str, "sentence": str, "impact": str}],
            "summary": {"total": int, "by_category": dict, "promo_density": float},
            "hotspots": [{"paragraph_index": int, "density": float, "excerpt": str}],
            "trust_score": float,  # 0-100 (높을수록 신뢰)
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    detections = _detect_promotions(_split_sentences(content))
    summary = _build_summary(detections, content)
    hotspots = _find_hotspots(_split_paragraphs(content))
    trust_score = _calculate_trust_score(detections, summary, hotspots)

    return {
        'detections': detections,
        'summary': summary,
        'hotspots': hotspots,
        'trust_score': trust_score,
        'suggestions': _generate_suggestions(detections, summary, hotspots, trust_score),
    }


def _split_sentences(content: str) -> list:
    """콘텐츠를 문장 단위로 분리합니다."""
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    return [s.strip() for s in raw if s.strip()]


def _split_paragraphs(content: str) -> list:
    """콘텐츠를 단락 단위로 분리합니다."""
    raw = re.split(r'\n\s*\n|\n{2,}', content)
    return [p.strip() for p in raw if p.strip()]


def _detect_promotions(sentences: list) -> list:
    """문장별로 프로모션 표현을 감지합니다."""
    detections = []

    for sentence in sentences:
        sentence_lower = sentence.lower()

        for category, patterns in _PROMO_PATTERNS.items():
            # 한국어 패턴
            for phrase in patterns['phrases']:
                if phrase in sentence:
                    impact = _assess_impact(phrase, category, sentence)
                    detections.append({
                        'phrase': phrase,
                        'category': category,
                        'sentence': sentence,
                        'impact': impact,
                    })

            # 영어 패턴 (대소문자 무시)
            for phrase in patterns['phrases_en']:
                if phrase.lower() in sentence_lower:
                    impact = _assess_impact(phrase, category, sentence)
                    detections.append({
                        'phrase': phrase,
                        'category': category,
                        'sentence': sentence,
                        'impact': impact,
                    })

    return detections


def _assess_impact(phrase: str, category: str, sentence: str) -> str:
    """개별 감지 항목의 신뢰 저하 영향도를 평가합니다."""
    base_impact = _CATEGORY_IMPACT.get(category, 'medium')

    # 느낌표와 함께 사용되면 영향도 상승
    if '!' in sentence or '!!' in sentence:
        if base_impact == 'low':
            return 'medium'
        return 'high'

    # 한 문장에 여러 대문자/강조 표현이 있으면 영향도 상승
    caps_count = len(re.findall(r'[A-Z]{2,}', sentence))
    if caps_count >= 2 and base_impact != 'high':
        return 'high'

    return base_impact


def _count_words(text: str) -> int:
    """한국어+영어 혼합 텍스트의 단어 수를 추정합니다."""
    # 영어 단어
    en_words = re.findall(r'[A-Za-z]+', text)
    # 한국어는 공백 기준 어절
    ko_words = re.findall(r'[가-힣]+', text)
    return len(en_words) + len(ko_words)


def _build_summary(detections: list, content: str) -> dict:
    """감지 결과의 요약 통계를 생성합니다."""
    by_category = {}
    for d in detections:
        cat = d['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    total = len(detections)
    word_count = _count_words(content)
    promo_density = total / word_count if word_count > 0 else 0.0

    return {
        'total': total,
        'by_category': by_category,
        'promo_density': round(promo_density, 4),
    }


def _find_hotspots(paragraphs: list) -> list:
    """단락별 프로모션 밀도를 분석하여 핫스팟을 찾습니다."""
    hotspots = []

    for idx, paragraph in enumerate(paragraphs):
        sentences = _split_sentences(paragraph)
        detections = _detect_promotions(sentences)
        word_count = _count_words(paragraph)

        if word_count == 0:
            continue

        density = len(detections) / word_count
        if density >= _HOTSPOT_DENSITY_THRESHOLD:
            # 발췌: 최대 80자
            excerpt = paragraph[:80] + ('...' if len(paragraph) > 80 else '')
            hotspots.append({
                'paragraph_index': idx,
                'density': round(density, 4),
                'excerpt': excerpt,
            })

    return hotspots


def _calculate_trust_score(detections: list, summary: dict, hotspots: list) -> float:
    """신뢰 점수를 계산합니다 (0-100, 높을수록 신뢰).

    감점 요소:
    - 프로모션 표현 수: 건당 -5점
    - high impact: 건당 추가 -3점
    - 핫스팟 존재: 개당 -5점
    - 높은 밀도: 밀도 0.1 초과 시 추가 -10점
    """
    score = 100.0

    # 표현 수 감점
    score -= summary['total'] * 5

    # high impact 추가 감점
    high_count = sum(1 for d in detections if d['impact'] == 'high')
    score -= high_count * 3

    # 핫스팟 감점
    score -= len(hotspots) * 5

    # 높은 밀도 추가 감점
    if summary['promo_density'] > 0.1:
        score -= 10

    # 0~100 범위로 클램핑
    return round(max(0.0, min(100.0, score)), 1)


_CATEGORY_SUGGESTIONS = {
    'superlative': (2, '최상급 표현이 다수 사용되었습니다. "최고의", "유일한" 등을 구체적 수치나 근거로 대체하세요.'),
    'hype': (1, '과장 표현("혁신적", "놀라운" 등)이 감지되었습니다. 구체적인 성과나 데이터로 뒷받침하세요.'),
    'urgency': (1, '긴급성 유도 표현("지금 바로", "한정" 등)이 포함되어 있습니다. 정보 전달 콘텐츠에서는 지양하세요.'),
    'guarantee': (1, '보장/확실 표현이 사용되었습니다. 법적 리스크를 고려하여 조건부 표현으로 완화하세요.'),
}


def _generate_suggestions(detections: list, summary: dict, hotspots: list, trust_score: float) -> list:
    """분석 결과 기반 개선 제안을 생성합니다."""
    if not detections:
        return ['프로모션 표현이 감지되지 않았습니다. 콘텐츠 신뢰도가 높습니다.']

    suggestions = _category_suggestions(summary['by_category'])

    if hotspots:
        indices = ', '.join(str(h['paragraph_index'] + 1) for h in hotspots)
        suggestions.append(f'단락 {indices}에 프로모션 표현이 집중되어 있습니다. 해당 구간을 중심으로 표현을 완화하세요.')

    if trust_score < 50:
        suggestions.append('전체 신뢰 점수가 낮습니다(50점 미만). 콘텐츠 전반에 걸쳐 객관적 톤으로 재작성을 권장합니다.')

    return suggestions


def _category_suggestions(by_cat: dict) -> list:
    """카테고리별 감지 수에 따른 제안 목록을 반환합니다."""
    suggestions = []
    for cat, (threshold, message) in _CATEGORY_SUGGESTIONS.items():
        if by_cat.get(cat, 0) >= threshold:
            suggestions.append(message)
    return suggestions
