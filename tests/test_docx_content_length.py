"""R20: /api/export/docx 응답에 Content-Length 헤더 포함 검증"""
import unittest
from unittest.mock import patch


class TestDocxContentLength(unittest.TestCase):
    """DOCX 내보내기 응답의 Content-Length 헤더 검증"""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def setUp(self, _mock_sb):
        import app as flask_app
        self.app = flask_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_content_length_header_present(self, _mock_sb):
        """DOCX 응답에 Content-Length 헤더가 있어야 함"""
        resp = self.client.post(
            '/api/export/docx',
            json={'title': '테스트 문서', 'content': '# 제목\n\n본문 텍스트입니다.'},
            headers={'Origin': 'http://localhost:3000'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Content-Length', resp.headers)
        content_length = int(resp.headers['Content-Length'])
        self.assertGreater(content_length, 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_content_length_matches_body(self, _mock_sb):
        """Content-Length가 실제 바디 크기와 일치해야 함"""
        resp = self.client.post(
            '/api/export/docx',
            json={'title': 'Length Test', 'content': '## 섹션\n\n- 항목 1\n- 항목 2\n- 항목 3'},
            headers={'Origin': 'http://localhost:3000'}
        )
        self.assertEqual(resp.status_code, 200)
        content_length = int(resp.headers['Content-Length'])
        body = resp.data
        self.assertEqual(content_length, len(body))

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_content_returns_400(self, _mock_sb):
        """빈 콘텐츠는 400 에러 반환"""
        resp = self.client.post(
            '/api/export/docx',
            json={'title': 'Empty', 'content': ''},
            headers={'Origin': 'http://localhost:3000'}
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
