"""
정보 이득 분석 서비스

콘텐츠의 정보 이득(고유 가치)을 분석하여
경쟁 콘텐츠 대비 차별화 수준을 측정합니다.
AI API 호출 없이 규칙 기반으로 동작합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# 5가지 정보 이득 신호 패턴
_SIGNAL_PATTERNS = {
    'unique_data': {
        'description': '고유 수치/통계',
        # 숫자 + 단위(%, 배, 개, 명, 원, 달러, 건, 시간, 분, 초 등)
        'patterns': [
            re.compile(r'\d[\d,]*\.?\d*\s*(%|퍼센트|배|개|명|원|달러|건|시간|분|초|만|억|조|kg|km|GB|MB|TB)'),
            re.compile(r'(약|대략|평균|최대|최소|총)\s*\d[\d,]*\.?\d*'),
        ],
    },
    'examples': {
        'description': '구체적 사례/예시',
        'patterns': [
            re.compile(r'예를\s*들어'),
            re.compile(r'예시\s*[:：]'),
            re.compile(r'사례\s*[:：]'),
            re.compile(r'[Cc]ase\s*[Ss]tudy'),
            re.compile(r'실제로\s'),
            re.compile(r'구체적으로\s'),
        ],
    },
    'counterpoints': {
        'description': '반론/반례',
        'patterns': [
            re.compile(r'반면[\s,]'),
            re.compile(r'그러나[\s,]'),
            re.compile(r'하지만[\s,]'),
            re.compile(r'다만[\s,]'),
            re.compile(r'한계[\s가이은는]'),
            re.compile(r'단점[\s이은는]'),
            re.compile(r'반론[\s이은는]'),
        ],
    },
    'original_insights': {
        'description': '독자적 관점',
        'patterns': [
            re.compile(r'필자는'),
            re.compile(r'제\s*경험'),
            re.compile(r'우리\s*팀'),
            re.compile(r'직접\s*테스트'),
            re.compile(r'실험\s*결과'),
            re.compile(r'개인적으로'),
            re.compile(r'저는\s'),
        ],
    },
    'actionable_tips': {
        'description': '실행 가능한 팁',
        'patterns': [
            re.compile(r'[가-힣]+하세요'),
            re.compile(r'[가-힣]+해보세요'),
            re.compile(r'팁\s*[:：]'),
            re.compile(r'방법\s*[:：]'),
            re.compile(r'체크리스트'),
            re.compile(r'추천\s*[:：]'),
            re.compile(r'[가-힣]+하는\s*것이\s*좋습니다'),
        ],
    },
}

# 신호별 만점 가중치 (총합 100)
_SIGNAL_WEIGHTS = {
    'unique_data': 25,
    'examples': 20,
    'counterpoints': 15,
    'original_insights': 25,
    'actionable_tips': 15,
}

# 각 신호의 최대 인정 개수 (과도한 반복 방지)
_MAX_COUNT_PER_SIGNAL = 5

# 등급 기준
_GRADE_THRESHOLDS = [
    (80, 'A'),
    (60, 'B'),
    (40, 'C'),
    (20, 'D'),
    (0, 'F'),
]

# 신호별 부족 판정 임계값
_WEAK_THRESHOLD = 1

# 신호별 개선 제안
_SIGNAL_SUGGESTIONS = {
    'unique_data': '구체적인 수치나 통계 데이터를 추가하면 신뢰도가 높아집니다.',
    'examples': '실제 사례나 예시를 추가하면 이해도가 향상됩니다.',
    'counterpoints': '반론이나 한계점을 함께 다루면 균형 잡힌 콘텐츠가 됩니다.',
    'original_insights': '직접 경험이나 독자적 분석을 추가하면 고유 가치가 높아집니다.',
    'actionable_tips': '실행 가능한 팁이나 체크리스트를 추가하면 실용성이 높아집니다.',
}


def analyze_information_gain(content: str, reference_contents: list = None) -> dict:
    """콘텐츠의 정보 이득을 분석합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        reference_contents: 비교 대상 경쟁 콘텐츠 리스트 (선택)

    Returns:
        {
            "signals": { signal_name: {"count": int, "items": list[str]} },
            "information_gain_score": float (0-100),
            "differentiation_score": float | None (0-100),
            "grade": str (A/B/C/D/F),
            "weak_areas": list[str],
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'signals': {name: {'count': 0, 'items': []} for name in _SIGNAL_PATTERNS},
            'information_gain_score': 0.0,
            'differentiation_score': None,
            'grade': 'F',
            'weak_areas': list(_SIGNAL_PATTERNS.keys()),
            'suggestions': ['콘텐츠가 비어 있습니다. 분석할 텍스트를 입력해 주세요.'],
        }

    # 1. 5가지 신호 분석
    signals = _detect_signals(content)

    # 2. 정보 이득 점수 계산
    score = _calculate_score(signals)

    # 3. 등급 부여
    grade = _assign_grade(score)

    # 4. 레퍼런스 대비 차별화 점수
    diff_score = None
    if reference_contents:
        diff_score = _calculate_differentiation(content, reference_contents)

    # 5. 부족 영역 및 제안
    weak_areas = _find_weak_areas(signals)
    suggestions = _generate_suggestions(weak_areas, signals, score)

    return {
        'signals': signals,
        'information_gain_score': round(score, 1),
        'differentiation_score': round(diff_score, 1) if diff_score is not None else None,
        'grade': grade,
        'weak_areas': weak_areas,
        'suggestions': suggestions,
    }


def _detect_signals(content: str) -> dict:
    """콘텐츠에서 5가지 정보 이득 신호를 감지합니다."""
    signals = {}

    for signal_name, config in _SIGNAL_PATTERNS.items():
        items = []
        for pattern in config['patterns']:
            for match in pattern.finditer(content):
                # 매칭된 텍스트의 주변 컨텍스트 추출 (앞뒤 20자)
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                snippet = content[start:end].strip()
                # 줄바꿈 제거
                snippet = re.sub(r'\s+', ' ', snippet)
                items.append(snippet)

        # 중복 제거 (동일 스니펫)
        seen = set()
        unique_items = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)

        signals[signal_name] = {
            'count': len(unique_items),
            'items': unique_items,
        }

    return signals


def _calculate_score(signals: dict) -> float:
    """신호 기반 정보 이득 점수를 계산합니다 (0-100)."""
    total = 0.0

    for signal_name, weight in _SIGNAL_WEIGHTS.items():
        count = signals.get(signal_name, {}).get('count', 0)
        # 최대 인정 개수로 정규화 (0~1)
        ratio = min(count, _MAX_COUNT_PER_SIGNAL) / _MAX_COUNT_PER_SIGNAL
        total += ratio * weight

    return total


def _assign_grade(score: float) -> str:
    """점수에 따라 등급을 부여합니다."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return 'F'


def _calculate_differentiation(content: str, reference_contents: list) -> float:
    """레퍼런스 대비 Jaccard 기반 차별화 점수를 계산합니다."""
    # 콘텐츠 키워드 추출 (2자 이상 한국어 + 3자 이상 영어)
    content_keywords = _extract_keywords(content)

    if not content_keywords:
        return 0.0

    # 레퍼런스 키워드 통합
    ref_keywords = set()
    for ref in reference_contents:
        if ref and ref.strip():
            ref_keywords.update(_extract_keywords(ref))

    if not ref_keywords:
        # 레퍼런스에 키워드가 없으면 완전 차별화
        return 100.0

    # 콘텐츠에만 있는 고유 키워드
    unique_to_content = content_keywords - ref_keywords

    # Jaccard 차별화: 고유 키워드 / 전체 합집합
    union = content_keywords | ref_keywords
    if not union:
        return 0.0

    differentiation = len(unique_to_content) / len(union) * 100
    return differentiation


def _extract_keywords(text: str) -> set:
    """텍스트에서 키워드를 추출합니다."""
    # 한국어 2자 이상
    ko_words = set(re.findall(r'[가-힣]{2,}', text))
    # 영어 3자 이상
    en_words = set(w.lower() for w in re.findall(r'[A-Za-z]{3,}', text))
    return ko_words | en_words


def _find_weak_areas(signals: dict) -> list:
    """부족한 신호 영역을 찾습니다."""
    weak = []
    for signal_name in _SIGNAL_PATTERNS:
        count = signals.get(signal_name, {}).get('count', 0)
        if count < _WEAK_THRESHOLD:
            weak.append(signal_name)
    return weak


def _generate_suggestions(weak_areas: list, signals: dict, score: float) -> list:
    """개선 제안을 생성합니다."""
    suggestions = []

    # 부족 영역별 제안
    for area in weak_areas:
        if area in _SIGNAL_SUGGESTIONS:
            suggestions.append(_SIGNAL_SUGGESTIONS[area])

    # 점수 기반 종합 제안
    if score < 20:
        suggestions.append('전반적으로 정보 이득이 부족합니다. 데이터, 사례, 독자적 관점을 보강해 주세요.')
    elif score < 40:
        suggestions.append('기본적인 정보는 포함되어 있으나, 차별화를 위해 더 구체적인 내용을 추가해 주세요.')

    return suggestions
