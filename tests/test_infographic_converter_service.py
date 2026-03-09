"""
infographic_converter_service 단위 테스트

텍스트 콘텐츠 → 인포그래픽 스펙 변환 로직을 검증합니다.
"""
import pytest

from services.infographic_converter_service import (
    InfographicSpec,
    InfoBlock,
    convert_to_infographic,
    _extract_title,
    _detect_stats,
    _detect_lists,
    _detect_timeline_items,
    _detect_comparisons,
    _determine_layout,
    _determine_color_scheme,
    _calculate_height,
    COLOR_SCHEMES,
)


class TestExtractTitle:
    """제목 추출 테스트"""

    def test_마크다운_헤딩_추출(self):
        content = "# 메인 제목\n본문 텍스트입니다."
        assert _extract_title(content) == "메인 제목"

    def test_h2_헤딩_추출(self):
        content = "## 서브 제목\n본문"
        assert _extract_title(content) == "서브 제목"

    def test_헤딩_없으면_첫줄_사용(self):
        content = "짧은 첫 줄\n본문입니다."
        assert _extract_title(content) == "짧은 첫 줄"

    def test_긴_첫줄_잘라내기(self):
        long_line = "가" * 100 + "\n본문"
        title = _extract_title(long_line)
        assert title.endswith('...')
        assert len(title) <= 63  # 57 + '...'


class TestDetectStats:
    """통계 수치 추출 테스트"""

    def test_퍼센트_추출(self):
        stats = _detect_stats("성장률은 25%를 기록했습니다")
        assert len(stats) >= 1
        assert any(s['unit'] == '%' for s in stats)

    def test_원화_추출(self):
        stats = _detect_stats("매출은 500억원입니다")
        assert len(stats) >= 1

    def test_명_단위_추출(self):
        stats = _detect_stats("직원은 1,200명입니다")
        assert len(stats) >= 1
        values = [s['value'] for s in stats]
        assert '1200' in values

    def test_숫자_없으면_빈_리스트(self):
        stats = _detect_stats("오늘 날씨가 좋습니다")
        assert stats == []

    def test_아이콘_매핑(self):
        stats = _detect_stats("사용자 500명입니다")
        if stats:
            assert stats[0]['icon'] == 'people'


class TestDetectLists:
    """리스트 항목 추출 테스트"""

    def test_번호_리스트_추출(self):
        content = "1. 첫 번째 항목\n2. 두 번째 항목\n3. 세 번째 항목"
        items = _detect_lists(content)
        assert len(items) == 3
        assert items[0] == '첫 번째 항목'

    def test_불릿_리스트_추출(self):
        content = "- 항목 A\n- 항목 B\n- 항목 C"
        items = _detect_lists(content)
        assert len(items) == 3

    def test_리스트_없으면_빈_리스트(self):
        content = "일반 텍스트 문단입니다."
        items = _detect_lists(content)
        assert items == []


class TestDetectTimelineItems:
    """타임라인 항목 추출 테스트"""

    def test_연도_패턴_추출(self):
        content = "2023년 서비스 출시\n2024년 100만 사용자 달성"
        items = _detect_timeline_items(content)
        assert len(items) == 2

    def test_분기_패턴_추출(self):
        content = "Q1 기획 완료\nQ2 개발 시작"
        items = _detect_timeline_items(content)
        assert len(items) == 2

    def test_단계_패턴_추출(self):
        content = "1단계 분석\n2단계 설계\n3단계 구현"
        items = _detect_timeline_items(content)
        assert len(items) == 3

    def test_타임라인_없으면_빈_리스트(self):
        content = "일반 텍스트입니다."
        items = _detect_timeline_items(content)
        assert items == []


class TestDetectComparisons:
    """비교 구문 추출 테스트"""

    def test_vs_패턴(self):
        content = "A사 vs B사 매출 차이가 큽니다."
        comparisons = _detect_comparisons(content)
        assert len(comparisons) >= 1

    def test_대비_패턴(self):
        content = "전년 대비 50% 성장했습니다."
        comparisons = _detect_comparisons(content)
        assert len(comparisons) >= 1

    def test_비교_없으면_빈_리스트(self):
        content = "오늘 날씨가 좋습니다"
        comparisons = _detect_comparisons(content)
        assert comparisons == []


class TestDetermineLayout:
    """레이아웃 결정 테스트"""

    def test_stat_3개_이상_two_column(self):
        blocks = [
            InfoBlock('stat', '10%', 'percent', 0),
            InfoBlock('stat', '20%', 'percent', 1),
            InfoBlock('stat', '30%', 'percent', 2),
        ]
        assert _determine_layout(blocks) == 'two_column'

    def test_timeline_있으면_vertical(self):
        blocks = [
            InfoBlock('timeline', '2023→2024', 'schedule', 0),
            InfoBlock('stat', '100', 'bar_chart', 1),
        ]
        assert _determine_layout(blocks) == 'vertical'

    def test_블록_5개_이상_zigzag(self):
        blocks = [InfoBlock('text', f'블록{i}', 'article', i) for i in range(5)]
        assert _determine_layout(blocks) == 'zigzag'

    def test_기본_vertical(self):
        blocks = [
            InfoBlock('header', '제목', 'title', 0),
            InfoBlock('text', '본문', 'article', 1),
        ]
        assert _determine_layout(blocks) == 'vertical'


class TestDetermineColorScheme:
    """색상 스킴 결정 테스트"""

    def test_기술_키워드_professional(self):
        assert _determine_color_scheme("API 개발 가이드") == 'professional'

    def test_마케팅_키워드_vibrant(self):
        assert _determine_color_scheme("마케팅 캠페인 전략") == 'vibrant'

    def test_환경_키워드_nature(self):
        assert _determine_color_scheme("친환경 지속가능 에너지") == 'nature'

    def test_기본_minimal(self):
        assert _determine_color_scheme("일반적인 주제") == 'minimal'


class TestCalculateHeight:
    """높이 계산 테스트"""

    def test_빈_블록_여백만(self):
        assert _calculate_height([]) == 80  # 상하 여백만

    def test_단일_블록(self):
        blocks = [InfoBlock('header', '제목', 'title', 0)]
        height = _calculate_height(blocks)
        assert height == 120 + 80  # header(120) + 여백(80)

    def test_여러_블록_간격_포함(self):
        blocks = [
            InfoBlock('header', '제목', 'title', 0),
            InfoBlock('stat', '100', 'bar_chart', 1),
        ]
        height = _calculate_height(blocks)
        # header(120) + stat(100) + 블록간격(20) + 상하여백(80)
        assert height == 120 + 100 + 20 + 80


class TestConvertToInfographic:
    """convert_to_infographic 통합 테스트"""

    def test_빈_콘텐츠_빈_스펙(self):
        spec = convert_to_infographic("")
        assert isinstance(spec, InfographicSpec)
        assert spec.blocks == []
        assert spec.estimated_height == 0

    def test_None_입력_빈_스펙(self):
        spec = convert_to_infographic(None)
        assert spec.blocks == []

    def test_공백만_빈_스펙(self):
        spec = convert_to_infographic("   ")
        assert spec.blocks == []

    def test_기본_콘텐츠_header_블록_생성(self):
        spec = convert_to_infographic("# 제목\n본문 텍스트입니다. 이것은 충분히 긴 본문 텍스트입니다 서른자를 넘어야 합니다.")
        assert len(spec.blocks) >= 1
        assert spec.blocks[0].block_type == 'header'
        assert spec.blocks[0].content == '제목'

    def test_통계_포함_콘텐츠(self):
        content = "# 실적 보고\n매출은 500억원을 달성했습니다. 성장률은 25%입니다."
        spec = convert_to_infographic(content)
        block_types = [b.block_type for b in spec.blocks]
        assert 'stat' in block_types

    def test_리스트_포함_콘텐츠(self):
        content = "# 주요 기능\n- 자동 분석\n- 실시간 모니터링\n- 알림 설정"
        spec = convert_to_infographic(content)
        block_types = [b.block_type for b in spec.blocks]
        assert 'icon_list' in block_types

    def test_타임라인_포함_콘텐츠(self):
        content = "# 로드맵\n2023년 기획\n2024년 개발\n2025년 출시"
        spec = convert_to_infographic(content)
        block_types = [b.block_type for b in spec.blocks]
        assert 'timeline' in block_types

    def test_비교_포함_콘텐츠(self):
        content = "# 분석\nA사 vs B사 실적을 비교합니다."
        spec = convert_to_infographic(content)
        block_types = [b.block_type for b in spec.blocks]
        assert 'comparison' in block_types

    def test_position_순차_증가(self):
        content = ("# 보고서\n매출은 100억원입니다. 비용은 50억원입니다.\n"
                   "- 항목 A\n- 항목 B\n2024년 출시 완료")
        spec = convert_to_infographic(content)
        for i, block in enumerate(spec.blocks):
            assert block.position == i

    def test_InfographicSpec_필드_타입_검증(self):
        content = "# 제목\n매출 500억원 성장률 25%"
        spec = convert_to_infographic(content)
        assert isinstance(spec.title, str)
        assert isinstance(spec.blocks, list)
        assert spec.layout in ('vertical', 'two_column', 'zigzag')
        assert spec.color_scheme in ('professional', 'vibrant', 'minimal', 'nature')
        assert isinstance(spec.estimated_height, int)
        assert spec.estimated_height >= 0

    def test_InfoBlock_필드_타입_검증(self):
        content = "# 테스트\n매출 200억원 이익 50억원"
        spec = convert_to_infographic(content)
        for block in spec.blocks:
            assert isinstance(block, InfoBlock)
            assert block.block_type in ('header', 'stat', 'text', 'icon_list',
                                         'timeline', 'comparison')
            assert isinstance(block.content, str)
            assert isinstance(block.icon, str)
            assert isinstance(block.position, int)

    def test_색상_스킴_자동_결정(self):
        spec = convert_to_infographic("# API 개발 가이드\nREST API 설계 패턴")
        assert spec.color_scheme == 'professional'

    def test_COLOR_SCHEMES_구조(self):
        """색상 스킴 정의에 필수 키가 포함되는지 확인"""
        for name, scheme in COLOR_SCHEMES.items():
            assert 'primary' in scheme
            assert 'secondary' in scheme
            assert 'accent' in scheme
            assert 'background' in scheme
            assert 'text' in scheme
