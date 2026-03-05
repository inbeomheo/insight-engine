"""
StylePerformanceService 단위 테스트 (F6-13)
"""
import unittest
from services.analytics.style_performance_service import StylePerformanceService


class TestStylePerformanceService(unittest.TestCase):

    def setUp(self):
        self.svc = StylePerformanceService()

    def test_record_and_comparison(self):
        self.svc.record('blog_seo', quality_score=80.0, views=100, tokens=1000)
        self.svc.record('blog_seo', quality_score=90.0, views=200, tokens=1200)
        self.svc.record('summary', quality_score=70.0, views=50, tokens=500)
        comparison = self.svc.get_comparison()
        styles = {c['style']: c for c in comparison}
        self.assertIn('blog_seo', styles)
        self.assertIn('summary', styles)
        self.assertAlmostEqual(styles['blog_seo']['avg_quality'], 85.0)
        self.assertEqual(styles['blog_seo']['count'], 2)

    def test_sorted_by_quality(self):
        self.svc.record('low', quality_score=50.0)
        self.svc.record('high', quality_score=95.0)
        comparison = self.svc.get_comparison()
        self.assertGreaterEqual(comparison[0]['avg_quality'], comparison[-1]['avg_quality'])

    def test_top_style(self):
        self.svc.record('blog_seo', quality_score=90.0, views=100)
        self.svc.record('summary', quality_score=70.0, views=500)
        top_by_quality = self.svc.get_top_style('avg_quality')
        self.assertEqual(top_by_quality['style'], 'blog_seo')
        top_by_views = self.svc.get_top_style('avg_views')
        self.assertEqual(top_by_views['style'], 'summary')

    def test_empty_comparison(self):
        result = self.svc.get_comparison()
        self.assertEqual(result, [])

    def test_empty_top_style(self):
        result = self.svc.get_top_style()
        self.assertIsNone(result)

    def test_style_detail(self):
        self.svc.record('blog_seo', quality_score=80.0)
        self.svc.record('blog_seo', quality_score=90.0)
        detail = self.svc.get_style_detail('blog_seo')
        self.assertEqual(detail['count'], 2)
        self.assertAlmostEqual(detail['avg_quality'], 85.0)
        self.assertAlmostEqual(detail['min_quality'], 80.0)
        self.assertAlmostEqual(detail['max_quality'], 90.0)

    def test_nonexistent_style_detail(self):
        detail = self.svc.get_style_detail('nonexistent')
        self.assertEqual(detail['count'], 0)


if __name__ == '__main__':
    unittest.main()
