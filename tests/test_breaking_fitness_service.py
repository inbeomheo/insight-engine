"""
Breaking Fitness 서비스 테스트

score_breaking_fitness() 함수의 적합성 평가, 시의성 판별,
관련도 계산, 엣지 케이스를 검증합니다.
"""
import pytest

from services.breaking_fitness_service import (
    FitnessScore,
    score_breaking_fitness,
)


class TestScoreBreakingFitness:
    """score_breaking_fitness 핵심 기능 테스트"""

    def test_empty_content_returns_zero(self):
        """빈 콘텐츠 → 적합성 0점"""
        result = score_breaking_fitness("", "AI 혁명")
        assert isinstance(result, FitnessScore)
        assert result.fitness_score == 0.0
        assert result.urgency == "not_urgent"
        assert result.recommended_action == "입력 데이터 부족"

    def test_empty_topic_returns_zero(self):
        """빈 토픽 → 적합성 0점"""
        result = score_breaking_fitness("콘텐츠 본문입니다", "")
        assert result.fitness_score == 0.0

    def test_whitespace_only_inputs(self):
        """공백만 있는 입력 → 적합성 0점"""
        result = score_breaking_fitness("   ", "  ")
        assert result.fitness_score == 0.0

    def test_none_inputs(self):
        """None 입력 → 적합성 0점"""
        result = score_breaking_fitness(None, None)
        assert result.fitness_score == 0.0

    def test_direct_topic_mention_high_score(self):
        """토픽이 콘텐츠에 직접 언급되면 높은 점수"""
        content = (
            "AI 혁명이 시작되었습니다. AI 혁명은 산업 전반에 영향을 미치고 있으며, "
            "AI 혁명에 대한 전문가 분석을 통해 데이터 기반의 변화를 살펴봅니다."
        )
        result = score_breaking_fitness(content, "AI 혁명")
        assert result.fitness_score > 30
        assert result.topic == "AI 혁명"
        assert any("직접 언급" in f for f in result.relevance_factors)

    def test_keyword_overlap_scoring(self):
        """토픽 키워드가 콘텐츠에 포함되면 점수 반영"""
        content = "인공지능 기술이 빠르게 발전하고 있습니다. 클라우드 서비스도 확장 중입니다."
        result = score_breaking_fitness(content, "인공지능 클라우드")
        assert result.fitness_score > 0
        assert any("키워드" in f for f in result.relevance_factors)

    def test_context_signals_detected(self):
        """컨텍스트 신호(전문가, 데이터 등)가 관련도에 반영"""
        content = "전문가들은 이 변화가 데이터 기반으로 진행되고 있다고 분석합니다."
        result = score_breaking_fitness(content, "기술 변화")
        factor_texts = " ".join(result.relevance_factors)
        assert "전문가" in factor_texts or "데이터" in factor_texts

    def test_urgency_immediate(self):
        """속보 키워드 → immediate 시의성"""
        content = "속보: 새로운 정책이 발표되었습니다. 정책 변화에 대한 분석입니다."
        result = score_breaking_fitness(content, "정책 변화")
        assert result.urgency == "immediate"

    def test_urgency_within_hours(self):
        """오늘/최신 키워드 → within_hours 시의성"""
        content = "오늘 발표된 최신 업데이트에 대해 알아봅니다."
        result = score_breaking_fitness(content, "업데이트")
        assert result.urgency == "within_hours"

    def test_urgency_next_day(self):
        """이번 주/최근 키워드 → next_day 시의성"""
        content = "이번 주 발생한 주요 변경 사항을 정리합니다."
        result = score_breaking_fitness(content, "변경 사항")
        assert result.urgency == "next_day"

    def test_urgency_not_urgent(self):
        """시의성 키워드 없음 → not_urgent"""
        content = "일반적인 기술 설명 글입니다. 기초부터 다뤄봅시다."
        result = score_breaking_fitness(content, "기술 기초")
        assert result.urgency == "not_urgent"

    def test_high_fitness_immediate_action(self):
        """높은 적합성 + immediate → 즉시 발행 권장"""
        content = (
            "속보: AI 혁명이 산업을 뒤흔들고 있습니다. AI 혁명 전문가 분석에 따르면 "
            "AI 혁명의 영향이 데이터로 확인되고 있습니다. AI 혁명의 전망도 주목됩니다."
        )
        result = score_breaking_fitness(content, "AI 혁명")
        assert result.fitness_score >= 50
        assert "즉시 발행" in result.recommended_action or "우선 발행" in result.recommended_action

    def test_low_fitness_action(self):
        """낮은 적합성 → 관련 없음 메시지"""
        content = "오늘의 날씨는 맑고 기온이 높겠습니다."
        result = score_breaking_fitness(content, "블록체인 규제")
        assert result.fitness_score < 30

    def test_score_range_0_to_100(self):
        """점수가 항상 0~100 범위"""
        content = "테스트 " * 500 + "AI " * 100
        result = score_breaking_fitness(content, "AI")
        assert 0 <= result.fitness_score <= 100

    def test_dataclass_fields(self):
        """FitnessScore 필드가 올바른 타입"""
        result = score_breaking_fitness("콘텐츠 테스트", "테스트 토픽")
        assert isinstance(result.topic, str)
        assert isinstance(result.fitness_score, float)
        assert isinstance(result.relevance_factors, list)
        assert isinstance(result.recommended_action, str)
        assert result.urgency in ("immediate", "within_hours", "next_day", "not_urgent")

    def test_english_content_and_topic(self):
        """영어 콘텐츠/토픽도 정상 처리"""
        content = "Breaking: The AI revolution is transforming industries. Expert analysis shows impact."
        result = score_breaking_fitness(content, "AI revolution")
        assert result.fitness_score > 0
        assert result.urgency == "immediate"  # "breaking" 키워드
