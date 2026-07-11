"""export_service Markdown 단위 테스트"""
import io
import unittest

from services.export.export_service import export_markdown


class TestExportMarkdown(unittest.TestCase):

    def test_returns_bytesio(self):
        """BytesIO 반환"""
        buf = export_markdown('제목', '내용입니다.')
        self.assertIsInstance(buf, io.BytesIO)

    def test_content_utf8(self):
        """UTF-8 인코딩"""
        buf = export_markdown('한국어 제목', '한국어 내용')
        text = buf.read().decode('utf-8')
        self.assertIn('한국어 제목', text)
        self.assertIn('한국어 내용', text)

    def test_heading_prefix(self):
        """제목에 # 접두사"""
        buf = export_markdown('Test', 'Body')
        text = buf.read().decode('utf-8')
        self.assertTrue(text.startswith('# Test'))


if __name__ == '__main__':
    unittest.main()
