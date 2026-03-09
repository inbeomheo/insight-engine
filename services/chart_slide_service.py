"""
차트 슬라이드 서비스

자막 텍스트에서 수치 데이터를 추출하여 차트 데이터로 변환합니다.
숫자/퍼센트 패턴을 탐지하고 자동으로 적절한 차트 유형을 결정합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 숫자 패턴: 정수, 소수, 퍼센트, 통화(원/달러)
_NUMBER_PATTERN = re.compile(
    r'(?P<label>[가-힣A-Za-z\s]+?)\s*'
    r'(?:는|은|이|가|에서|으로|:)?\s*'
    r'(?P<value>[\d,]+(?:\.\d+)?)\s*'
    r'(?P<unit>%|퍼센트|원|달러|만|억|배|개|명|건|회|위)?',
)

# 비교 패턴: "A vs B", "A 대비 B"
_COMPARISON_PATTERN = re.compile(
    r'(?P<a>[가-힣A-Za-z\s]+?)\s*'
    r'(?:vs\.?|대비|보다|와|과|에서)\s*'
    r'(?P<b>[가-힣A-Za-z\s]+)',
    re.IGNORECASE,
)

# 퍼센트 패턴
_PERCENT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(%|퍼센트)')

# 시계열 패턴: 연도/분기/월
_TIME_PATTERN = re.compile(
    r'(?P<time>\d{4}년|\d{1,2}월|\d분기|Q[1-4]|1H|2H|상반기|하반기)'
)


@dataclass
class ChartData:
    """차트 데이터를 나타내는 데이터 클래스"""
    title: str
    chart_type: str  # "bar", "line", "pie", "comparison"
    data_points: list  # list[dict] — 각 항목: {label, value, unit?}
    source_text: str  # 원본 자막 문장
    slide_index: int  # 슬라이드 순서


def _parse_number(raw: str) -> float:
    """쉼표 제거 후 숫자 파싱"""
    cleaned = raw.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_data_from_sentence(sentence: str) -> List[dict]:
    """단일 문장에서 데이터 포인트 추출"""
    points = []
    seen_labels = set()

    for match in _NUMBER_PATTERN.finditer(sentence):
        label = match.group('label').strip()
        value_str = match.group('value')
        unit = match.group('unit') or ''

        # 빈 라벨이나 너무 짧은 라벨 제외
        if len(label) < 1:
            continue

        # 중복 라벨 방지
        if label in seen_labels:
            continue
        seen_labels.add(label)

        value = _parse_number(value_str)
        point = {'label': label, 'value': value}
        if unit:
            point['unit'] = unit

        points.append(point)

    return points


def _determine_chart_type(sentence: str, data_points: List[dict]) -> str:
    """문맥에 따라 적절한 차트 유형 결정

    규칙:
    - 퍼센트 데이터가 다수 → pie
    - 시계열 키워드 존재 → line
    - 비교 키워드 존재 → comparison
    - 기본 → bar
    """
    # 퍼센트가 과반수이면 pie
    percent_count = sum(
        1 for p in data_points
        if p.get('unit') in ('%', '퍼센트')
    )
    if percent_count > 0 and percent_count >= len(data_points) / 2:
        return 'pie'

    # 시계열 패턴이 있으면 line
    if _TIME_PATTERN.search(sentence):
        return 'line'

    # 비교 패턴이 있으면 comparison
    if _COMPARISON_PATTERN.search(sentence):
        return 'comparison'

    return 'bar'


def _split_sentences(transcript: str) -> List[str]:
    """자막을 문장 단위로 분리"""
    # 마침표, 느낌표, 물음표, 줄바꿈 기준 분리
    sentences = re.split(r'[.!?\n]+', transcript)
    return [s.strip() for s in sentences if s.strip()]


def _generate_chart_title(sentence: str, chart_type: str) -> str:
    """문장에서 차트 제목 생성"""
    # 문장이 너무 길면 앞부분만 사용
    title = sentence[:50].strip()
    if len(sentence) > 50:
        title += '...'

    type_labels = {
        'bar': '수치 비교',
        'line': '추이',
        'pie': '비율 분포',
        'comparison': '비교 분석',
    }
    suffix = type_labels.get(chart_type, '데이터')
    return f"{title} — {suffix}"


def extract_charts(transcript: str) -> List[ChartData]:
    """자막에서 수치 데이터를 추출하여 차트 데이터 리스트로 변환합니다.

    Args:
        transcript: 자막 텍스트 전체

    Returns:
        ChartData 리스트 (데이터 포인트가 2개 이상인 문장만 포함)
    """
    if not transcript or not transcript.strip():
        return []

    sentences = _split_sentences(transcript)
    charts: List[ChartData] = []
    slide_index = 0

    for sentence in sentences:
        data_points = _extract_data_from_sentence(sentence)

        # 데이터 포인트가 2개 이상이어야 차트로 의미 있음
        if len(data_points) < 2:
            continue

        chart_type = _determine_chart_type(sentence, data_points)
        title = _generate_chart_title(sentence, chart_type)

        chart = ChartData(
            title=title,
            chart_type=chart_type,
            data_points=data_points,
            source_text=sentence,
            slide_index=slide_index,
        )
        charts.append(chart)
        slide_index += 1

    logger.info(f"자막에서 {len(charts)}개 차트 데이터 추출 완료")
    return charts
