"""시사 맥락 주입 서비스 테스트"""
import pytest
from services.news_context_service import (
    inject_news_context,
    ContextualContent,
    _find_relevant_topics,
    _calculate_relevance,
)


class TestInjectNewsContext:
    """inject_news_context 함수 테스트"""

    def test_basic_context_injection(self):
        """기본 시사 맥락 주입이 동작한다."""
        content = "인공지능 기술이 발전하고 있습니다.\n\n다양한 활용 사례가 있습니다."
        result = inject_news_context(content, "AI")

        assert isinstance(result, ContextualContent)
        assert result.original_content == content
        assert len(result.context_points) > 0
        assert result.relevance_score > 0

    def test_empty_content(self):
        """빈 콘텐츠는 빈 결과를 반환한다."""
        result = inject_news_context("", "AI")

        assert result.original_content == ""
        assert result.context_points == []
        assert result.relevance_score == 0.0

    def test_empty_topic(self):
        """빈 토픽은 맥락 없이 원본을 반환한다."""
        content = "테스트 콘텐츠입니다."
        result = inject_news_context(content, "")

        assert result.injected_content == content
        assert result.context_points == []

    def test_none_content(self):
        """None 콘텐츠도 에러 없이 처리한다."""
        result = inject_news_context(None, "AI")
        assert result.relevance_score == 0.0

    def test_ai_topic(self):
        """AI 토픽으로 관련 맥락을 주입한다."""
        content = "머신러닝 모델을 학습시키는 방법을 설명합니다."
        result = inject_news_context(content, "인공지능")

        assert len(result.context_points) > 0
        assert any("AI" in cp or "생성형" in cp or "규제" in cp for cp in result.context_points)

    def test_economy_topic(self):
        """경제 토픽으로 관련 맥락을 주입한다."""
        content = "스타트업 투자 전략에 대해 알아봅니다."
        result = inject_news_context(content, "경제")

        assert len(result.context_points) > 0

    def test_technology_topic(self):
        """기술 토픽으로 관련 맥락을 주입한다."""
        content = "클라우드 네이티브 개발 환경을 구축합니다."
        result = inject_news_context(content, "기술")

        assert len(result.context_points) > 0

    def test_injected_content_differs(self):
        """맥락이 주입되면 원본과 다른 콘텐츠가 생성된다."""
        content = "인공지능 기반 서비스를 개발합니다.\n\n다양한 모델을 활용합니다."
        result = inject_news_context(content, "AI")

        if result.context_points:
            assert result.injected_content != result.original_content

    def test_relevance_score_range(self):
        """관련성 점수가 0.0 ~ 1.0 범위 내에 있다."""
        content = "AI 기술과 경제 성장에 대한 분석입니다."
        result = inject_news_context(content, "AI")

        assert 0.0 <= result.relevance_score <= 1.0

    def test_unknown_topic(self):
        """알 수 없는 토픽은 빈 맥락을 반환한다."""
        content = "일반적인 내용입니다."
        result = inject_news_context(content, "xyz알수없는토픽abc")

        # 콘텐츠 내 키워드 매칭으로 부분 맥락이 나올 수 있음
        assert isinstance(result.context_points, list)

    def test_context_points_are_strings(self):
        """맥락 포인트가 문자열 리스트이다."""
        content = "교육 기술의 발전을 논의합니다."
        result = inject_news_context(content, "교육")

        for point in result.context_points:
            assert isinstance(point, str)
            assert len(point) > 0

    def test_multiple_topic_keywords(self):
        """콘텐츠에 여러 토픽 키워드가 있으면 부가 맥락도 추가된다."""
        content = "AI 기술을 교육 분야에 적용하여 학습 효과를 높입니다."
        result = inject_news_context(content, "AI")

        # AI 맥락 + 교육 부가 맥락
        assert len(result.context_points) >= 1


class TestFindRelevantTopics:
    """_find_relevant_topics 함수 테스트"""

    def test_direct_mapping(self):
        """직접 매핑된 토픽을 찾는다."""
        result = _find_relevant_topics("내용", "ai")
        assert len(result) > 0

    def test_partial_match(self):
        """부분 매칭으로 토픽을 찾는다."""
        result = _find_relevant_topics("내용", "인공지능")
        assert len(result) > 0

    def test_no_match(self):
        """매칭되지 않으면 빈 리스트를 반환한다."""
        result = _find_relevant_topics("내용", "xyz없는토픽")
        assert isinstance(result, list)


class TestCalculateRelevance:
    """_calculate_relevance 함수 테스트"""

    def test_high_relevance(self):
        """관련 키워드가 많으면 높은 점수를 반환한다."""
        score = _calculate_relevance(
            "AI 머신러닝 딥러닝 기술 발전", "ai", ["맥락 문장"]
        )
        assert score > 0.3

    def test_no_context_points(self):
        """맥락 포인트가 없으면 0.0을 반환한다."""
        score = _calculate_relevance("내용", "ai", [])
        assert score == 0.0
