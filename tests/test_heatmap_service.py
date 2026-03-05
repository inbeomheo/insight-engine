"""
HeatmapService 단위 테스트 (F6-09)
"""
import unittest
from services.analytics.heatmap_service import HeatmapService


class TestHeatmapService(unittest.TestCase):

    def setUp(self):
        self.svc = HeatmapService()

    def test_click_heatmap_basic(self):
        self.svc.record_click('c1', 100, 200)
        self.svc.record_click('c1', 100, 200)
        self.svc.record_click('c1', 500, 300)
        result = self.svc.get_click_heatmap('c1', grid_size=100)
        self.assertEqual(result['total_clicks'], 3)
        self.assertGreater(len(result['cells']), 0)
        # 첫 번째 셀이 가장 많이 클릭된 셀이어야 함
        self.assertEqual(result['cells'][0]['count'], 2)

    def test_click_heatmap_empty(self):
        result = self.svc.get_click_heatmap('nonexistent')
        self.assertEqual(result['total_clicks'], 0)
        self.assertEqual(result['cells'], [])

    def test_scroll_distribution(self):
        self.svc.record_scroll('c2', 10)
        self.svc.record_scroll('c2', 25)
        self.svc.record_scroll('c2', 75)
        self.svc.record_scroll('c2', 100)
        result = self.svc.get_scroll_distribution('c2')
        self.assertEqual(result['total_scroll_events'], 4)
        self.assertAlmostEqual(result['avg_depth_pct'], 52.5)
        self.assertGreater(len(result['buckets']), 0)

    def test_scroll_depth_clamped(self):
        self.svc.record_scroll('c3', -10)   # 0으로 클램프
        self.svc.record_scroll('c3', 150)   # 100으로 클램프
        result = self.svc.get_scroll_distribution('c3')
        self.assertAlmostEqual(result['avg_depth_pct'], 50.0)

    def test_scroll_empty(self):
        result = self.svc.get_scroll_distribution('empty')
        self.assertEqual(result['avg_depth_pct'], 0)

    def test_aggregate_scroll(self):
        self.svc.record_scroll('a', 50)
        self.svc.record_scroll('b', 100)
        agg = self.svc.get_aggregate_scroll()
        self.assertAlmostEqual(agg['avg_depth_pct'], 75.0)
        self.assertEqual(agg['total_events'], 2)


if __name__ == '__main__':
    unittest.main()
