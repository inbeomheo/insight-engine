"""R55: DOCX 내보내기 font_size 옵션 테스트"""
import io
import unittest
from unittest.mock import patch


class TestDocxFontSize(unittest.TestCase):
    """font_size 옵션 (small/medium/large) 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def _export(self, font_size=None):
        payload = {'title': '테스트', 'content': '## 제목\n본문입니다.'}
        if font_size is not None:
            payload['font_size'] = font_size
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            return self.client.post('/api/export/docx',
                json=payload,
                headers={'Origin': 'http://localhost:3000'})

    def _get_font_size(self, resp):
        from docx import Document
        from docx.shared import Pt
        doc = Document(io.BytesIO(resp.data))
        normal = doc.styles['Normal']
        return normal.font.size

    def test_default_medium(self):
        """font_size 미지정 시 기본 11pt"""
        from docx.shared import Pt
        resp = self._export()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._get_font_size(resp), Pt(11))

    def test_small(self):
        """font_size=small → 9pt"""
        from docx.shared import Pt
        resp = self._export('small')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._get_font_size(resp), Pt(9))

    def test_large(self):
        """font_size=large → 14pt"""
        from docx.shared import Pt
        resp = self._export('large')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._get_font_size(resp), Pt(14))

    def test_invalid_falls_back_to_medium(self):
        """잘못된 값은 medium(11pt)으로 폴백"""
        from docx.shared import Pt
        resp = self._export('huge')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._get_font_size(resp), Pt(11))


if __name__ == '__main__':
    unittest.main()
