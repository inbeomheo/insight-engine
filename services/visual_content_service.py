"""
시각 콘텐츠 제안 서비스

콘텐츠를 분석하여 삽입하면 좋을 시각 콘텐츠(이미지, 차트, 인포그래픽,
다이어그램, 표, 스크린샷)를 규칙 기반으로 제안합니다.
AI API 호출 없이 순수 규칙 기반으로 동작합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# --- 키워드 사전 ---

# 차트 관련
_CHART_TREND_KEYWORDS = ['증가', '감소', '변화', '추이', '비교', '성장', '하락', '상승']
_CHART_TIMESERIES_KEYWORDS = ['연도별', '월별', '분기별', '주별', '일별', '년간', '기간별']
_NUMBER_UNIT_PATTERN = re.compile(
    r'\d+(?:\.\d+)?(?:\s*)(?:%|퍼센트|원|달러|배|명|건|개|회|억|만|천|위|점)'
)

# 표 관련
_TABLE_COMPARE_KEYWORDS = ['vs', 'VS', '대비', '반면', '차이점', '비교하면', '에 비해']
_TABLE_FEATURE_KEYWORDS = ['특징', '장단점', '장점', '단점', '비교', '차이']

# 인포그래픽 관련
_STEP_PATTERNS = [
    re.compile(r'(\d+)\s*단계'),
    re.compile(r'(\d+)\.\s'),
    re.compile(r'(첫째|둘째|셋째|넷째|다섯째|여섯째|일곱째|여덟째)'),
    re.compile(r'(first|second|third|fourth|fifth)', re.IGNORECASE),
]
_INFOGRAPHIC_KEYWORDS = ['핵심', '요약', '정리', '한눈에', '요점']

# 다이어그램 관련
_DIAGRAM_KEYWORDS = ['연결', '구성', '흐름', '아키텍처', '구조', '계층', '관계', '의존성']
_DIAGRAM_DIRECTION_PATTERN = re.compile(r'[가-힣A-Za-z]+\s*(?:→|->|에서\s+[가-힣A-Za-z]+(?:로|으로))')
_DIAGRAM_SYSTEM_KEYWORDS = ['시스템', '프로세스', '워크플로우', '파이프라인', '네트워크']

# 이미지 관련
_IMAGE_KEYWORDS = ['화면', '인터페이스', '외관', '모습', '디자인', '레이아웃']
_IMAGE_EXAMPLE_KEYWORDS = ['예시', '사례', '실제로', '실물', '모양']

# 스크린샷 관련
_SCREENSHOT_KEYWORDS = ['클릭', '선택', '설정', '메뉴', '버튼', '탭', '체크박스', '드롭다운', '입력']

# 기존 시각 요소 감지 패턴
_EXISTING_VISUAL_PATTERNS = {
    'markdown_image': re.compile(r'!\['),
    'html_img': re.compile(r'<img\b', re.IGNORECASE),
    'markdown_table': re.compile(r'\|[-:]+\|'),
    'code_block': re.compile(r'```'),
}

# 긴 단락 기준 (글자 수)
_LONG_PARAGRAPH_THRESHOLD = 300


def _split_paragraphs(content: str) -> list[str]:
    """콘텐츠를 단락 단위로 분리한다."""
    paragraphs = re.split(r'\n\s*\n', content.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _count_pattern_matches(text: str, pattern: re.Pattern) -> int:
    """정규식 매치 수를 센다."""
    return len(pattern.findall(text))


def _count_keyword_matches(text: str, keywords: list[str]) -> int:
    """키워드 출현 횟수를 센다."""
    count = 0
    for kw in keywords:
        count += text.count(kw)
    return count


def _detect_existing_visuals(content: str) -> list[str]:
    """이미 존재하는 시각 요소를 감지한다."""
    found = []
    labels = {
        'markdown_image': '마크다운 이미지',
        'html_img': 'HTML 이미지',
        'markdown_table': '마크다운 테이블',
        'code_block': '코드 블록',
    }
    for key, pattern in _EXISTING_VISUAL_PATTERNS.items():
        if pattern.search(content):
            found.append(labels[key])
    return found


def _count_existing_visuals(content: str) -> int:
    """기존 시각 요소의 총 개수를 센다."""
    total = 0
    for pattern in _EXISTING_VISUAL_PATTERNS.values():
        total += len(pattern.findall(content))
    return total


def _calc_visual_density(content: str, paragraphs: list[str]) -> float:
    """시각 콘텐츠 밀도 점수를 계산한다 (0~100)."""
    if not paragraphs:
        return 0.0
    existing_count = _count_existing_visuals(content)
    # 3단락당 1개 시각 요소가 이상적
    ideal_count = max(len(paragraphs) / 3, 1)
    score = (existing_count / ideal_count) * 100
    return min(score, 100.0)


def _analyze_chart(paragraphs: list[str]) -> list[dict]:
    """차트 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        number_count = _count_pattern_matches(para, _NUMBER_UNIT_PATTERN)
        has_trend = _count_keyword_matches(para, _CHART_TREND_KEYWORDS) > 0
        has_timeseries = _count_keyword_matches(para, _CHART_TIMESERIES_KEYWORDS) > 0

        # 숫자 데이터 3개+ 또는 (추이 키워드 + 숫자 2개+) 또는 시계열 키워드 + 숫자
        trigger = False
        if number_count >= 3:
            trigger = True
        elif has_trend and number_count >= 2:
            trigger = True
        elif has_timeseries and number_count >= 1:
            trigger = True

        if trigger:
            priority = 'high' if number_count >= 5 else 'medium'
            suggestions.append({
                'type': 'chart',
                'reason': '숫자 데이터가 포함되어 차트로 시각화하면 이해도가 높아집니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '데이터 추이를 보여주는 바 차트 또는 라인 차트',
                'priority': priority,
            })
    return suggestions


def _analyze_table(paragraphs: list[str]) -> list[dict]:
    """표 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        compare_count = _count_keyword_matches(para, _TABLE_COMPARE_KEYWORDS)
        has_feature_kw = _count_keyword_matches(para, _TABLE_FEATURE_KEYWORDS) > 0

        # 쉼표/줄바꿈으로 구분된 항목 수 (간이 추정)
        comma_items = len(re.findall(r'[,，]', para))
        # 비교 대상 수 추정
        compare_targets = len(re.findall(r'[가-힣A-Za-z]+(?:와|과|,)\s*[가-힣A-Za-z]+', para))

        trigger = False
        if compare_count >= 3:
            trigger = True
        elif comma_items >= 5:
            trigger = True
        elif has_feature_kw and compare_targets >= 2:
            trigger = True

        if trigger:
            priority = 'high' if compare_count >= 5 or comma_items >= 7 else 'medium'
            suggestions.append({
                'type': 'table',
                'reason': '비교 항목이 많아 표로 정리하면 한눈에 파악할 수 있습니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '항목별 비교 표',
                'priority': priority,
            })
    return suggestions


def _analyze_infographic(paragraphs: list[str]) -> list[dict]:
    """인포그래픽 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        step_count = 0
        for pattern in _STEP_PATTERNS:
            step_count += len(pattern.findall(para))

        stat_count = _count_pattern_matches(para, _NUMBER_UNIT_PATTERN)
        has_summary_kw = _count_keyword_matches(para, _INFOGRAPHIC_KEYWORDS) > 0

        trigger = False
        if step_count >= 3:
            trigger = True
        elif stat_count >= 3 and has_summary_kw:
            trigger = True
        elif has_summary_kw and step_count >= 2:
            trigger = True

        if trigger:
            priority = 'high' if step_count >= 4 else 'medium'
            suggestions.append({
                'type': 'infographic',
                'reason': '단계별 프로세스를 인포그래픽으로 표현하면 직관적입니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '프로세스 흐름 또는 핵심 통계 인포그래픽',
                'priority': priority,
            })
    return suggestions


def _analyze_diagram(paragraphs: list[str]) -> list[dict]:
    """다이어그램 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        struct_count = _count_keyword_matches(para, _DIAGRAM_KEYWORDS)
        direction_count = _count_pattern_matches(para, _DIAGRAM_DIRECTION_PATTERN)
        system_count = _count_keyword_matches(para, _DIAGRAM_SYSTEM_KEYWORDS)

        trigger = False
        if struct_count >= 2:
            trigger = True
        elif direction_count >= 1:
            trigger = True
        elif system_count >= 1 and struct_count >= 1:
            trigger = True

        if trigger:
            total_kw = struct_count + system_count
            priority = 'high' if total_kw >= 3 else 'medium'
            suggestions.append({
                'type': 'diagram',
                'reason': '구조나 흐름이 설명되어 다이어그램으로 시각화하면 명확해집니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '시스템 구조 또는 데이터 흐름 다이어그램',
                'priority': priority,
            })
    return suggestions


def _analyze_image(paragraphs: list[str]) -> list[dict]:
    """이미지 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        has_visual_kw = _count_keyword_matches(para, _IMAGE_KEYWORDS) > 0
        has_example_kw = _count_keyword_matches(para, _IMAGE_EXAMPLE_KEYWORDS) > 0
        is_long = len(para) >= _LONG_PARAGRAPH_THRESHOLD

        trigger = False
        if has_visual_kw:
            trigger = True
        elif has_example_kw:
            trigger = True
        elif is_long:
            trigger = True

        if trigger:
            priority = 'medium'
            if has_visual_kw and has_example_kw:
                priority = 'high'
            elif is_long and not has_visual_kw and not has_example_kw:
                priority = 'low'
            suggestions.append({
                'type': 'image',
                'reason': '시각적 참고 이미지를 추가하면 독자의 이해를 돕습니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '관련 이미지 또는 예시 사진',
                'priority': priority,
            })
    return suggestions


def _analyze_screenshot(paragraphs: list[str]) -> list[dict]:
    """스크린샷 제안 트리거를 분석한다."""
    suggestions = []
    for i, para in enumerate(paragraphs):
        ui_count = _count_keyword_matches(para, _SCREENSHOT_KEYWORDS)
        step_count = 0
        for pattern in _STEP_PATTERNS:
            step_count += len(pattern.findall(para))
        has_steps = step_count >= 2

        trigger = False
        if ui_count >= 2:
            trigger = True
        elif has_steps and ui_count >= 1:
            trigger = True

        if trigger:
            priority = 'high' if ui_count >= 3 else 'medium'
            suggestions.append({
                'type': 'screenshot',
                'reason': 'UI 조작 설명에 스크린샷을 추가하면 따라하기 쉬워집니다',
                'location': f'{i + 1}번째 단락 뒤',
                'description': '해당 UI 화면의 스크린샷',
                'priority': priority,
            })
    return suggestions


_EMPTY_VISUAL_RESULT = {
    'suggestions': [],
    'summary': {'total_suggestions': 0, 'by_type': {}, 'visual_density_score': 0.0},
    'existing_visuals': [],
    'recommendations': [],
}

_ANALYZERS = [
    _analyze_chart, _analyze_table, _analyze_infographic,
    _analyze_diagram, _analyze_image, _analyze_screenshot,
]

_TYPE_RECOMMENDATIONS = {
    'chart': '숫자 데이터를 차트로 시각화하는 것을 권장합니다',
    'table': '비교 항목을 표로 정리하면 한눈에 파악할 수 있습니다',
    'infographic': '단계별 프로세스를 인포그래픽으로 표현하면 직관적입니다',
    'diagram': '시스템 구조를 다이어그램으로 표현하면 명확해집니다',
    'screenshot': 'UI 가이드에 스크린샷을 추가하면 따라하기 쉬워집니다',
}


def _collect_all_suggestions(paragraphs: list[str]) -> list[dict]:
    """6종 분석기를 실행하여 시각 콘텐츠 제안을 수집합니다."""
    results = []
    for analyzer in _ANALYZERS:
        results.extend(analyzer(paragraphs))
    return results


def _build_recommendations(
    by_type: dict[str, int],
    density_score: float,
    has_suggestions: bool,
) -> list[str]:
    """타입별 집계와 밀도 점수로 추천 문구를 생성합니다."""
    recs = []
    if density_score < 30:
        recs.append('시각 콘텐츠를 추가하면 가독성이 향상됩니다')
    for vis_type, msg in _TYPE_RECOMMENDATIONS.items():
        if by_type.get(vis_type, 0) > 0:
            recs.append(msg)
    if not has_suggestions and not recs:
        recs.append('현재 콘텐츠는 시각 요소가 충분합니다')
    return recs


def suggest_visuals(content: str) -> dict:
    """콘텐츠를 분석하여 시각 콘텐츠 삽입 제안을 생성합니다.

    Args:
        content: 분석할 텍스트 콘텐츠 (마크다운 포함 가능)

    Returns:
        suggestions, summary, existing_visuals, recommendations를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_VISUAL_RESULT)

    paragraphs = _split_paragraphs(content)
    all_suggestions = _collect_all_suggestions(paragraphs)
    density_score = _calc_visual_density(content, paragraphs)

    by_type: dict[str, int] = {}
    for s in all_suggestions:
        by_type[s['type']] = by_type.get(s['type'], 0) + 1

    return {
        'suggestions': all_suggestions,
        'summary': {
            'total_suggestions': len(all_suggestions),
            'by_type': by_type,
            'visual_density_score': round(density_score, 1),
        },
        'existing_visuals': _detect_existing_visuals(content),
        'recommendations': _build_recommendations(by_type, density_score, bool(all_suggestions)),
    }
