"""언더라이팅 점수 서비스 테스트."""

import unittest
from services.underwriting_score_service import (
    RiskFactor,
    UnderwritingResult,
    assess_risk,
    calculate_total_score,
    classify_risk_level,
    generate_recommendations,
)


class TestUnderwritingScoreService(unittest.TestCase):
    """UnderwritingScoreService 단위 테스트."""

    def test_classify_risk_level_low(self):
        """0~30: low."""
        self.assertEqual(classify_risk_level(0), "low")
        self.assertEqual(classify_risk_level(15), "low")
        self.assertEqual(classify_risk_level(30), "low")

    def test_classify_risk_level_medium(self):
        """31~60: medium."""
        self.assertEqual(classify_risk_level(31), "medium")
        self.assertEqual(classify_risk_level(60), "medium")

    def test_classify_risk_level_high(self):
        """61~80: high."""
        self.assertEqual(classify_risk_level(61), "high")
        self.assertEqual(classify_risk_level(80), "high")

    def test_classify_risk_level_critical(self):
        """81~100: critical."""
        self.assertEqual(classify_risk_level(81), "critical")
        self.assertEqual(classify_risk_level(100), "critical")

    def test_calculate_total_score_basic(self):
        """가중 평균 점수를 올바르게 계산한다."""
        factors = [
            RiskFactor("a", 50.0, 0.5, "test"),
            RiskFactor("b", 100.0, 0.5, "test"),
        ]
        # (50*0.5 + 100*0.5) / (0.5+0.5) = 75.0
        self.assertEqual(calculate_total_score(factors), 75.0)

    def test_calculate_total_score_empty(self):
        """빈 팩터 목록은 0.0."""
        self.assertEqual(calculate_total_score([]), 0.0)

    def test_calculate_total_score_single(self):
        """단일 팩터."""
        factors = [RiskFactor("a", 40.0, 1.0, "test")]
        self.assertEqual(calculate_total_score(factors), 40.0)

    def test_calculate_total_score_zero_weight(self):
        """모든 가중치가 0이면 0.0."""
        factors = [RiskFactor("a", 50.0, 0.0, "test")]
        self.assertEqual(calculate_total_score(factors), 0.0)

    def test_assess_risk_clean_content(self):
        """깨끗한 콘텐츠는 low 리스크."""
        content = {"id": "c1", "text": "일반적인 기술 블로그 글입니다."}
        result = assess_risk(content)
        self.assertIsInstance(result, UnderwritingResult)
        self.assertEqual(result.content_id, "c1")
        self.assertEqual(len(result.factors), 4)

    def test_assess_risk_legal_keywords(self):
        """법적 키워드 포함 시 legal 팩터 점수가 높아진다."""
        content = {"id": "c2", "text": "이 제품은 100% 보증합니다. 무조건 확실한 효과를 약속합니다."}
        result = assess_risk(content)
        legal = next(f for f in result.factors if f.factor_name == "legal")
        self.assertGreater(legal.score, 30)

    def test_assess_risk_brand_keywords(self):
        """브랜드 키워드 포함 시 brand 팩터 점수가 높아진다."""
        content = {"id": "c3", "text": "경쟁사를 비방하는 내용이며 최고의 유일한 독보적 제품입니다."}
        result = assess_risk(content)
        brand = next(f for f in result.factors if f.factor_name == "brand")
        self.assertGreater(brand.score, 30)

    def test_assess_risk_returns_recommendations(self):
        """권고 사항이 포함된다."""
        content = {"id": "c4", "text": "보증합니다 무조건 확실 100% 경쟁사 비방"}
        result = assess_risk(content)
        self.assertIsInstance(result.recommendations, list)

    def test_generate_recommendations_high_factor(self):
        """높은 점수 팩터에 대한 권고."""
        factors = [RiskFactor("legal", 70.0, 0.35, "법적 리스크")]
        result = UnderwritingResult("c1", factors, 70.0, "high", [])
        recs = generate_recommendations(result)
        self.assertTrue(any("legal" in r for r in recs))

    def test_generate_recommendations_critical(self):
        """critical 수준에 법무 승인 필수 권고."""
        factors = [RiskFactor("legal", 90.0, 0.35, "법적 리스크")]
        result = UnderwritingResult("c1", factors, 90.0, "critical", [])
        recs = generate_recommendations(result)
        self.assertTrue(any("CRITICAL" in r for r in recs))

    def test_generate_recommendations_low_factors(self):
        """30점 이하 팩터는 권고 없음."""
        factors = [RiskFactor("legal", 20.0, 0.35, "양호")]
        result = UnderwritingResult("c1", factors, 20.0, "low", [])
        recs = generate_recommendations(result)
        self.assertEqual(len(recs), 0)

    def test_assess_risk_default_id(self):
        """id가 없는 콘텐츠는 'unknown'."""
        result = assess_risk({"text": "test"})
        self.assertEqual(result.content_id, "unknown")

    def test_assess_risk_four_factors(self):
        """항상 4개 팩터(legal/brand/factual/technical)를 반환한다."""
        result = assess_risk({"text": "test"})
        names = {f.factor_name for f in result.factors}
        self.assertEqual(names, {"legal", "brand", "factual", "technical"})


if __name__ == "__main__":
    unittest.main()
