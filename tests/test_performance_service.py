"""
PerformanceService 단위 테스트 (F6-02)
"""
import unittest
from services.analytics.performance_service import PerformanceService


class TestPerformanceService(unittest.TestCase):

    def setUp(self):
        self.svc = PerformanceService()

    def test_init_and_view(self):
        self.svc.init_content('c1', style='blog_seo')
        self.svc.record_view('c1')
        self.svc.record_view('c1')
        m = self.svc.get_metrics('c1')
        self.assertEqual(m['views'], 2)
        self.assertEqual(m['style'], 'blog_seo')

    def test_ctr_calculation(self):
        self.svc.init_content('c2')
        self.svc.record_impression('c2')
        self.svc.record_impression('c2')
        self.svc.record_click('c2')
        m = self.svc.get_metrics('c2')
        self.assertEqual(m['ctr'], 50.0)

    def test_auto_init_on_record(self):
        self.svc.record_view('c3')
        m = self.svc.get_metrics('c3')
        self.assertEqual(m['views'], 1)

    def test_top_contents(self):
        self.svc.init_content('a')
        self.svc.init_content('b')
        for _ in range(5):
            self.svc.record_view('a')
        for _ in range(3):
            self.svc.record_view('b')
        top = self.svc.get_top_contents(by='views', limit=2)
        self.assertEqual(top[0]['content_id'], 'a')

    def test_aggregate(self):
        self.svc.record_view('x')
        self.svc.record_share('x')
        agg = self.svc.get_aggregate()
        self.assertEqual(agg['total_contents'], 1)
        self.assertEqual(agg['total_views'], 1)
        self.assertEqual(agg['total_shares'], 1)

    def test_empty_metrics(self):
        m = self.svc.get_metrics('nonexistent')
        self.assertEqual(m, {})


if __name__ == '__main__':
    unittest.main()
