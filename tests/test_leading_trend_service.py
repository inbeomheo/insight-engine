"""
선행 트렌드 감지 서비스 테스트

detect_leading_trends() 함수의 트렌드 감지, 신호 강도 계산,
카테고리 분류, 성장률 계산, 엣지 케이스를 검증합니다.
"""
import pytest

from services.leading_trend_service import (
    LeadingTrend,
    detect_leading_trends,
)


class TestDetectLeadingTrends:
    """detect_leading_trends 핵심 기능 테스트"""

    def test_empty_signals_returns_empty(self):
        """빈 신호 → 빈 결과"""
        result = detect_leading_trends([])
        assert result == []

    def test_none_signals_returns_empty(self):
        """None 신호 → 빈 결과"""
        result = detect_leading_trends(None)
        assert result == []

    def test_single_signal_basic(self):
        """단일 신호 → 단일 트렌드"""
        signals = [{"name": "AI 에이전트", "signal_strength": 70}]
        result = detect_leading_trends(signals)
        assert len(result) == 1
        assert result[0].trend_name == "AI 에이전트"
        assert result[0].signal_strength == 70

    def test_technology_category(self):
        """기술 키워드 → technology 카테고리"""
        signals = [{"name": "AI 클라우드 서비스", "signal_strength": 50}]
        result = detect_leading_trends(signals)
        assert result[0].category == "technology"

    def test_business_category(self):
        """비즈니스 키워드 → business 카테고리"""
        signals = [{"name": "스타트업 투자 트렌드", "signal_strength": 50}]
        result = detect_leading_trends(signals)
        assert result[0].category == "business"

    def test_explicit_category(self):
        """메타데이터에 명시적 카테고리 → 그대로 사용"""
        signals = [{"name": "커스텀 트렌드", "signal_strength": 50, "category": "custom"}]
        result = detect_leading_trends(signals)
        assert result[0].category == "custom"

    def test_signal_strength_from_components(self):
        """여러 구성 요소에서 신호 강도 계산"""
        signals = [{
            "name": "새 트렌드",
            "search_growth": 30,
            "mentions": 200,
            "engagement": 60,
        }]
        result = detect_leading_trends(signals)
        assert result[0].signal_strength > 0
        assert result[0].signal_strength <= 100

    def test_growth_rate_direct(self):
        """직접 growth_rate 필드 → 그대로 반영"""
        signals = [{"name": "트렌드", "signal_strength": 50, "growth_rate": 35.5}]
        result = detect_leading_trends(signals)
        assert result[0].growth_rate == 35.5

    def test_growth_rate_from_values(self):
        """previous/current 값에서 성장률 계산"""
        signals = [{
            "name": "트렌드",
            "signal_strength": 50,
            "previous_value": 100,
            "current_value": 200,
        }]
        result = detect_leading_trends(signals)
        assert result[0].growth_rate == 100.0  # 100% 성장

    def test_first_detected_field(self):
        """first_detected 날짜 추출"""
        signals = [{"name": "트렌드", "signal_strength": 50, "first_detected": "2026-03-01"}]
        result = detect_leading_trends(signals)
        assert result[0].first_detected == "2026-03-01"

    def test_first_detected_fallback(self):
        """first_detected 없으면 다른 날짜 필드 사용"""
        signals = [{"name": "트렌드", "signal_strength": 50, "date": "2026-02-15"}]
        result = detect_leading_trends(signals)
        assert result[0].first_detected == "2026-02-15"

    def test_sorted_by_signal_strength_desc(self):
        """신호 강도 내림차순 정렬"""
        signals = [
            {"name": "약한 트렌드", "signal_strength": 20},
            {"name": "강한 트렌드", "signal_strength": 90},
            {"name": "중간 트렌드", "signal_strength": 50},
        ]
        result = detect_leading_trends(signals)
        strengths = [t.signal_strength for t in result]
        assert strengths == sorted(strengths, reverse=True)

    def test_zero_strength_filtered(self):
        """신호 강도 0 → 결과에서 제외"""
        signals = [
            {"name": "무의미한 신호", "signal_strength": 0},
            {"name": "유효한 신호", "signal_strength": 50},
        ]
        result = detect_leading_trends(signals)
        assert len(result) == 1
        assert result[0].trend_name == "유효한 신호"

    def test_empty_name_skipped(self):
        """빈 이름 → 건너뛰기"""
        signals = [
            {"name": "", "signal_strength": 50},
            {"name": "유효 트렌드", "signal_strength": 40},
        ]
        result = detect_leading_trends(signals)
        assert len(result) == 1
        assert result[0].trend_name == "유효 트렌드"

    def test_recommended_content_urgent(self):
        """높은 신호 강도 → 긴급 콘텐츠 추천"""
        signals = [{"name": "AI 혁신", "signal_strength": 80}]
        result = detect_leading_trends(signals)
        assert "긴급" in result[0].recommended_content

    def test_recommended_content_early(self):
        """중간 신호 강도 → 조기 진입 콘텐츠 추천"""
        signals = [{"name": "새 분야", "signal_strength": 50}]
        result = detect_leading_trends(signals)
        assert "조기 진입" in result[0].recommended_content

    def test_recommended_content_monitor(self):
        """낮은 신호 강도 → 모니터링 콘텐츠 추천"""
        signals = [{"name": "초기 신호", "signal_strength": 15}]
        result = detect_leading_trends(signals)
        assert "모니터링" in result[0].recommended_content

    def test_leading_trend_dataclass_fields(self):
        """LeadingTrend 필드 타입 검증"""
        signals = [{"name": "테스트", "signal_strength": 50}]
        result = detect_leading_trends(signals)
        t = result[0]
        assert isinstance(t.trend_name, str)
        assert isinstance(t.signal_strength, float)
        assert isinstance(t.first_detected, str)
        assert isinstance(t.growth_rate, float)
        assert isinstance(t.category, str)
        assert isinstance(t.recommended_content, str)

    def test_signal_strength_capped_at_100(self):
        """신호 강도가 100을 초과하지 않음"""
        signals = [{"name": "강한 신호", "signal_strength": 200}]
        result = detect_leading_trends(signals)
        assert result[0].signal_strength <= 100.0

    def test_large_signal_list(self):
        """50개 신호 처리"""
        signals = [{"name": f"트렌드_{i}", "signal_strength": i * 2} for i in range(1, 51)]
        result = detect_leading_trends(signals)
        assert len(result) == 50
        # 정렬 검증
        assert result[0].signal_strength >= result[-1].signal_strength
