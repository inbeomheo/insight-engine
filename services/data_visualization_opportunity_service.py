"""
Data Visualization Opportunity 서비스

콘텐츠에서 데이터 시각화가 효과적인 구간을 찾아 추천합니다.
숫자 밀집 구간, 비교/추세 서술, 목록 데이터를 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 숫자 패턴 (퍼센트, 금액, 수량)
_NUMBER_RE = re.compile(r'(?:\d+(?:\.\d+)?(?:%|퍼센트|원|달러|건|개|명|회|배|만|억|조))', re.UNICODE)

# 비교 표현
_COMPARISON_RE = re.compile(
    r'(?:보다|대비|비교|증가|감소|상승|하락|차이|격차|높|낮|많|적|크|작)',
    re.UNICODE
)

# 추세/변화 표현
_TREND_RE = re.compile(
    r'(?:추세|트렌드|변화|추이|성장|감소세|증가세|하락세|전년|전월|전분기|동기|대비)',
    re.UNICODE
)

# 나열/목록 (3개 이상 항목)
_LIST_PATTERN = re.compile(r'(?:,|，)\s*(?:[^,，]{2,20}(?:,|，)\s*){2,}', re.UNICODE)

# 순위/랭킹 표현
_RANKING_RE = re.compile(r'(?:1위|2위|3위|순위|랭킹|상위|하위|TOP|top)', re.UNICODE)

# 영어 비교/추세
_EN_COMPARISON = re.compile(
    r'\b(?:compared\s+to|versus|increase|decrease|growth|decline|higher|lower|more\s+than|less\s+than)\b',
    re.IGNORECASE
)

# 차트 유형 매핑
_CHART_TYPES = {
    'comparison': '막대 차트 (Bar Chart)',
    'trend': '선 그래프 (Line Chart)',
    'proportion': '파이 차트 (Pie Chart)',
    'ranking': '수평 막대 차트 (Horizontal Bar)',
    'distribution': '히스토그램 (Histogram)',
    'list_data': '표 (Table)',
}


def _analyze_sentence(sentence: str) -> List[Dict]:
    """문장에서 시각화 기회를 감지합니다."""
    opportunities = []

    numbers = _NUMBER_RE.findall(sentence)
    has_comparison = bool(_COMPARISON_RE.search(sentence)) or bool(_EN_COMPARISON.search(sentence))
    has_trend = bool(_TREND_RE.search(sentence))
    has_ranking = bool(_RANKING_RE.search(sentence))

    # 숫자 2개 이상 + 비교 → 막대 차트
    if len(numbers) >= 2 and has_comparison:
        opportunities.append({
            'type': 'comparison',
            'chart': _CHART_TYPES['comparison'],
            'reason': f'숫자 {len(numbers)}개와 비교 표현 감지',
        })

    # 추세 표현 + 숫자 → 선 그래프
    if has_trend and len(numbers) >= 1:
        opportunities.append({
            'type': 'trend',
            'chart': _CHART_TYPES['trend'],
            'reason': '추세/변화 표현과 수치 데이터 감지',
        })

    # 퍼센트 여러 개 → 파이 차트
    pct_count = sum(1 for n in numbers if '%' in n or '퍼센트' in n)
    if pct_count >= 2:
        opportunities.append({
            'type': 'proportion',
            'chart': _CHART_TYPES['proportion'],
            'reason': f'비율 데이터 {pct_count}개 감지',
        })

    # 순위 → 수평 막대
    if has_ranking:
        opportunities.append({
            'type': 'ranking',
            'chart': _CHART_TYPES['ranking'],
            'reason': '순위/랭킹 표현 감지',
        })

    return opportunities


_EMPTY_RESULT = {
    'opportunities': [],
    'summary': {
        'total_opportunities': 0,
        'chart_types': {},
        'number_density': 0.0,
        'level': 'none',
    },
    'score': 50.0,
    'suggestions': [],
}


def _collect_opportunities(sentences: List[str], cleaned: str) -> tuple:
    """문장별 시각화 기회와 목록 데이터를 수집합니다.

    Returns:
        (all_opportunities, chart_type_counter)
    """
    all_opportunities = []
    chart_type_counter = {}

    for sent in sentences:
        opps = _analyze_sentence(sent)
        for opp in opps:
            opp['text'] = sent if len(sent) <= 60 else sent[:57] + '...'
            all_opportunities.append(opp)
            ct = opp['type']
            chart_type_counter[ct] = chart_type_counter.get(ct, 0) + 1

    list_matches = _LIST_PATTERN.findall(cleaned)
    if list_matches:
        chart_type_counter['list_data'] = len(list_matches)
        for match in list_matches[:3]:
            all_opportunities.append({
                'type': 'list_data',
                'chart': _CHART_TYPES['list_data'],
                'reason': '나열 데이터 감지',
                'text': match[:60] if len(match) <= 60 else match[:57] + '...',
            })

    return all_opportunities, chart_type_counter


def _compute_viz_score(total: int) -> tuple:
    """시각화 기회 수로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if total >= 5:
        level = 'rich'
    elif total >= 3:
        level = 'moderate'
    elif total >= 1:
        level = 'minimal'
    else:
        level = 'none'

    if total == 0:
        score = 50.0
    else:
        score = min(100.0, 50.0 + total * 10.0)

    return round(max(0.0, min(100.0, score)), 1), level


def find_visualization_opportunities(content: str) -> dict:
    """데이터 시각화 기회를 찾습니다.

    Returns:
        opportunities, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    cleaned = _HEADING_RE.sub('', content)
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(cleaned)
                 if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        return dict(_EMPTY_RESULT)

    all_numbers = _NUMBER_RE.findall(cleaned)
    word_count = len(cleaned.split())
    number_density = round(len(all_numbers) / max(word_count, 1) * 100, 1)

    all_opportunities, chart_type_counter = _collect_opportunities(sentences, cleaned)
    score, level = _compute_viz_score(len(all_opportunities))

    suggestions = _generate_suggestions(
        all_opportunities, chart_type_counter, number_density, level
    )

    return {
        'opportunities': all_opportunities[:20],
        'summary': {
            'total_opportunities': len(all_opportunities),
            'chart_types': chart_type_counter,
            'number_density': number_density,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(opportunities: List[Dict],
                           chart_types: Dict, density: float,
                           level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'rich': '풍부', 'moderate': '보통',
        'minimal': '최소', 'none': '없음',
    }

    suggestions.append(
        f'시각화 기회 {len(opportunities)}건 ({level_labels.get(level, level)}). '
        f'숫자 밀도 {density}%.'
    )

    if chart_types:
        for ct, count in list(chart_types.items())[:3]:
            suggestions.append(
                f'{_CHART_TYPES.get(ct, ct)} 추천 ({count}건).'
            )

    if level == 'none' and density > 0:
        suggestions.append(
            '숫자 데이터가 있지만 시각화 기회가 적습니다. '
            '비교/추세 맥락을 추가하면 차트로 표현할 수 있습니다.'
        )

    return suggestions
