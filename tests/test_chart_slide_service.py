"""
chart_slide_service 단위 테스트

자막에서 수치 데이터 추출 → 차트 데이터 변환 로직을 검증합니다.
"""
import pytest

from services.chart_slide_service import (
    ChartData,
    extract_charts,
    _parse_number,
    _extract_data_from_sentence,
    _determine_chart_type,
    _split_sentences,
    _generate_chart_title,
)


class TestParseNumber:
    """숫자 파싱 유틸리티 테스트"""

    def test_정수_파싱(self):
        assert _parse_number('1000') == 1000.0

    def test_쉼표_포함_숫자(self):
        assert _parse_number('1,234,567') == 1234567.0

    def test_소수점_파싱(self):
        assert _parse_number('3.14') == 3.14

    def test_잘못된_입력_0_반환(self):
        assert _parse_number('abc') == 0.0


class TestSplitSentences:
    """문장 분리 테스트"""

    def test_마침표_기준_분리(self):
        result = _split_sentences("첫 문장. 두 번째 문장. 세 번째.")
        assert len(result) == 3

    def test_줄바꿈_기준_분리(self):
        result = _split_sentences("첫 줄\n두 번째 줄\n세 번째 줄")
        assert len(result) == 3

    def test_빈_문자열_필터링(self):
        result = _split_sentences("문장.. 빈칸  .")
        # 공백만 있는 항목은 제외
        for s in result:
            assert s.strip() != ''

    def test_빈_입력(self):
        result = _split_sentences("")
        assert result == []


class TestExtractDataFromSentence:
    """문장에서 데이터 포인트 추출 테스트"""

    def test_퍼센트_데이터_추출(self):
        sentence = "모바일은 65% 데스크톱은 35%를 차지합니다"
        points = _extract_data_from_sentence(sentence)
        assert len(points) >= 2
        # 퍼센트 단위 포함 확인
        units = [p.get('unit', '') for p in points]
        assert '%' in units

    def test_원화_데이터_추출(self):
        sentence = "매출은 500만원 비용은 200만원입니다"
        points = _extract_data_from_sentence(sentence)
        # 숫자가 추출되어야 함
        values = [p['value'] for p in points]
        assert any(v > 0 for v in values)

    def test_숫자_없는_문장(self):
        sentence = "오늘 날씨가 좋습니다"
        points = _extract_data_from_sentence(sentence)
        assert len(points) == 0

    def test_중복_라벨_방지(self):
        sentence = "매출은 100억 매출은 200억"
        points = _extract_data_from_sentence(sentence)
        labels = [p['label'] for p in points]
        # 중복 라벨이 없어야 함
        assert len(labels) == len(set(labels))


class TestDetermineChartType:
    """차트 유형 결정 로직 테스트"""

    def test_퍼센트_과반수면_pie(self):
        data_points = [
            {'label': 'A', 'value': 60, 'unit': '%'},
            {'label': 'B', 'value': 40, 'unit': '%'},
        ]
        result = _determine_chart_type("A는 60% B는 40%", data_points)
        assert result == 'pie'

    def test_시계열_키워드면_line(self):
        data_points = [
            {'label': 'Q1', 'value': 100},
            {'label': 'Q2', 'value': 150},
        ]
        result = _determine_chart_type("2024년 매출은 100만 2025년 매출은 150만", data_points)
        assert result == 'line'

    def test_비교_키워드면_comparison(self):
        data_points = [
            {'label': 'A사', 'value': 500},
            {'label': 'B사', 'value': 300},
        ]
        result = _determine_chart_type("A사 대비 B사 매출 차이", data_points)
        assert result == 'comparison'

    def test_기본값은_bar(self):
        data_points = [
            {'label': '항목A', 'value': 10},
            {'label': '항목B', 'value': 20},
        ]
        result = _determine_chart_type("항목A는 10개 항목B는 20개", data_points)
        assert result == 'bar'

    def test_퍼센트_소수면_pie_아님(self):
        """퍼센트가 과반수가 아니면 pie가 아닌 다른 유형"""
        data_points = [
            {'label': 'A', 'value': 60, 'unit': '%'},
            {'label': 'B', 'value': 300},
            {'label': 'C', 'value': 500},
        ]
        result = _determine_chart_type("A는 60% B는 300개 C는 500개", data_points)
        assert result != 'pie'


class TestGenerateChartTitle:
    """차트 제목 생성 테스트"""

    def test_짧은_문장_그대로_사용(self):
        title = _generate_chart_title("매출 비교", "bar")
        assert "매출 비교" in title
        assert "수치 비교" in title

    def test_긴_문장_잘라내기(self):
        long_sentence = "가" * 100
        title = _generate_chart_title(long_sentence, "pie")
        assert "..." in title
        assert "비율 분포" in title

    def test_차트_유형별_라벨(self):
        assert "추이" in _generate_chart_title("매출", "line")
        assert "비교 분석" in _generate_chart_title("매출", "comparison")


class TestExtractCharts:
    """extract_charts 통합 테스트"""

    def test_빈_자막_빈_리스트(self):
        assert extract_charts("") == []
        assert extract_charts("   ") == []
        assert extract_charts(None) == []

    def test_숫자_없는_자막_빈_리스트(self):
        transcript = "오늘 날씨가 좋습니다. 내일도 맑겠습니다."
        assert extract_charts(transcript) == []

    def test_수치_포함_자막_차트_생성(self):
        transcript = (
            "모바일 사용자는 65% 데스크톱 사용자는 35%를 차지합니다. "
            "2024년 매출은 500만원 2025년 매출은 800만원으로 성장했습니다."
        )
        charts = extract_charts(transcript)
        assert len(charts) >= 1
        assert all(isinstance(c, ChartData) for c in charts)

    def test_ChartData_필드_검증(self):
        transcript = "A팀은 85% B팀은 15%를 달성했습니다"
        charts = extract_charts(transcript)
        if charts:
            chart = charts[0]
            assert isinstance(chart.title, str)
            assert chart.chart_type in ('bar', 'line', 'pie', 'comparison')
            assert isinstance(chart.data_points, list)
            assert isinstance(chart.source_text, str)
            assert isinstance(chart.slide_index, int)
            assert chart.slide_index >= 0

    def test_슬라이드_인덱스_순차_증가(self):
        transcript = (
            "A는 50% B는 50% 비율입니다. "
            "X는 100개 Y는 200개 생산했습니다. "
            "P는 30% Q는 70% 점유합니다."
        )
        charts = extract_charts(transcript)
        if len(charts) >= 2:
            for i in range(1, len(charts)):
                assert charts[i].slide_index == charts[i - 1].slide_index + 1

    def test_데이터_포인트_2개_미만_제외(self):
        """데이터 포인트가 1개뿐인 문장은 차트에서 제외"""
        transcript = "매출은 500만원입니다. 오늘 날씨가 좋습니다."
        charts = extract_charts(transcript)
        for chart in charts:
            assert len(chart.data_points) >= 2
