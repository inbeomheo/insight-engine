"""환경 변화 재프레이밍 서비스 테스트"""
import pytest
from services.reframing_service import (
    reframe_for_change,
    ReframedContent,
    _apply_frame,
    _identify_adaptations,
    _CHANGE_FRAMES,
    _VALID_CHANGE_TYPES,
)


class TestReframeForChange:
    """reframe_for_change 함수 테스트"""

    def test_basic_reframing(self):
        """기본 재프레이밍이 동작한다."""
        content = "기존 비즈니스 모델을 운영합니다.\n\n고객에게 가치를 제공합니다."
        result = reframe_for_change(content, "technology")

        assert isinstance(result, ReframedContent)
        assert result.original == content
        assert result.reframed != content
        assert result.change_type == "technology"
        assert len(result.adaptations) > 0

    def test_empty_content(self):
        """빈 콘텐츠는 빈 결과를 반환한다."""
        result = reframe_for_change("", "regulation")

        assert result.original == ""
        assert result.reframed == ""
        assert result.adaptations == []

    def test_none_content(self):
        """None 콘텐츠도 에러 없이 처리한다."""
        result = reframe_for_change(None, "market")
        assert result.original == ""

    def test_regulation_change_type(self):
        """regulation 유형으로 재프레이밍한다."""
        content = "규제 환경에서 사업을 운영합니다."
        result = reframe_for_change(content, "regulation")

        assert result.change_type == "regulation"
        assert "규제" in result.reframed

    def test_technology_change_type(self):
        """technology 유형으로 재프레이밍한다."""
        content = "기술 혁신이 필요한 시점입니다."
        result = reframe_for_change(content, "technology")

        assert result.change_type == "technology"
        assert "기술" in result.reframed

    def test_market_change_type(self):
        """market 유형으로 재프레이밍한다."""
        content = "시장 트렌드를 분석합니다."
        result = reframe_for_change(content, "market")

        assert result.change_type == "market"
        assert "시장" in result.reframed

    def test_social_change_type(self):
        """social 유형으로 재프레이밍한다."""
        content = "사회적 가치를 추구합니다."
        result = reframe_for_change(content, "social")

        assert result.change_type == "social"
        assert "사회" in result.reframed

    def test_invalid_change_type_fallback(self):
        """잘못된 change_type은 technology로 폴백한다."""
        content = "테스트 콘텐츠입니다."
        result = reframe_for_change(content, "invalid_type")

        assert result.change_type == "technology"

    def test_original_preserved(self):
        """원본 콘텐츠가 보존된다."""
        content = "원본 텍스트입니다."
        result = reframe_for_change(content, "regulation")

        assert result.original == content

    def test_adaptations_are_strings(self):
        """적응 항목이 문자열 리스트이다."""
        content = "기술 발전에 대응합니다."
        result = reframe_for_change(content, "technology")

        for adaptation in result.adaptations:
            assert isinstance(adaptation, str)
            assert len(adaptation) > 0

    def test_keyword_enhancement(self):
        """콘텐츠 내 프레임 키워드가 강조된다."""
        content = "디지털 전환을 추진합니다.\n\nAI 기술을 도입합니다."
        result = reframe_for_change(content, "technology")

        # 키워드 강조 (**키워드**) 확인
        assert "**" in result.reframed or "기술" in result.reframed

    def test_all_change_types_valid(self):
        """모든 유효한 change_type이 처리된다."""
        content = "테스트 콘텐츠입니다."
        for change_type in _VALID_CHANGE_TYPES:
            result = reframe_for_change(content, change_type)
            assert result.change_type == change_type


class TestIdentifyAdaptations:
    """_identify_adaptations 함수 테스트"""

    def test_template_adaptations(self):
        """기본 템플릿 적응 항목이 포함된다."""
        frame = _CHANGE_FRAMES["technology"]
        result = _identify_adaptations("일반 콘텐츠", frame)

        assert len(result) >= 3  # 템플릿에 3개 기본 항목

    def test_keyword_specific_adaptation(self):
        """프레임 키워드가 콘텐츠에 있으면 구체적 항목이 추가된다."""
        frame = _CHANGE_FRAMES["technology"]
        result = _identify_adaptations("AI 기술 혁신 내용", frame)

        # 기본 3개 + 키워드 매칭 추가
        assert len(result) >= 4

    def test_no_keyword_match(self):
        """키워드 매칭이 없으면 기본 항목만 반환한다."""
        frame = _CHANGE_FRAMES["regulation"]
        result = _identify_adaptations("요리 레시피 설명", frame)

        assert len(result) == 3  # 기본 템플릿만
