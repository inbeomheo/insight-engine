"""export_service 단위 테스트"""
import io
import unittest

from services.export_service import (
    markdown_to_docx, export_markdown, export_txt, export_zip,
    _add_formatted_text, DEFAULT_FONT,
)


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


class TestExportTxt(unittest.TestCase):

    def test_returns_bytesio(self):
        """BytesIO 반환"""
        buf = export_txt('제목', '**굵은** 텍스트')
        self.assertIsInstance(buf, io.BytesIO)

    def test_strips_markdown(self):
        """마크다운 서식 제거"""
        buf = export_txt('제목', '**굵은** 텍스트')
        text = buf.read().decode('utf-8')
        self.assertNotIn('**', text)
        self.assertIn('굵은', text)

    def test_strips_links(self):
        """링크 서식 제거"""
        buf = export_txt('제목', '[링크](https://example.com)')
        text = buf.read().decode('utf-8')
        self.assertNotIn('](', text)
        self.assertIn('링크', text)


class TestMarkdownToDocx(unittest.TestCase):

    def test_returns_bytesio(self):
        """BytesIO 반환"""
        buf = markdown_to_docx('제목', '내용')
        self.assertIsInstance(buf, io.BytesIO)

    def test_valid_docx(self):
        """유효한 DOCX (ZIP 헤더)"""
        buf = markdown_to_docx('제목', '내용입니다.')
        data = buf.read()
        # DOCX는 ZIP 형식 (PK 헤더)
        self.assertTrue(data[:2] == b'PK')

    def test_heading_conversion(self):
        """마크다운 헤딩 변환"""
        content = '## 소제목\n\n내용입니다.'
        buf = markdown_to_docx('메인 제목', content)
        self.assertGreater(buf.getbuffer().nbytes, 0)

    def test_list_conversion(self):
        """리스트 아이템 변환"""
        content = '- 항목1\n- 항목2\n\n1. 순서1\n2. 순서2'
        buf = markdown_to_docx('제목', content)
        self.assertGreater(buf.getbuffer().nbytes, 0)

    def test_blockquote(self):
        """인용문 변환"""
        content = '> 인용문입니다.'
        buf = markdown_to_docx('제목', content)
        self.assertGreater(buf.getbuffer().nbytes, 0)


class TestExportZip(unittest.TestCase):

    def test_returns_bytesio(self):
        """BytesIO 반환"""
        buf = export_zip('제목', '내용')
        self.assertIsInstance(buf, io.BytesIO)

    def test_valid_zip(self):
        """유효한 ZIP 파일"""
        import zipfile
        buf = export_zip('제목', '내용입니다.')
        self.assertTrue(zipfile.is_zipfile(buf))

    def test_contains_all_formats(self):
        """ZIP 내 md, txt, docx, meta.json 포함"""
        import zipfile
        buf = export_zip('제목', '내용')
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.endswith('.md') for n in names))
            self.assertTrue(any(n.endswith('.txt') for n in names))
            self.assertTrue(any(n.endswith('.docx') for n in names))
            self.assertIn('meta.json', names)


if __name__ == '__main__':
    unittest.main()
