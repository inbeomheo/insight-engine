"""auto_newsletter_service 단위 테스트 (내부 빌더 위주)"""
import unittest

from services.auto_newsletter_service import (
    AutoNewsletterService,
    NewsletterIssue,
)


class TestNewsletterIssue(unittest.TestCase):

    def test_dataclass_fields(self):
        """NewsletterIssue 필수 필드"""
        issue = NewsletterIssue(
            issue_id='123',
            subject='테스트 뉴스레터',
            html_body='<h1>Hello</h1>',
            text_body='Hello',
            recipients=['a@b.com'],
        )
        self.assertEqual(issue.issue_id, '123')
        self.assertEqual(issue.subject, '테스트 뉴스레터')
        self.assertEqual(issue.sent_count, 0)
        self.assertEqual(issue.failed_count, 0)

    def test_default_counts(self):
        """기본 sent_count, failed_count = 0"""
        issue = NewsletterIssue('1', 'S', '<p>H</p>', 'T', [])
        self.assertEqual(issue.sent_count, 0)
        self.assertEqual(issue.failed_count, 0)

    def test_created_at_auto(self):
        """created_at 자동 생성"""
        issue = NewsletterIssue('1', 'S', 'H', 'T', [])
        self.assertIsInstance(issue.created_at, float)
        self.assertGreater(issue.created_at, 0)


class TestBuildHtml(unittest.TestCase):

    def setUp(self):
        self.svc = AutoNewsletterService()

    def test_contains_title(self):
        """HTML에 제목 포함"""
        html = self.svc._build_html('주간 뉴스', [])
        self.assertIn('주간 뉴스', html)

    def test_contains_item_title(self):
        """HTML에 아이템 제목 포함"""
        summaries = [{'title': '첫 번째 글', 'summary': '요약입니다', 'url': 'https://a.com'}]
        html = self.svc._build_html('뉴스레터', summaries)
        self.assertIn('첫 번째 글', html)
        self.assertIn('요약입니다', html)

    def test_contains_url_link(self):
        """URL이 있으면 원문 보기 링크 포함"""
        summaries = [{'title': 'T', 'summary': 'S', 'url': 'https://example.com'}]
        html = self.svc._build_html('뉴스', summaries)
        self.assertIn('https://example.com', html)
        self.assertIn('원문 보기', html)

    def test_no_url_no_link(self):
        """URL 없으면 원문 보기 없음"""
        summaries = [{'title': 'T', 'summary': 'S', 'url': ''}]
        html = self.svc._build_html('뉴스', summaries)
        self.assertNotIn('원문 보기', html)

    def test_valid_html_structure(self):
        """유효한 HTML 구조"""
        html = self.svc._build_html('테스트', [])
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<html>', html)
        self.assertIn('</html>', html)


class TestBuildText(unittest.TestCase):

    def setUp(self):
        self.svc = AutoNewsletterService()

    def test_contains_title(self):
        """텍스트에 제목 포함"""
        text = self.svc._build_text('주간 리포트', [])
        self.assertIn('주간 리포트', text)

    def test_contains_items(self):
        """텍스트에 아이템 포함"""
        summaries = [{'title': '글 제목', 'summary': '글 요약', 'url': 'https://a.com'}]
        text = self.svc._build_text('뉴스레터', summaries)
        self.assertIn('글 제목', text)
        self.assertIn('글 요약', text)
        self.assertIn('https://a.com', text)

    def test_separator(self):
        """텍스트에 구분자 포함"""
        text = self.svc._build_text('뉴스레터 제목', [])
        self.assertIn('=', text)  # title underline

    def test_footer(self):
        """텍스트에 푸터 포함"""
        text = self.svc._build_text('뉴스', [])
        self.assertIn('Insight Engine', text)


class TestSend(unittest.TestCase):

    def setUp(self):
        self.svc = AutoNewsletterService()

    def test_empty_recipients(self):
        """수신자 없음 → 에러 응답"""
        issue = NewsletterIssue('1', 'S', 'H', 'T', [])
        result = self.svc.send(issue, [])
        self.assertEqual(result['sent'], 0)
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
