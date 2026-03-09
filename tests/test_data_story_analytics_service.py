"""data_story_analytics_service 단위 테스트"""
import unittest

from services.data_story_analytics_service import (
    DataStoryAnalytics,
    analyze_data_story,
    _compute_stats,
    _detect_trend,
    _find_anomalies,
)


class TestComputeStats(unittest.TestCase):
    """통계 계산 테스트"""

    def test_normal_values(self):
        stats = _compute_stats([10.0, 20.0, 30.0])
        self.assertEqual(stats["mean"], 20.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 30.0)

    def test_empty_values(self):
        stats = _compute_stats([])
        self.assertEqual(stats["mean"], 0)
        self.assertEqual(stats["std"], 0)

    def test_single_value(self):
        stats = _compute_stats([5.0])
        self.assertEqual(stats["mean"], 5.0)
        self.assertEqual(stats["std"], 0)


class TestDetectTrend(unittest.TestCase):
    """추세 감지 테스트"""

    def test_increasing(self):
        self.assertEqual(_detect_trend([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), "increasing")

    def test_decreasing(self):
        self.assertEqual(_detect_trend([10, 9, 8, 7, 6, 5, 4, 3, 2, 1]), "decreasing")

    def test_stable(self):
        self.assertEqual(_detect_trend([5, 5, 5, 5, 5]), "stable")

    def test_single_value_stable(self):
        self.assertEqual(_detect_trend([5]), "stable")


class TestFindAnomalies(unittest.TestCase):
    """이상치 탐지 테스트"""

    def test_no_anomalies(self):
        metrics = [{"label": "a", "value": 5}, {"label": "b", "value": 5}]
        stats = _compute_stats([5.0, 5.0])
        result = _find_anomalies(metrics, [5.0, 5.0], stats)
        self.assertEqual(result, [])

    def test_detects_high_anomaly(self):
        values = [5.0, 5.0, 5.0, 5.0, 5.0, 100.0]
        metrics = [{"label": f"p{i}"} for i in range(6)]
        stats = _compute_stats(values)
        result = _find_anomalies(metrics, values, stats)
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["direction"], "high")


class TestAnalyzeDataStory(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_metrics(self):
        result = analyze_data_story([])
        self.assertIsInstance(result, DataStoryAnalytics)
        self.assertEqual(result.trend_direction, "stable")
        self.assertIn("데이터가 없습니다", result.narrative)

    def test_increasing_narrative(self):
        metrics = [{"label": f"day{i}", "value": float(i * 10)} for i in range(1, 11)]
        result = analyze_data_story(metrics)
        self.assertEqual(result.trend_direction, "increasing")
        self.assertIn("상승", result.narrative)

    def test_insights_generated(self):
        metrics = [{"label": f"d{i}", "value": float(i * 5)} for i in range(1, 8)]
        result = analyze_data_story(metrics)
        self.assertTrue(len(result.key_insights) > 0)

    def test_anomalies_detected(self):
        # 정상 값 + 극단 이상치
        metrics = [{"label": f"p{i}", "value": 10.0} for i in range(10)]
        metrics.append({"label": "outlier", "value": 1000.0})
        result = analyze_data_story(metrics)
        self.assertTrue(len(result.anomalies) > 0)

    def test_narrative_contains_count(self):
        metrics = [{"label": "a", "value": 1.0}, {"label": "b", "value": 2.0}]
        result = analyze_data_story(metrics)
        self.assertIn("2개", result.narrative)

    def test_stable_small_variation(self):
        metrics = [{"label": f"d{i}", "value": 50.0 + (i % 2) * 0.1} for i in range(10)]
        result = analyze_data_story(metrics)
        self.assertIn(result.trend_direction, ["stable", "increasing"])

    def test_dataclass_fields(self):
        analytics = DataStoryAnalytics(
            narrative="테스트",
            key_insights=["인사이트"],
            trend_direction="stable",
            anomalies=[{"index": 0}],
        )
        self.assertEqual(analytics.narrative, "테스트")
        self.assertEqual(len(analytics.anomalies), 1)

    def test_volatile_data(self):
        # 큰 변동성 데이터
        metrics = [
            {"label": "d1", "value": 100.0},
            {"label": "d2", "value": 1.0},
            {"label": "d3", "value": 100.0},
            {"label": "d4", "value": 1.0},
            {"label": "d5", "value": 100.0},
        ]
        result = analyze_data_story(metrics)
        self.assertEqual(result.trend_direction, "volatile")


if __name__ == '__main__':
    unittest.main()
