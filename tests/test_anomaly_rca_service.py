"""
이상 탐지 근본 원인 분석 (RCA) 서비스 테스트

root_cause_analysis() 함수의 원인 추정, 확률 계산,
이상 유형 분류, 엣지 케이스를 검증합니다.
"""
import pytest

from services.anomaly_rca_service import (
    RCAReport,
    RootCause,
    root_cause_analysis,
)


class TestRootCauseAnalysis:
    """root_cause_analysis 핵심 기능 테스트"""

    def test_empty_data_returns_empty_report(self):
        """빈 데이터 → 빈 보고서"""
        result = root_cause_analysis({})
        assert isinstance(result, RCAReport)
        assert result.anomaly_type == "unknown"
        assert result.root_causes == []
        assert result.confidence == 0.0

    def test_none_data_returns_empty_report(self):
        """None 데이터 → 빈 보고서"""
        result = root_cause_analysis(None)
        assert result.anomaly_type == "unknown"
        assert result.confidence == 0.0

    def test_spike_traffic_cause(self):
        """트래픽 급증 스파이크 → 트래픽 원인 감지"""
        data = {
            "anomaly_type": "spike",
            "traffic_change": 200,
        }
        result = root_cause_analysis(data)
        assert result.anomaly_type == "spike"
        assert len(result.root_causes) > 0
        causes_text = [c.cause for c in result.root_causes]
        assert any("트래픽" in c for c in causes_text)

    def test_spike_bot_cause(self):
        """봇 비율 높은 스파이크 → 봇 원인 감지"""
        data = {
            "anomaly_type": "spike",
            "bot_ratio": 0.8,
        }
        result = root_cause_analysis(data)
        causes_text = [c.cause for c in result.root_causes]
        assert any("봇" in c for c in causes_text)

    def test_spike_campaign_cause(self):
        """캠페인 활성 스파이크 → 캠페인 원인 감지"""
        data = {
            "anomaly_type": "spike",
            "campaign_active": True,
        }
        result = root_cause_analysis(data)
        causes_text = [c.cause for c in result.root_causes]
        assert any("캠페인" in c for c in causes_text)

    def test_drop_error_rate_cause(self):
        """높은 에러율 하락 → 서버 장애 원인"""
        data = {
            "anomaly_type": "drop",
            "error_rate": 0.5,
        }
        result = root_cause_analysis(data)
        assert result.anomaly_type == "drop"
        causes_text = [c.cause for c in result.root_causes]
        assert any("서버" in c or "장애" in c for c in causes_text)

    def test_drop_bounce_rate_cause(self):
        """높은 이탈률 하락 → 콘텐츠 품질 원인"""
        data = {
            "anomaly_type": "drop",
            "bounce_rate": 0.85,
        }
        result = root_cause_analysis(data)
        causes_text = [c.cause for c in result.root_causes]
        assert any("콘텐츠" in c or "품질" in c for c in causes_text)

    def test_drop_seo_ranking_cause(self):
        """SEO 순위 하락 → SEO 원인"""
        data = {
            "anomaly_type": "drop",
            "ranking_change": -10,
        }
        result = root_cause_analysis(data)
        causes_text = [c.cause for c in result.root_causes]
        assert any("SEO" in c or "순위" in c for c in causes_text)

    def test_inferred_type_from_metric_change(self):
        """anomaly_type 없을 때 metric_change로 추론"""
        data = {"metric_change": 50}
        result = root_cause_analysis(data)
        assert result.anomaly_type == "spike"

        data2 = {"metric_change": -30}
        result2 = root_cause_analysis(data2)
        assert result2.anomaly_type == "drop"

    def test_probabilities_sum_lte_one(self):
        """확률 합이 1.0 이하"""
        data = {
            "anomaly_type": "spike",
            "traffic_change": 150,
            "bot_ratio": 0.6,
            "campaign_active": True,
        }
        result = root_cause_analysis(data)
        total_prob = sum(c.probability for c in result.root_causes)
        assert total_prob <= 1.01  # 부동소수점 허용

    def test_causes_sorted_by_probability(self):
        """원인이 확률 내림차순으로 정렬"""
        data = {
            "anomaly_type": "drop",
            "error_rate": 0.3,
            "bounce_rate": 0.8,
            "ranking_change": -8,
            "competitor_growth": 30,
        }
        result = root_cause_analysis(data)
        if len(result.root_causes) >= 2:
            probs = [c.probability for c in result.root_causes]
            assert probs == sorted(probs, reverse=True)

    def test_confidence_range(self):
        """신뢰도가 0~1 범위"""
        data = {"anomaly_type": "spike", "traffic_change": 100}
        result = root_cause_analysis(data)
        assert 0 <= result.confidence <= 1.0

    def test_recommended_fix_not_empty(self):
        """권장 조치가 항상 존재"""
        data = {"anomaly_type": "spike", "traffic_change": 100}
        result = root_cause_analysis(data)
        assert len(result.recommended_fix) > 0

    def test_root_cause_dataclass_fields(self):
        """RootCause 필드 타입 검증"""
        data = {"anomaly_type": "spike", "traffic_change": 200}
        result = root_cause_analysis(data)
        for cause in result.root_causes:
            assert isinstance(cause.cause, str)
            assert isinstance(cause.probability, float)
            assert isinstance(cause.evidence, list)
            assert isinstance(cause.category, str)

    def test_anomaly_type_with_seasonal(self):
        """범용 anomaly 타입 — 계절적 패턴 감지"""
        data = {
            "anomaly_type": "anomaly",
            "is_seasonal": True,
        }
        result = root_cause_analysis(data)
        causes_text = [c.cause for c in result.root_causes]
        assert any("계절" in c or "주기" in c for c in causes_text)

    def test_no_matching_rules_low_confidence(self):
        """규칙 매칭 없음 → 낮은 신뢰도"""
        data = {
            "anomaly_type": "spike",
            "traffic_change": 5,  # 100 미만 → 매칭 안 됨
            "bot_ratio": 0.1,     # 0.5 미만
        }
        result = root_cause_analysis(data)
        assert result.confidence <= 0.5

    def test_evidence_populated(self):
        """증거 필드가 채워지는지 확인"""
        data = {"anomaly_type": "spike", "traffic_change": 300}
        result = root_cause_analysis(data)
        traffic_causes = [c for c in result.root_causes if "트래픽" in c.cause]
        if traffic_causes:
            assert len(traffic_causes[0].evidence) > 0
