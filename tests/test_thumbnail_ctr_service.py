"""thumbnail_ctr_service 단위 테스트"""
import pytest
from services.thumbnail_ctr_service import (
    generate_thumbnail_variants,
    ThumbnailVariant,
    _calculate_title_boost,
    _extract_title_keywords,
    _generate_variant_id,
)


class TestGenerateThumbnailVariants:
    """generate_thumbnail_variants 함수 테스트"""

    def test_basic_generation(self):
        """기본 4개 변형 생성"""
        result = generate_thumbnail_variants("vid1")
        assert len(result) == 4
        for v in result:
            assert isinstance(v, ThumbnailVariant)
            assert v.variant_id
            assert v.layout in ("face_focus", "text_overlay", "split", "minimal")
            assert 0.0 < v.predicted_ctr < 1.0

    def test_sorted_by_ctr_descending(self):
        """CTR 내림차순 정렬"""
        result = generate_thumbnail_variants("vid2")
        ctrs = [v.predicted_ctr for v in result]
        assert ctrs == sorted(ctrs, reverse=True)

    def test_custom_n(self):
        """변형 수 지정"""
        result = generate_thumbnail_variants("vid3", n=2)
        assert len(result) == 2

    def test_n_clamped_to_max(self):
        """n=20 → 최대 8로 클램프"""
        result = generate_thumbnail_variants("vid4", n=20)
        assert len(result) == 8

    def test_n_clamped_to_min(self):
        """n=0 → 최소 1로 클램프"""
        result = generate_thumbnail_variants("vid5", n=0)
        assert len(result) == 1

    def test_empty_video_id_raises(self):
        """빈 video_id → ValueError"""
        with pytest.raises(ValueError, match="video_id"):
            generate_thumbnail_variants("")

    def test_title_affects_ctr(self):
        """제목이 CTR에 영향을 미치는지"""
        result_no_title = generate_thumbnail_variants("vid6", title="")
        result_with_title = generate_thumbnail_variants("vid6", title="충격적인 비밀 5가지 꿀팁")
        # 동일 레이아웃 비교 (face_focus)
        no_title_face = [v for v in result_no_title if v.layout == "face_focus"]
        with_title_face = [v for v in result_with_title if v.layout == "face_focus"]
        if no_title_face and with_title_face:
            assert with_title_face[0].predicted_ctr > no_title_face[0].predicted_ctr

    def test_elements_include_keywords_from_title(self):
        """제목 키워드가 요소에 포함되는지"""
        result = generate_thumbnail_variants("vid7", title="파이썬 프로그래밍 입문")
        has_keyword_element = any(
            any("키워드:" in e for e in v.elements)
            for v in result
        )
        assert has_keyword_element

    def test_variant_ids_unique(self):
        """변형 ID가 고유한지"""
        result = generate_thumbnail_variants("vid8", n=8)
        ids = [v.variant_id for v in result]
        assert len(set(ids)) == len(ids)

    def test_deterministic_ids(self):
        """같은 입력이면 같은 ID 생성"""
        r1 = generate_thumbnail_variants("vid9", title="테스트", n=4)
        r2 = generate_thumbnail_variants("vid9", title="테스트", n=4)
        ids1 = sorted(v.variant_id for v in r1)
        ids2 = sorted(v.variant_id for v in r2)
        assert ids1 == ids2

    def test_color_scheme_present(self):
        """색상 구성표가 비어있지 않은지"""
        result = generate_thumbnail_variants("vid10")
        for v in result:
            assert v.color_scheme
            assert isinstance(v.color_scheme, str)


class TestCalculateTitleBoost:
    """_calculate_title_boost 함수 테스트"""

    def test_empty_title(self):
        assert _calculate_title_boost("") == 0.0

    def test_keyword_boost(self):
        """호기심 유발 키워드 → 양수 보정"""
        boost = _calculate_title_boost("충격적인 비밀")
        assert boost > 0

    def test_number_boost(self):
        """숫자 포함 → 보정 추가"""
        boost_no_num = _calculate_title_boost("프로그래밍 팁")
        boost_with_num = _calculate_title_boost("프로그래밍 팁 10가지")
        assert boost_with_num > boost_no_num

    def test_question_mark_boost(self):
        """물음표 포함 → 보정 추가"""
        boost = _calculate_title_boost("왜 이렇게 될까?")
        assert boost > 0


class TestExtractTitleKeywords:
    """_extract_title_keywords 함수 테스트"""

    def test_basic(self):
        result = _extract_title_keywords("파이썬 프로그래밍 입문 강좌")
        assert "파이썬" in result
        assert "프로그래밍" in result

    def test_max_5(self):
        result = _extract_title_keywords("가나다 라마바 사아자 차카타 파하가 나다라 마바사")
        assert len(result) <= 5

    def test_empty_title(self):
        assert _extract_title_keywords("") == []


class TestGenerateVariantId:
    """_generate_variant_id 함수 테스트"""

    def test_deterministic(self):
        id1 = _generate_variant_id("v1", "face_focus", 0)
        id2 = _generate_variant_id("v1", "face_focus", 0)
        assert id1 == id2

    def test_different_inputs(self):
        id1 = _generate_variant_id("v1", "face_focus", 0)
        id2 = _generate_variant_id("v1", "face_focus", 1)
        assert id1 != id2
