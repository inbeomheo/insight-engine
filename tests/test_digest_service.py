"""
DigestService 단위 테스트 (F6-23)
"""
import unittest
from datetime import datetime, timezone, timedelta
from services.content.digest_service import DigestService


class TestDigestService(unittest.TestCase):

    def setUp(self):
        self.svc = DigestService()
        now = datetime.now(timezone.utc)
        self.recent_generations = [
            {'title': '블로그 1', 'style': 'blog_seo', 'model': 'gemini', 'tokens': 1000,
             'success': True, 'created_at': (now - timedelta(days=1)).isoformat()},
            {'title': '요약 1', 'style': 'summary', 'model': 'deepseek', 'tokens': 500,
             'success': True, 'created_at': (now - timedelta(days=2)).isoformat()},
            {'title': '블로그 2', 'style': 'blog_seo', 'model': 'gemini', 'tokens': 900,
             'success': False, 'created_at': (now - timedelta(days=3)).isoformat()},
        ]

    def test_build_digest_total(self):
        digest = self.svc.build_digest(self.recent_generations, period_days=7)
        self.assertEqual(digest['total_generations'], 3)
        self.assertEqual(digest['success_count'], 2)
        self.assertEqual(digest['failure_count'], 1)

    def test_build_digest_success_rate(self):
        digest = self.svc.build_digest(self.recent_generations, period_days=7)
        self.assertAlmostEqual(digest['success_rate'], 66.7, places=1)

    def test_top_styles(self):
        digest = self.svc.build_digest(self.recent_generations, period_days=7)
        top = digest['top_styles']
        self.assertEqual(top[0]['style'], 'blog_seo')
        self.assertEqual(top[0]['count'], 2)

    def test_old_items_excluded(self):
        old = [{
            'title': '오래된 글', 'style': 'summary', 'model': 'gemini',
            'tokens': 100, 'success': True,
            'created_at': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        }]
        digest = self.svc.build_digest(old, period_days=7)
        self.assertEqual(digest['total_generations'], 0)

    def test_to_text(self):
        digest = self.svc.build_digest(self.recent_generations, period_days=7)
        text = self.svc.to_text(digest)
        self.assertIn('총 생성', text)
        self.assertIn('blog_seo', text)

    def test_to_html(self):
        digest = self.svc.build_digest(self.recent_generations, period_days=7)
        html = self.svc.to_html(digest)
        self.assertIn('<html>', html)
        self.assertIn('blog_seo', html)

    def test_history_accumulated(self):
        self.svc.build_digest(self.recent_generations, period_days=7)
        self.svc.build_digest(self.recent_generations, period_days=7)
        self.assertEqual(len(self.svc.get_history()), 2)

    def test_empty_generations(self):
        digest = self.svc.build_digest([], period_days=7)
        self.assertEqual(digest['total_generations'], 0)
        self.assertEqual(digest['success_rate'], 0.0)


if __name__ == '__main__':
    unittest.main()
