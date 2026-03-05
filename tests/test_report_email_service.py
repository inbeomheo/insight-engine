"""
ReportEmailService 단위 테스트 (F4-23)
"""
import unittest
from services.report_email_service import ReportEmailService


class TestReportEmailService(unittest.TestCase):

    def setUp(self):
        self.svc = ReportEmailService()

    def test_generate_weekly_report(self):
        stats = {
            'total_generations': 42,
            'total_tokens': 150000,
            'top_styles': [{'name': 'blog_seo', 'count': 20}, {'name': 'summary', 'count': 15}],
        }
        result = self.svc.generate_report('u1', 'weekly', stats)
        self.assertIn('주간', result['subject'])
        self.assertIn('42', result['html'])
        self.assertIn('blog_seo', result['html'])

    def test_generate_monthly_report(self):
        result = self.svc.generate_report('u1', 'monthly', {'total_generations': 0, 'total_tokens': 0})
        self.assertIn('월간', result['subject'])

    def test_invalid_period_rejected(self):
        result = self.svc.generate_report('u1', 'daily', {})
        self.assertIn('error', result)

    def test_empty_styles(self):
        result = self.svc.generate_report('u1', 'weekly', {'total_generations': 5, 'total_tokens': 1000})
        self.assertNotIn('인기 스타일', result['html'])


if __name__ == '__main__':
    unittest.main()
