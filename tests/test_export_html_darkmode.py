"""HTML 내보내기 다크모드 CSS 옵션 테스트."""
import unittest
from unittest.mock import patch

from app import create_app


class TestExportHtmlDarkMode(unittest.TestCase):
    """POST /api/export/html dark_mode 옵션 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000',
        }

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_dark_mode_false_no_dark_css(self, _mock_sb):
        """dark_mode=false이면 다크모드 미디어쿼리가 없어야 한다."""
        resp = self.client.post(
            '/api/export/html',
            json={'title': '테스트', 'html': '<p>내용</p>', 'dark_mode': False},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertNotIn('prefers-color-scheme: dark', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_dark_mode_true_includes_dark_css(self, _mock_sb):
        """dark_mode=true이면 다크모드 미디어쿼리가 포함되어야 한다."""
        resp = self.client.post(
            '/api/export/html',
            json={'title': '테스트', 'html': '<p>내용</p>', 'dark_mode': True},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('prefers-color-scheme: dark', html)
        self.assertIn('#1a1a2e', html)  # 다크 배경색

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_default_no_dark_mode(self, _mock_sb):
        """dark_mode 미지정 시 기본값은 비활성."""
        resp = self.client.post(
            '/api/export/html',
            json={'title': '테스트', 'html': '<p>내용</p>'},
            headers=self.headers,
        )
        html = resp.data.decode('utf-8')
        self.assertNotIn('prefers-color-scheme: dark', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_dark_mode_still_has_light_styles(self, _mock_sb):
        """다크모드 활성화해도 기본 라이트 스타일은 유지된다."""
        resp = self.client.post(
            '/api/export/html',
            json={'title': '테스트', 'html': '<p>내용</p>', 'dark_mode': True},
            headers=self.headers,
        )
        html = resp.data.decode('utf-8')
        self.assertIn('color: #1a1a1a', html)  # 라이트 기본색 유지
        self.assertIn('prefers-color-scheme: dark', html)


if __name__ == '__main__':
    unittest.main()
