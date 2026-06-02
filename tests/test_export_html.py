"""HTML 내보내기 API 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestExportHtml(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_exports_html_file(self, _mock_sb):
        """HTML 파일로 다운로드."""
        resp = self.client.post('/api/export/html',
                                json={'title': '테스트 제목', 'html': '<p>본문</p>'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/html', resp.content_type)
        html = resp.data.decode('utf-8')
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('테스트 제목', html)
        self.assertIn('<p>본문</p>', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_content_returns_400(self, _mock_sb):
        """빈 콘텐츠는 400."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'x', 'html': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_markdown_content_is_rendered_to_html(self, _mock_sb):
        """content로 받은 마크다운은 raw MD가 아니라 HTML로 내려간다."""
        resp = self.client.post('/api/export/html',
                                json={'title': '문서', 'content': '# 섹션\n\n**굵게** 본문'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('<h1>섹션</h1>', html)
        self.assertIn('<strong>굵게</strong>', html)
        self.assertNotIn('**굵게**', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_includes_inline_css(self, _mock_sb):
        """인라인 CSS 포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'CSS 테스트', 'html': '<p>ok</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('<style>', html)
        self.assertIn('font-family', html)


    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_lang_auto_detect_korean(self, _mock_sb):
        """한국어 콘텐츠에 lang='ko' 설정."""
        resp = self.client.post('/api/export/html',
                                json={'title': '테스트', 'html': '<p>한국어 콘텐츠입니다</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('lang="ko"', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_lang_auto_detect_english(self, _mock_sb):
        """영어 콘텐츠에 lang='en' 설정."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'Test', 'html': '<p>This is English content for testing</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('lang="en"', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_lang_auto_detect_japanese(self, _mock_sb):
        """일본어 콘텐츠에 lang='ja' 설정."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'テスト', 'html': '<p>これはテストです</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('lang="ja"', html)


if __name__ == '__main__':
    unittest.main()
