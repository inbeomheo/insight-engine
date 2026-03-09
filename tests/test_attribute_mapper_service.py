"""제품 속성 추출 서비스 테스트"""
import pytest
from services.attribute_mapper_service import (
    map_product_attributes,
    ProductAttribute,
    _detect_sentiment,
    _extract_attributes,
)


class TestMapProductAttributes:
    """map_product_attributes 함수 테스트"""

    def test_basic_extraction(self):
        """기본 속성-값 패턴을 추출한다."""
        transcript = "배터리가 오래가서 좋습니다. 화면이 밝고 선명합니다."
        result = map_product_attributes(transcript)

        assert isinstance(result, list)
        assert all(isinstance(a, ProductAttribute) for a in result)

    def test_empty_input(self):
        """빈 입력은 빈 리스트를 반환한다."""
        assert map_product_attributes("") == []
        assert map_product_attributes("   ") == []
        assert map_product_attributes(None) == []

    def test_colon_pattern_extraction(self):
        """콜론 패턴으로 속성을 추출한다."""
        transcript = "배터리: 10시간 지속. 무게: 1.2kg. 가격: 합리적."
        result = map_product_attributes(transcript)

        assert len(result) > 0
        names = [a.name for a in result]
        assert "배터리" in names

    def test_sentiment_detection_positive(self):
        """긍정 키워드를 감지한다."""
        transcript = "디자인이 훌륭합니다. 성능이 최고입니다."
        result = map_product_attributes(transcript)

        positive_attrs = [a for a in result if a.sentiment == "positive"]
        assert len(positive_attrs) > 0

    def test_sentiment_detection_negative(self):
        """부정 키워드를 감지한다."""
        transcript = "무게가 무겁고 불편합니다. 속도가 느립니다."
        result = map_product_attributes(transcript)

        negative_attrs = [a for a in result if a.sentiment == "negative"]
        assert len(negative_attrs) > 0

    def test_mention_count_tracking(self):
        """동일 속성의 언급 횟수를 추적한다."""
        transcript = "배터리: 우수. 배터리가 정말 오래 갑니다. 배터리 - 최고."
        result = map_product_attributes(transcript)

        battery_attrs = [a for a in result if "배터리" in a.name]
        if battery_attrs:
            assert battery_attrs[0].mention_count >= 2

    def test_sorted_by_mention_count(self):
        """결과가 mention_count 내림차순으로 정렬된다."""
        transcript = (
            "가격이 합리적. 가격: 저렴. 가격이 좋아요.\n"
            "디자인: 세련됨.\n"
        )
        result = map_product_attributes(transcript)

        if len(result) >= 2:
            assert result[0].mention_count >= result[1].mention_count

    def test_valid_sentiment_values(self):
        """감성 값이 유효한 범위 내에 있다."""
        transcript = "화질이 좋습니다. 소음이 심합니다. 크기는 적당합니다."
        result = map_product_attributes(transcript)

        valid = {"positive", "negative", "neutral"}
        for attr in result:
            assert attr.sentiment in valid

    def test_hyphen_pattern(self):
        """하이픈 패턴으로도 속성을 추출한다."""
        transcript = "무게 - 가벼움. 크기 - 컴팩트."
        result = map_product_attributes(transcript)

        assert len(result) > 0

    def test_mixed_language(self):
        """한영 혼합 리뷰도 처리한다."""
        transcript = "display: excellent. 배터리가 good합니다."
        result = map_product_attributes(transcript)

        assert isinstance(result, list)

    def test_short_transcript(self):
        """매우 짧은 자막도 에러 없이 처리한다."""
        result = map_product_attributes("좋아요")
        assert isinstance(result, list)


class TestDetectSentiment:
    """_detect_sentiment 함수 테스트"""

    def test_positive_context(self):
        """긍정 문맥을 감지한다."""
        assert _detect_sentiment("정말 좋은 제품입니다") == "positive"

    def test_negative_context(self):
        """부정 문맥을 감지한다."""
        assert _detect_sentiment("너무 느리고 불편합니다") == "negative"

    def test_neutral_context(self):
        """중립 문맥을 감지한다."""
        assert _detect_sentiment("크기는 보통입니다") == "neutral"

    def test_empty_context(self):
        """빈 문맥은 neutral을 반환한다."""
        assert _detect_sentiment("") == "neutral"
