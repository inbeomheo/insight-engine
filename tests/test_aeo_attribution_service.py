"""AEO 귀속 분석 서비스 테스트"""
import unittest
from services.aeo_attribution_service import (
    attribute_ai_funnel,
    AttributionReport,
    _classify_source,
)


class TestClassifySource(unittest.TestCase):
    """소스 분류 테스트"""

    def test_ai_source(self):
        self.assertEqual(_classify_source("chatgpt"), "ai")
        self.assertEqual(_classify_source("ChatGPT"), "ai")
        self.assertEqual(_classify_source("perplexity"), "ai")

    def test_organic_source(self):
        self.assertEqual(_classify_source("google"), "organic")
        self.assertEqual(_classify_source("naver"), "organic")

    def test_direct_source(self):
        self.assertEqual(_classify_source("direct"), "direct")
        self.assertEqual(_classify_source("bookmark"), "direct")
        self.assertEqual(_classify_source("(direct)"), "direct")

    def test_unknown_source_fallback(self):
        """분류 불가한 소스는 organic으로 처리"""
        self.assertEqual(_classify_source("some_random_ref"), "organic")


class TestAttributeAiFunnel(unittest.TestCase):
    """AI 유입 귀속 테스트"""

    def test_empty_data(self):
        result = attribute_ai_funnel([])
        self.assertIsInstance(result, AttributionReport)
        self.assertEqual(result.total_visits, 0)
        self.assertEqual(result.conversion_rate, 0.0)

    def test_ai_traffic(self):
        data = [{"source": "chatgpt", "visits": 100, "conversions": 5}]
        result = attribute_ai_funnel(data)
        self.assertEqual(result.total_visits, 100)
        self.assertEqual(result.ai_attributed, 100)
        self.assertEqual(result.organic, 0)
        self.assertEqual(result.direct, 0)
        self.assertAlmostEqual(result.conversion_rate, 0.05)

    def test_mixed_traffic(self):
        data = [
            {"source": "chatgpt", "visits": 50, "conversions": 3},
            {"source": "google", "visits": 200, "conversions": 10},
            {"source": "direct", "visits": 30, "conversions": 1},
        ]
        result = attribute_ai_funnel(data)
        self.assertEqual(result.total_visits, 280)
        self.assertEqual(result.ai_attributed, 50)
        self.assertEqual(result.organic, 200)
        self.assertEqual(result.direct, 30)
        self.assertAlmostEqual(result.conversion_rate, round(14 / 280, 4))

    def test_negative_values_clamped(self):
        """음수 방문/전환은 0으로 처리"""
        data = [{"source": "google", "visits": -10, "conversions": -5}]
        result = attribute_ai_funnel(data)
        self.assertEqual(result.total_visits, 0)
        self.assertEqual(result.conversion_rate, 0.0)

    def test_channels_dict(self):
        data = [
            {"source": "chatgpt", "visits": 100, "conversions": 5},
            {"source": "claude", "visits": 50, "conversions": 2},
        ]
        result = attribute_ai_funnel(data)
        self.assertIn("ai", result.channels)
        self.assertEqual(result.channels["ai"]["visits"], 150)
        self.assertEqual(result.channels["ai"]["conversions"], 7)

    def test_missing_fields(self):
        """필드 누락 시 기본값"""
        data = [{"source": "google"}, {"visits": 10}]
        result = attribute_ai_funnel(data)
        self.assertEqual(result.total_visits, 10)

    def test_multiple_ai_sources(self):
        data = [
            {"source": "chatgpt", "visits": 40, "conversions": 2},
            {"source": "perplexity", "visits": 30, "conversions": 1},
            {"source": "gemini", "visits": 20, "conversions": 1},
        ]
        result = attribute_ai_funnel(data)
        self.assertEqual(result.ai_attributed, 90)
        self.assertEqual(result.total_visits, 90)

    def test_conversion_rate_calculation(self):
        data = [{"source": "google", "visits": 1000, "conversions": 50}]
        result = attribute_ai_funnel(data)
        self.assertAlmostEqual(result.conversion_rate, 0.05)


if __name__ == "__main__":
    unittest.main()
