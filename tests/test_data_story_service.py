"""
data_story_service 단위 테스트

데이터 포인트 → 스크롤 데이터 스토리 변환 로직을 검증합니다.
"""
import pytest

from services.data_story_service import (
    ScrollStory,
    StorySection,
    build_scroll_story,
    _detect_flow,
    _sort_data_points,
    _determine_visual_type,
    _build_narrative,
    _generate_heading,
    _generate_story_title,
    FLOW_ASCENDING,
    FLOW_DESCENDING,
    FLOW_CHRONOLOGICAL,
)


class TestDetectFlow:
    """내러티브 흐름 결정 로직 테스트"""

    def test_시간_키_있으면_chronological(self):
        data = [
            {'label': 'Q1', 'value': 100, 'year': 2024},
            {'label': 'Q2', 'value': 150, 'year': 2025},
        ]
        assert _detect_flow(data) == FLOW_CHRONOLOGICAL

    def test_date_키도_chronological(self):
        data = [
            {'label': 'A', 'value': 10, 'date': '2024-01'},
            {'label': 'B', 'value': 20, 'date': '2024-06'},
        ]
        assert _detect_flow(data) == FLOW_CHRONOLOGICAL

    def test_증가_추세면_ascending(self):
        data = [
            {'label': 'A', 'value': 10},
            {'label': 'B', 'value': 30},
            {'label': 'C', 'value': 50},
        ]
        assert _detect_flow(data) == FLOW_ASCENDING

    def test_감소_추세면_descending(self):
        data = [
            {'label': 'A', 'value': 100},
            {'label': 'B', 'value': 60},
            {'label': 'C', 'value': 20},
        ]
        assert _detect_flow(data) == FLOW_DESCENDING

    def test_빈_리스트_기본값_ascending(self):
        assert _detect_flow([]) == FLOW_ASCENDING

    def test_dict_아닌_항목_무시(self):
        data = ['not_a_dict', 42]
        assert _detect_flow(data) == FLOW_ASCENDING


class TestSortDataPoints:
    """데이터 정렬 테스트"""

    def test_ascending_값_오름차순(self):
        data = [
            {'label': 'C', 'value': 30},
            {'label': 'A', 'value': 10},
            {'label': 'B', 'value': 20},
        ]
        sorted_data = _sort_data_points(data, FLOW_ASCENDING)
        values = [d['value'] for d in sorted_data]
        assert values == [10, 20, 30]

    def test_descending_값_내림차순(self):
        data = [
            {'label': 'A', 'value': 10},
            {'label': 'C', 'value': 30},
            {'label': 'B', 'value': 20},
        ]
        sorted_data = _sort_data_points(data, FLOW_DESCENDING)
        values = [d['value'] for d in sorted_data]
        assert values == [30, 20, 10]

    def test_chronological_year_키_정렬(self):
        data = [
            {'label': 'B', 'value': 200, 'year': 2025},
            {'label': 'A', 'value': 100, 'year': 2024},
        ]
        sorted_data = _sort_data_points(data, FLOW_CHRONOLOGICAL)
        assert sorted_data[0]['year'] == 2024
        assert sorted_data[1]['year'] == 2025


class TestDetermineVisualType:
    """시각화 유형 결정 테스트"""

    def test_퍼센트_데이터_progress(self):
        assert _determine_visual_type({'value': 75, 'unit': '%'}) == 'progress'
        assert _determine_visual_type({'value': 50, 'unit': '퍼센트'}) == 'progress'

    def test_큰_숫자_counter(self):
        assert _determine_visual_type({'value': 5_000_000}) == 'counter'

    def test_비교_키_comparison(self):
        assert _determine_visual_type({'value': 100, 'compare': 'B'}) == 'comparison'

    def test_아이템_리스트_icon_grid(self):
        dp = {'value': 5, 'items': ['a', 'b', 'c']}
        assert _determine_visual_type(dp) == 'icon_grid'

    def test_일반_숫자_chart(self):
        assert _determine_visual_type({'value': 500}) == 'chart'

    def test_dict_아닌_입력_chart(self):
        assert _determine_visual_type('not_dict') == 'chart'

    def test_value_없는_dict_chart(self):
        assert _determine_visual_type({'label': 'test'}) == 'chart'


class TestBuildNarrative:
    """내러티브 텍스트 생성 테스트"""

    def test_첫_항목_도입부(self):
        dp = {'label': '매출', 'value': '100', 'unit': '억'}
        narrative = _build_narrative(dp, 0, 3, FLOW_ASCENDING)
        assert '먼저 주목할 점' in narrative

    def test_마지막_항목(self):
        dp = {'label': '이익', 'value': '50', 'unit': '억'}
        narrative = _build_narrative(dp, 2, 3, FLOW_ASCENDING)
        assert '마지막으로' in narrative

    def test_ascending_흐름_상승세_언급(self):
        dp = {'label': '성장률', 'value': '25', 'unit': '%'}
        narrative = _build_narrative(dp, 1, 3, FLOW_ASCENDING)
        assert '상승세' in narrative

    def test_descending_흐름_하락_언급(self):
        dp = {'label': '감소율', 'value': '10', 'unit': '%'}
        narrative = _build_narrative(dp, 1, 3, FLOW_DESCENDING)
        assert '하락' in narrative

    def test_context_포함(self):
        dp = {'label': '매출', 'value': '100', 'context': '전년 대비 2배 성장'}
        narrative = _build_narrative(dp, 0, 1, FLOW_ASCENDING)
        assert '전년 대비 2배 성장' in narrative


class TestGenerateHeading:
    """섹션 제목 생성 테스트"""

    def test_라벨과_값_포함(self):
        heading = _generate_heading({'label': '매출', 'value': '500', 'unit': '억'}, 0)
        assert '매출' in heading
        assert '500' in heading

    def test_값_없으면_라벨만(self):
        heading = _generate_heading({'label': '개요'}, 0)
        assert '개요' in heading


class TestGenerateStoryTitle:
    """스토리 제목 생성 테스트"""

    def test_빈_데이터_기본_제목(self):
        assert _generate_story_title([], FLOW_ASCENDING) == "데이터 스토리"

    def test_ascending_성장_스토리(self):
        data = [{'label': '매출'}]
        title = _generate_story_title(data, FLOW_ASCENDING)
        assert '매출' in title
        assert '성장 스토리' in title

    def test_chronological_타임라인(self):
        data = [{'label': '분기'}]
        title = _generate_story_title(data, FLOW_CHRONOLOGICAL)
        assert '타임라인' in title


class TestBuildScrollStory:
    """build_scroll_story 통합 테스트"""

    def test_빈_데이터_빈_스토리(self):
        story = build_scroll_story([])
        assert isinstance(story, ScrollStory)
        assert story.sections == []
        assert story.total_data_points == 0

    def test_dict_아닌_항목_필터링(self):
        story = build_scroll_story(['not_dict', 42, None])
        assert story.total_data_points == 0
        assert story.sections == []

    def test_정상_데이터_스토리_생성(self):
        data = [
            {'label': '1분기', 'value': 100, 'unit': '억', 'year': 2024},
            {'label': '2분기', 'value': 150, 'unit': '억', 'year': 2024},
            {'label': '3분기', 'value': 200, 'unit': '억', 'year': 2024},
        ]
        story = build_scroll_story(data)
        assert isinstance(story, ScrollStory)
        assert len(story.sections) == 3
        assert story.total_data_points == 3
        assert story.narrative_flow == FLOW_CHRONOLOGICAL

    def test_섹션_position_순차_증가(self):
        data = [
            {'label': 'A', 'value': 10},
            {'label': 'B', 'value': 20},
            {'label': 'C', 'value': 30},
        ]
        story = build_scroll_story(data)
        for i, section in enumerate(story.sections):
            assert section.position == i

    def test_StorySection_필드_검증(self):
        data = [
            {'label': '매출', 'value': 500, 'unit': '억'},
            {'label': '비용', 'value': 200, 'unit': '억'},
        ]
        story = build_scroll_story(data)
        for section in story.sections:
            assert isinstance(section, StorySection)
            assert isinstance(section.heading, str)
            assert isinstance(section.narrative, str)
            assert isinstance(section.data_highlight, dict)
            assert isinstance(section.visual_type, str)
            assert isinstance(section.position, int)

    def test_data_highlight에_position_ratio_포함(self):
        data = [
            {'label': 'A', 'value': 10},
            {'label': 'B', 'value': 20},
        ]
        story = build_scroll_story(data)
        for section in story.sections:
            assert 'position_ratio' in section.data_highlight

    def test_narrative_flow_ascending_정렬(self):
        """ascending 흐름에서 값이 오름차순 정렬되는지 확인"""
        data = [
            {'label': 'C', 'value': 300},
            {'label': 'A', 'value': 100},
            {'label': 'B', 'value': 200},
        ]
        story = build_scroll_story(data)
        assert story.narrative_flow == FLOW_ASCENDING
        values = [s.data_highlight['value'] for s in story.sections]
        assert values == [100, 200, 300]
