"""utm_lineage_service 단위 테스트"""
import unittest

from services.utm_lineage_service import (
    UTMLineage,
    CampaignTrace,
    trace_utm_lineage,
    _build_campaign_key,
    _aggregate_campaigns,
)


class TestBuildCampaignKey(unittest.TestCase):
    """캠페인 키 생성 테스트"""

    def test_full_utm_params(self):
        entry = {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "spring"}
        key = _build_campaign_key(entry)
        self.assertEqual(key, "google|cpc|spring")

    def test_missing_params_defaults(self):
        key = _build_campaign_key({})
        self.assertEqual(key, "direct|none|unknown")


class TestAggregateCampaigns(unittest.TestCase):
    """캠페인 집계 테스트"""

    def test_single_entry(self):
        data = [{"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "q1", "visits": 100, "conversions": 10}]
        result = _aggregate_campaigns(data)
        self.assertEqual(len(result), 1)
        key = "google|cpc|q1"
        self.assertEqual(result[key]["visits"], 100)

    def test_same_campaign_merged(self):
        data = [
            {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "q1", "visits": 50, "conversions": 5},
            {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "q1", "visits": 30, "conversions": 3},
        ]
        result = _aggregate_campaigns(data)
        self.assertEqual(len(result), 1)
        key = "google|cpc|q1"
        self.assertEqual(result[key]["visits"], 80)
        self.assertEqual(result[key]["conversions"], 8)


class TestTraceUtmLineage(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_data(self):
        result = trace_utm_lineage([])
        self.assertIsInstance(result, UTMLineage)
        self.assertEqual(result.campaigns, [])
        self.assertEqual(result.total_touchpoints, 0)
        self.assertEqual(result.top_performing, "")

    def test_single_campaign(self):
        data = [{"utm_source": "naver", "utm_medium": "display", "utm_campaign": "brand", "visits": 200, "conversions": 20}]
        result = trace_utm_lineage(data)
        self.assertEqual(len(result.campaigns), 1)
        self.assertEqual(result.total_touchpoints, 200)
        self.assertEqual(result.top_performing, "brand")

    def test_multiple_campaigns_attribution(self):
        data = [
            {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "search", "visits": 100, "conversions": 30},
            {"utm_source": "facebook", "utm_medium": "social", "utm_campaign": "retarget", "visits": 200, "conversions": 10},
        ]
        result = trace_utm_lineage(data)
        self.assertEqual(len(result.campaigns), 2)
        self.assertEqual(result.total_touchpoints, 300)
        # search 캠페인이 전환율 더 높음
        self.assertEqual(result.top_performing, "search")

    def test_attribution_weights_sum_to_one(self):
        data = [
            {"utm_source": "a", "utm_medium": "m", "utm_campaign": "c1", "visits": 100, "conversions": 10},
            {"utm_source": "b", "utm_medium": "m", "utm_campaign": "c2", "visits": 200, "conversions": 20},
            {"utm_source": "c", "utm_medium": "m", "utm_campaign": "c3", "visits": 50, "conversions": 5},
        ]
        result = trace_utm_lineage(data)
        total_weight = sum(c.attribution_weight for c in result.campaigns)
        self.assertAlmostEqual(total_weight, 1.0, places=2)

    def test_campaigns_sorted_by_weight(self):
        data = [
            {"utm_source": "a", "utm_medium": "m", "utm_campaign": "low", "visits": 100, "conversions": 1},
            {"utm_source": "b", "utm_medium": "m", "utm_campaign": "high", "visits": 100, "conversions": 50},
        ]
        result = trace_utm_lineage(data)
        weights = [c.attribution_weight for c in result.campaigns]
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_zero_conversions_equal_weight(self):
        data = [
            {"utm_source": "a", "utm_medium": "m", "utm_campaign": "c1", "visits": 100, "conversions": 0},
            {"utm_source": "b", "utm_medium": "m", "utm_campaign": "c2", "visits": 200, "conversions": 0},
        ]
        result = trace_utm_lineage(data)
        weights = [c.attribution_weight for c in result.campaigns]
        self.assertAlmostEqual(weights[0], weights[1], places=2)

    def test_campaign_trace_dataclass(self):
        trace = CampaignTrace(
            utm_source="google", utm_medium="cpc", utm_campaign="test",
            visits=100, conversions=10, attribution_weight=0.5,
        )
        self.assertEqual(trace.utm_source, "google")
        self.assertEqual(trace.attribution_weight, 0.5)

    def test_default_visits_one(self):
        data = [{"utm_source": "x", "utm_medium": "y", "utm_campaign": "z"}]
        result = trace_utm_lineage(data)
        self.assertEqual(result.campaigns[0].visits, 1)


if __name__ == '__main__':
    unittest.main()
