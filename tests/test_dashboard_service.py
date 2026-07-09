"""
DashboardService 단위 테스트 (F6-01)
"""
import unittest
from services.analytics.dashboard_service import DashboardService


class TestDashboardService(unittest.TestCase):

    def setUp(self):
        self.svc = DashboardService()

    def test_record_and_summary(self):
        self.svc.record_generation('summary', 'chatmock/gpt-5.4-mini', 1000, 2000, True)
        self.svc.record_generation('qna', 'chatmock/gpt-5.4', 800, 1500, False)
        summary = self.svc.get_summary(30)
        self.assertEqual(summary['total_generations'], 2)
        self.assertEqual(summary['success_count'], 1)
        self.assertEqual(summary['failure_count'], 1)
        self.assertEqual(summary['total_tokens'], 1800)
        self.assertEqual(summary['success_rate'], 50.0)

    def test_empty_summary(self):
        summary = self.svc.get_summary(30)
        self.assertEqual(summary['total_generations'], 0)
        self.assertEqual(summary['success_rate'], 0.0)

    def test_style_stats(self):
        self.svc.record_generation('blog_seo', 'model', 100, 500, True)
        self.svc.record_generation('blog_seo', 'model', 200, 600, True)
        self.svc.record_generation('summary', 'model', 150, 400, False)
        stats = self.svc.get_style_stats(30)
        style_names = [s['style'] for s in stats]
        self.assertIn('blog_seo', style_names)
        self.assertIn('summary', style_names)
        blog_stat = next(s for s in stats if s['style'] == 'blog_seo')
        self.assertEqual(blog_stat['count'], 2)
        self.assertEqual(blog_stat['success_rate'], 100.0)

    def test_model_stats(self):
        self.svc.record_generation('summary', 'chatmock/gpt-5.4-mini', 1000, 2000, True)
        self.svc.record_generation('qna', 'chatmock/gpt-5.4', 800, 1000, True)
        stats = self.svc.get_model_stats(30)
        model_names = [s['model'] for s in stats]
        self.assertIn('chatmock/gpt-5.4-mini', model_names)
        self.assertIn('chatmock/gpt-5.4', model_names)

    def test_daily_trend(self):
        self.svc.record_generation('summary', 'chatmock/gpt-5.4-mini', 100, 500, True, '2026-01-01T00:00:00+00:00')
        self.svc.record_generation('qna', 'chatmock/gpt-5.4-mini', 100, 500, True, '2026-01-01T12:00:00+00:00')
        self.svc.record_generation('summary', 'chatmock/gpt-5.4-mini', 100, 500, True, '2026-01-02T00:00:00+00:00')
        trend = self.svc.get_daily_trend(365)
        dates = {t['date'] for t in trend}
        self.assertIn('2026-01-01', dates)
        self.assertIn('2026-01-02', dates)
        day1 = next(t for t in trend if t['date'] == '2026-01-01')
        self.assertEqual(day1['count'], 2)


if __name__ == '__main__':
    unittest.main()
