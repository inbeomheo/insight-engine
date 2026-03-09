"""
데이터 스토리 서비스

데이터 포인트들을 시간순/크기순으로 정렬하여
스크롤 기반 데이터 스토리 내러티브를 구성합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 내러티브 흐름 유형
FLOW_ASCENDING = 'ascending'    # 작은 값 → 큰 값 (성장 스토리)
FLOW_DESCENDING = 'descending'  # 큰 값 → 작은 값 (감소 스토리)
FLOW_CHRONOLOGICAL = 'chronological'  # 시간순

# 비주얼 유형 매핑 기준
_VISUAL_THRESHOLDS = {
    'large_number': 1_000_000,   # 큰 숫자 → 카운터 애니메이션
    'percentage': 100,           # 퍼센트 → 프로그레스 바
    'small_set': 5,              # 소수 항목 → 아이콘 그리드
}


@dataclass
class StorySection:
    """스크롤 스토리의 개별 섹션"""
    heading: str
    narrative: str  # 서술형 설명 텍스트
    data_highlight: dict  # 강조할 데이터 {label, value, unit?, context?}
    visual_type: str  # 시각화 유형: counter, progress, chart, icon_grid, comparison
    position: int  # 섹션 순서 (0-based)


@dataclass
class ScrollStory:
    """스크롤 데이터 스토리 전체 구조"""
    title: str
    sections: List[StorySection]
    total_data_points: int
    narrative_flow: str  # ascending, descending, chronological


def _detect_flow(data_points: List[dict]) -> str:
    """데이터 포인트의 정렬 방향(내러티브 흐름)을 결정합니다.

    - 'year', 'date', 'time', 'order' 키가 있으면 시간순
    - 값이 증가 추세면 ascending, 감소 추세면 descending
    """
    # 시간 관련 키가 있는지 확인
    time_keys = {'year', 'date', 'time', 'month', 'quarter', 'period', 'order'}
    has_time = any(
        any(k in time_keys for k in dp.keys())
        for dp in data_points
        if isinstance(dp, dict)
    )
    if has_time:
        return FLOW_CHRONOLOGICAL

    # 값 추세 분석
    values = []
    for dp in data_points:
        if isinstance(dp, dict) and 'value' in dp:
            try:
                values.append(float(dp['value']))
            except (ValueError, TypeError):
                continue

    if len(values) >= 2:
        increases = sum(1 for i in range(1, len(values)) if values[i] > values[i - 1])
        decreases = sum(1 for i in range(1, len(values)) if values[i] < values[i - 1])
        if increases > decreases:
            return FLOW_ASCENDING
        elif decreases > increases:
            return FLOW_DESCENDING

    return FLOW_ASCENDING


def _sort_data_points(data_points: List[dict], flow: str) -> List[dict]:
    """내러티브 흐름에 따라 데이터 포인트를 정렬합니다."""
    if flow == FLOW_CHRONOLOGICAL:
        # 시간 키로 정렬 시도
        time_keys = ['year', 'date', 'time', 'month', 'quarter', 'period', 'order']
        for key in time_keys:
            if any(key in dp for dp in data_points if isinstance(dp, dict)):
                return sorted(
                    data_points,
                    key=lambda dp: dp.get(key, 0) if isinstance(dp, dict) else 0,
                )
        return data_points

    # 값 기준 정렬
    def get_value(dp):
        if not isinstance(dp, dict):
            return 0
        try:
            return float(dp.get('value', 0))
        except (ValueError, TypeError):
            return 0

    reverse = (flow == FLOW_DESCENDING)
    return sorted(data_points, key=get_value, reverse=reverse)


def _determine_visual_type(data_point: dict) -> str:
    """데이터 포인트의 특성에 따라 시각화 유형을 결정합니다."""
    if not isinstance(data_point, dict):
        return 'chart'

    value = data_point.get('value')
    unit = data_point.get('unit', '')

    # 퍼센트 데이터 → 프로그레스 바
    if unit in ('%', '퍼센트', 'percent'):
        return 'progress'

    # 숫자 값 판별
    try:
        num_value = float(value) if value is not None else 0
    except (ValueError, TypeError):
        return 'chart'

    # 비교 컨텍스트가 있으면 comparison
    if 'compare' in data_point or 'vs' in data_point:
        return 'comparison'

    # 큰 숫자 → 카운터 애니메이션
    if num_value >= _VISUAL_THRESHOLDS['large_number']:
        return 'counter'

    # 아이템 목록이 있으면 아이콘 그리드
    if 'items' in data_point and isinstance(data_point['items'], list):
        return 'icon_grid'

    return 'chart'


def _build_narrative(data_point: dict, position: int, total: int, flow: str) -> str:
    """데이터 포인트에 대한 서술형 텍스트를 생성합니다."""
    label = data_point.get('label', '항목')
    value = data_point.get('value', '')
    unit = data_point.get('unit', '')
    context = data_point.get('context', '')

    value_str = f"{value}{unit}" if unit else str(value)

    # 위치에 따른 도입부
    if position == 0:
        intro = "먼저 주목할 점은"
    elif position == total - 1:
        intro = "마지막으로"
    else:
        ordinals = ["두 번째로", "세 번째로", "네 번째로", "다섯 번째로",
                     "여섯 번째로", "일곱 번째로", "여덟 번째로"]
        idx = min(position - 1, len(ordinals) - 1)
        intro = ordinals[idx]

    narrative = f"{intro}, {label}은(는) {value_str}를 기록했습니다."

    # 흐름에 따른 맥락 추가
    if flow == FLOW_ASCENDING and position > 0:
        narrative += " 이전 데이터 대비 상승세를 보이고 있습니다."
    elif flow == FLOW_DESCENDING and position > 0:
        narrative += " 하락 추세가 이어지고 있습니다."

    if context:
        narrative += f" {context}"

    return narrative


def _generate_heading(data_point: dict, position: int) -> str:
    """섹션 제목 생성"""
    label = data_point.get('label', f'데이터 #{position + 1}')
    value = data_point.get('value', '')
    unit = data_point.get('unit', '')

    if value:
        value_str = f"{value}{unit}" if unit else str(value)
        return f"{label}: {value_str}"
    return str(label)


def _generate_story_title(data_points: List[dict], flow: str) -> str:
    """스토리 전체 제목 생성"""
    if not data_points:
        return "데이터 스토리"

    # 첫 번째 항목의 라벨 기반
    first_label = data_points[0].get('label', '데이터') if isinstance(data_points[0], dict) else '데이터'

    flow_labels = {
        FLOW_ASCENDING: '성장 스토리',
        FLOW_DESCENDING: '변화 추이',
        FLOW_CHRONOLOGICAL: '타임라인',
    }
    suffix = flow_labels.get(flow, '분석')
    return f"{first_label} — {suffix}"


def build_scroll_story(data_points: List[dict]) -> ScrollStory:
    """데이터 포인트 리스트를 스크롤 데이터 스토리로 변환합니다.

    Args:
        data_points: 데이터 포인트 딕셔너리 리스트
            각 항목은 최소 {label, value} 필수, {unit, context, year 등} 선택

    Returns:
        ScrollStory 데이터클래스 인스턴스
    """
    if not data_points:
        return ScrollStory(
            title="데이터 스토리",
            sections=[],
            total_data_points=0,
            narrative_flow=FLOW_ASCENDING,
        )

    # dict가 아닌 항목 필터링
    valid_points = [dp for dp in data_points if isinstance(dp, dict)]
    if not valid_points:
        return ScrollStory(
            title="데이터 스토리",
            sections=[],
            total_data_points=0,
            narrative_flow=FLOW_ASCENDING,
        )

    # 내러티브 흐름 결정
    flow = _detect_flow(valid_points)

    # 데이터 정렬
    sorted_points = _sort_data_points(valid_points, flow)

    # 스토리 제목
    title = _generate_story_title(sorted_points, flow)

    # 섹션 빌드
    total = len(sorted_points)
    sections: List[StorySection] = []

    for idx, dp in enumerate(sorted_points):
        heading = _generate_heading(dp, idx)
        narrative = _build_narrative(dp, idx, total, flow)
        visual_type = _determine_visual_type(dp)

        # data_highlight: 원본 데이터 + 위치 메타
        highlight = dict(dp)
        highlight['position_ratio'] = round(idx / max(total - 1, 1), 2)

        section = StorySection(
            heading=heading,
            narrative=narrative,
            data_highlight=highlight,
            visual_type=visual_type,
            position=idx,
        )
        sections.append(section)

    story = ScrollStory(
        title=title,
        sections=sections,
        total_data_points=len(valid_points),
        narrative_flow=flow,
    )

    logger.info(f"스크롤 스토리 생성: {len(sections)}개 섹션, 흐름={flow}")
    return story
