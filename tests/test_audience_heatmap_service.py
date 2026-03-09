"""audience_heatmap_service 단위 테스트"""
import unittest

from services.audience_heatmap_service import (
    AudienceHeatmap,
    SegmentData,
    generate_audience_heatmap,
    _classify_trend,
    _build_segment,
)


class TestClassifyTrend(unittest.TestCase):
    """추세 판별 함수 테스트"""

    def test_single_value_stable(self):
        self.assertEqual(_classify_trend([0.5]), "stable")

    def test_increasing_trend(self):
        self.assertEqual(_classify_trend([0.1, 0.2, 0.3]), "up")

    def test_decreasing_trend(self):
        self.assertEqual(_classify_trend([0.9, 0.7, 0.5]), "down")

    def test_stable_trend(self):
        self.assertEqual(_classify_trend([0.5, 0.51, 0.52]), "stable")

    def test_empty_values(self):
        self.assertEqual(_classify_trend([]), "stable")


class TestBuildSegment(unittest.TestCase):
    """세그먼트 빌드 함수 테스트"""

    def test_single_entry(self):
        entries = [{"engagement_rate": 0.8, "size": 100}]
        seg = _build_segment("test_seg", entries)
        self.assertEqual(seg.segment_name, "test_seg")
        self.assertEqual(seg.engagement_rate, 0.8)
        self.assertEqual(seg.size, 100)

    def test_multiple_entries_weighted_average(self):
        entries = [
            {"engagement_rate": 0.6, "size": 200},
            {"engagement_rate": 0.8, "size": 200},
        ]
        seg = _build_segment("multi", entries)
        self.assertEqual(seg.size, 400)
        self.assertAlmostEqual(seg.engagement_rate, 0.7, places=2)

    def test_zero_size_entries(self):
        entries = [{"engagement_rate": 0.5, "size": 0}]
        seg = _build_segment("zero", entries)
        self.assertEqual(seg.size, 0)
        self.assertEqual(seg.engagement_rate, 0.0)


class TestGenerateAudienceHeatmap(unittest.TestCase):
    """메인 히트맵 생성 함수 테스트"""

    def test_empty_data_returns_empty_heatmap(self):
        result = generate_audience_heatmap([])
        self.assertIsInstance(result, AudienceHeatmap)
        self.assertEqual(result.segments, [])
        self.assertEqual(result.total_audience, 0)

    def test_single_hot_segment(self):
        data = [{"segment": "core_fans", "engagement_rate": 0.9, "size": 500}]
        result = generate_audience_heatmap(data)
        self.assertEqual(len(result.segments), 1)
        self.assertIn("core_fans", result.hot_zones)
        self.assertEqual(result.cold_zones, [])
        self.assertEqual(result.total_audience, 500)

    def test_single_cold_segment(self):
        data = [{"segment": "inactive", "engagement_rate": 0.1, "size": 300}]
        result = generate_audience_heatmap(data)
        self.assertIn("inactive", result.cold_zones)
        self.assertEqual(result.hot_zones, [])

    def test_mixed_segments(self):
        data = [
            {"segment": "power_users", "engagement_rate": 0.85, "size": 100},
            {"segment": "casual", "engagement_rate": 0.35, "size": 400},
            {"segment": "dormant", "engagement_rate": 0.05, "size": 200},
        ]
        result = generate_audience_heatmap(data)
        self.assertEqual(len(result.segments), 3)
        self.assertIn("power_users", result.hot_zones)
        self.assertIn("dormant", result.cold_zones)
        self.assertNotIn("casual", result.hot_zones)
        self.assertNotIn("casual", result.cold_zones)
        self.assertEqual(result.total_audience, 700)

    def test_segments_sorted_by_engagement_desc(self):
        data = [
            {"segment": "low", "engagement_rate": 0.1, "size": 100},
            {"segment": "high", "engagement_rate": 0.9, "size": 100},
            {"segment": "mid", "engagement_rate": 0.5, "size": 100},
        ]
        result = generate_audience_heatmap(data)
        rates = [s.engagement_rate for s in result.segments]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_same_segment_grouped(self):
        data = [
            {"segment": "mobile", "engagement_rate": 0.6, "size": 100},
            {"segment": "mobile", "engagement_rate": 0.8, "size": 100},
        ]
        result = generate_audience_heatmap(data)
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].segment_name, "mobile")
        self.assertEqual(result.segments[0].size, 200)

    def test_missing_segment_name_defaults_to_unknown(self):
        data = [{"engagement_rate": 0.5, "size": 50}]
        result = generate_audience_heatmap(data)
        self.assertEqual(result.segments[0].segment_name, "unknown")

    def test_segment_data_dataclass_fields(self):
        seg = SegmentData(segment_name="test", engagement_rate=0.5, size=100, trend="up")
        self.assertEqual(seg.segment_name, "test")
        self.assertEqual(seg.trend, "up")


if __name__ == '__main__':
    unittest.main()
