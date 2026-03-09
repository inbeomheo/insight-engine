"""
제품 아바타 서비스 테스트
"""
import pytest
from services.product_avatar_service import (
    hold_product,
    ProductDemo,
    _detect_category,
    _extract_features,
)


class TestDetectCategory:
    """카테고리 감지 테스트."""

    def test_tech(self):
        assert _detect_category("스마트워치 전자기기") == "tech"

    def test_beauty(self):
        assert _detect_category("수분 크림 스킨케어 제품") == "beauty"

    def test_food(self):
        assert _detect_category("유기농 식품 간식") == "food"

    def test_fashion(self):
        assert _detect_category("겨울 패션 코트") == "fashion"

    def test_home(self):
        assert _detect_category("인테리어 소품 가구") == "home"

    def test_default(self):
        assert _detect_category("알 수 없는 제품") == "default"


class TestExtractFeatures:
    """특징 추출 테스트."""

    def test_comma_separated(self):
        features = _extract_features("무선 블루투스, 노이즈 캔슬링, 30시간 배터리")
        assert len(features) >= 2

    def test_max_five(self):
        features = _extract_features("a특징, b특징, c특징, d특징, e특징, f특징, g특징, h특징")
        assert len(features) <= 5

    def test_short_parts_filtered(self):
        """4글자 미만 특징은 제외."""
        features = _extract_features("좋은, 이건 좋은 특징입니다")
        # "좋은" (2글자)는 제외, "이건 좋은 특징입니다"는 포함
        assert all(len(f) >= 4 for f in features)


class TestHoldProduct:
    """hold_product 통합 테스트."""

    def test_empty_avatar_raises(self):
        with pytest.raises(ValueError, match="아바타"):
            hold_product("", "제품 설명")

    def test_empty_product_raises(self):
        with pytest.raises(ValueError, match="제품"):
            hold_product("아바타 설명", "")

    def test_basic_demo(self):
        """기본 데모 생성."""
        result = hold_product(
            "친근한 여성 캐릭터",
            "스마트 무선 블루투스 이어폰, 노이즈 캔슬링 기능, 30시간 배터리"
        )

        assert isinstance(result, ProductDemo)
        assert result.demo_id
        assert result.avatar["type"] == "virtual_presenter"
        assert result.product["category"] == "tech"
        assert len(result.demo_scenes) >= 3
        assert result.duration_seconds > 0

    def test_beauty_product_scenes(self):
        """뷰티 제품은 클로즈업, 비교 장면 포함."""
        result = hold_product(
            "뷰티 인플루언서",
            "수분 크림 스킨케어 보습 세럼"
        )

        scene_types = [s["scene_type"] for s in result.demo_scenes]
        assert "close_up" in scene_types

    def test_food_product_scenes(self):
        """음식 제품 장면 구성."""
        result = hold_product(
            "셰프 캐릭터",
            "유기농 식품 건강 간식"
        )

        scene_types = [s["scene_type"] for s in result.demo_scenes]
        assert "intro" in scene_types
        assert "outro" in scene_types

    def test_duration_matches_scenes(self):
        """전체 시간 = 장면 시간 합."""
        result = hold_product(
            "캐릭터",
            "전자 기기 스마트 디바이스"
        )

        total = sum(s["duration_seconds"] for s in result.demo_scenes)
        assert result.duration_seconds == total

    def test_product_features_extracted(self):
        """제품 특징이 추출됨."""
        result = hold_product(
            "아바타",
            "방수 기능, 초경량 소재, 접이식 디자인, 휴대 편리"
        )

        assert result.product["feature_count"] >= 1
        assert len(result.product["features"]) >= 1

    def test_scenes_have_index(self):
        """장면에 순서 인덱스 포함."""
        result = hold_product("아바타", "스마트 기기 제품")

        for i, scene in enumerate(result.demo_scenes):
            assert scene["index"] == i

    def test_whitespace_only_raises(self):
        """공백만 있는 입력은 ValueError."""
        with pytest.raises(ValueError):
            hold_product("   ", "제품")

        with pytest.raises(ValueError):
            hold_product("아바타", "   ")
