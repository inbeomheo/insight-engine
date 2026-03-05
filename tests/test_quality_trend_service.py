"""
QualityTrendService 단위 테스트 (F6-12)
"""
import unittest
from services.analytics.quality_trend_service import QualityTrendService


class TestQualityTrendService(unittest.TestCase):

    def setUp(self):
        self.svc = QualityTrendService()

    def test_record_and_trend(self):
        self.svc.record_score('c1', 80.0, style='blog_seo', timestamp='2026-01-01T00:00:00+00:00')
        self.svc.record_score('c2', 90.0, style='summary', timestamp='2026-01-02T00:00:00+00:00')
        trend = self.svc.get_trend(days=365)
        self.assertEqual(len(trend), 2)

    def test_score_clamped(self):
        self.svc.record_score('c1', -10.0)
        self.svc.record_score('c2', 150.0)
        stats = self.svc.get_overall_stats()
        self.assertEqual(stats['min_score'], 0.0)
        self.assertEqual(stats['max_score'], 100.0)

    def test_style_quality(self):
        self.svc.record_score('c1', 80.0, style='blog_seo')
        self.svc.record_score('c2', 60.0, style='blog_seo')
        self.svc.record_score('c3', 90.0, style='summary')
        by_style = self.svc.get_style_quality(365)
        styles = {s['style']: s for s in by_style}
        self.assertAlmostEqual(styles['blog_seo']['avg_score'], 70.0)
        self.assertAlmostEqual(styles['summary']['avg_score'], 90.0)
        # 내림차순 정렬
        self.assertGreaterEqual(by_style[0]['avg_score'], by_style[-1]['avg_score'])

    def test_model_quality(self):
        self.svc.record_score('c1', 85.0, model='gemini')
        self.svc.record_score('c2', 75.0, model='deepseek')
        by_model = self.svc.get_model_quality(365)
        self.assertEqual(len(by_model), 2)

    def test_overall_stats(self):
        self.svc.record_score('a', 70.0)
        self.svc.record_score('b', 90.0)
        stats = self.svc.get_overall_stats()
        self.assertEqual(stats['total'], 2)
        self.assertAlmostEqual(stats['avg_score'], 80.0)

    def test_empty_stats(self):
        stats = self.svc.get_overall_stats()
        self.assertEqual(stats['total'], 0)


if __name__ == '__main__':
    unittest.main()
