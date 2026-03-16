"""TXT 내보내기 줄바꿈 스타일 옵션 테스트 (R37)."""
import unittest
from unittest.mock import patch

from services.export.export_service import export_txt


class TestExportTxtLineEnding(unittest.TestCase):
    """export_txt의 line_ending 파라미터 검증."""

    def test_default_unix_line_ending(self):
        """기본값은 LF (\\n)."""
        buf = export_txt('제목', '첫 줄\n둘째 줄\n셋째 줄')
        text = buf.getvalue().decode('utf-8')
        self.assertNotIn('\r\n', text)
        self.assertIn('\n', text)

    def test_windows_line_ending(self):
        """line_ending='windows' → CRLF (\\r\\n)."""
        buf = export_txt('제목', '첫 줄\n둘째 줄', line_ending='windows')
        text = buf.getvalue().decode('utf-8')
        # 모든 줄바꿈이 CRLF여야 함
        lines_crlf = text.split('\r\n')
        self.assertGreater(len(lines_crlf), 1)
        # LF 단독은 없어야 함
        stripped = text.replace('\r\n', '')
        self.assertNotIn('\n', stripped)

    def test_unix_explicit(self):
        """line_ending='unix' → LF만."""
        buf = export_txt('제목', '줄1\n줄2', line_ending='unix')
        text = buf.getvalue().decode('utf-8')
        self.assertNotIn('\r\n', text)

    def test_api_endpoint_accepts_line_ending(self):
        """API 엔드포인트가 line_ending 파라미터를 수용."""
        from app import create_app

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            resp = client.post('/api/export/txt',
                json={'title': '테스트', 'content': '줄1\n줄2', 'line_ending': 'windows'},
                headers={'Origin': 'http://localhost:3000'})
            self.assertEqual(resp.status_code, 200)
            data = resp.data.decode('utf-8')
            self.assertIn('\r\n', data)

    def test_api_ignores_invalid_line_ending(self):
        """잘못된 line_ending 값은 unix로 폴백."""
        from app import create_app

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            resp = client.post('/api/export/txt',
                json={'title': '테스트', 'content': '줄1\n줄2', 'line_ending': 'mac'},
                headers={'Origin': 'http://localhost:3000'})
            self.assertEqual(resp.status_code, 200)
            data = resp.data.decode('utf-8')
            self.assertNotIn('\r\n', data)


if __name__ == '__main__':
    unittest.main()
