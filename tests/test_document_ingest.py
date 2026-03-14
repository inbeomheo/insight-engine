"""
문서 텍스트 추출 서비스 테스트
"""
import os
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock, mock_open

from services.content.document_ingest_service import (
    extract_text,
    extract_from_upload,
    _extract_pdf,
    _extract_docx,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
)


class TestExtractText(unittest.TestCase):
    """extract_text() 디스패치 테스트"""

    def test_unsupported_mime_type(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text('/tmp/test.txt', 'text/plain')
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch('services.document_ingest_service._extract_pdf')
    def test_pdf_dispatches(self, mock_pdf):
        mock_pdf.return_value = {'title': 't', 'content': 'c', 'source_type': 'document', 'page_count': 1}
        result = extract_text('/tmp/test.pdf', 'application/pdf')
        mock_pdf.assert_called_once_with('/tmp/test.pdf')
        self.assertEqual(result['source_type'], 'document')

    @patch('services.document_ingest_service._extract_docx')
    def test_docx_dispatches(self, mock_docx):
        mock_docx.return_value = {'title': 't', 'content': 'c', 'source_type': 'document', 'page_count': 5}
        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        result = extract_text('/tmp/test.docx', mime)
        mock_docx.assert_called_once_with('/tmp/test.docx')


class TestExtractPdf(unittest.TestCase):
    """PDF 추출 테스트 — builtins.open + PyPDF2.PdfReader 모킹"""

    @patch('PyPDF2.PdfReader')
    @patch('builtins.open', mock_open(read_data=b'%PDF'))
    def test_encrypted_pdf_raises(self, mock_reader_cls):
        mock_reader = MagicMock()
        mock_reader.is_encrypted = True
        mock_reader_cls.return_value = mock_reader

        with self.assertRaises(ValueError) as ctx:
            _extract_pdf('/tmp/enc.pdf')
        self.assertIn('암호화', str(ctx.exception))

    @patch('PyPDF2.PdfReader')
    @patch('builtins.open', mock_open(read_data=b'%PDF'))
    def test_empty_pdf_raises(self, mock_reader_cls):
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.pages = []
        mock_reader_cls.return_value = mock_reader

        with self.assertRaises(ValueError) as ctx:
            _extract_pdf('/tmp/empty.pdf')
        self.assertIn('빈 PDF', str(ctx.exception))

    @patch('PyPDF2.PdfReader')
    @patch('builtins.open', mock_open(read_data=b'%PDF'))
    def test_no_text_raises(self, mock_reader_cls):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ''
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.pages = [mock_page]
        mock_reader.metadata = None
        mock_reader_cls.return_value = mock_reader

        with self.assertRaises(ValueError) as ctx:
            _extract_pdf('/tmp/image.pdf')
        self.assertIn('텍스트를 추출할 수 없습니다', str(ctx.exception))

    @patch('PyPDF2.PdfReader')
    @patch('builtins.open', mock_open(read_data=b'%PDF'))
    def test_successful_extraction(self, mock_reader_cls):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = '첫 번째 페이지 내용'
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = '두 번째 페이지 내용'

        mock_metadata = MagicMock()
        mock_metadata.title = '테스트 문서'

        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader.metadata = mock_metadata
        mock_reader_cls.return_value = mock_reader

        result = _extract_pdf('/tmp/test.pdf')
        self.assertEqual(result['title'], '테스트 문서')
        self.assertIn('첫 번째 페이지', result['content'])
        self.assertIn('두 번째 페이지', result['content'])
        self.assertEqual(result['page_count'], 2)
        self.assertEqual(result['source_type'], 'document')


class TestExtractDocx(unittest.TestCase):
    """DOCX 추출 테스트"""

    @patch('docx.Document')
    def test_successful_extraction(self, mock_doc_cls):
        mock_para1 = MagicMock()
        mock_para1.text = '문단 1 내용'
        mock_para2 = MagicMock()
        mock_para2.text = '문단 2 내용'

        mock_cell = MagicMock()
        mock_cell.text = '셀 데이터'
        mock_row = MagicMock()
        mock_row.cells = [mock_cell]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = [mock_table]
        mock_doc.core_properties.title = 'DOCX 제목'
        mock_doc_cls.return_value = mock_doc

        result = _extract_docx('/tmp/test.docx')
        self.assertEqual(result['title'], 'DOCX 제목')
        self.assertIn('문단 1', result['content'])
        self.assertIn('셀 데이터', result['content'])

    @patch('docx.Document')
    def test_empty_docx_raises(self, mock_doc_cls):
        mock_para = MagicMock()
        mock_para.text = ''
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = []
        mock_doc_cls.return_value = mock_doc

        with self.assertRaises(ValueError) as ctx:
            _extract_docx('/tmp/empty.docx')
        self.assertIn('텍스트를 추출할 수 없습니다', str(ctx.exception))


class TestExtractFromUpload(unittest.TestCase):
    """extract_from_upload() 테스트"""

    def test_unsupported_extension(self):
        mock_file = MagicMock()
        mock_file.filename = 'test.txt'
        mock_file.content_type = 'text/plain'

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('PDF', str(ctx.exception))

    @patch('services.document_ingest_service.extract_text')
    def test_empty_file_raises(self, mock_extract):
        mock_file = MagicMock()
        mock_file.filename = 'test.pdf'
        mock_file.content_type = 'application/pdf'
        mock_file.save.side_effect = lambda path: open(path, 'wb').close()

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('빈 파일', str(ctx.exception))

    @patch('services.document_ingest_service.extract_text')
    def test_oversized_file_raises(self, mock_extract):
        mock_file = MagicMock()
        mock_file.filename = 'big.pdf'
        mock_file.content_type = 'application/pdf'

        def save_big(path):
            with open(path, 'wb') as f:
                f.write(b'x' * (MAX_FILE_SIZE + 1))

        mock_file.save.side_effect = save_big

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('초과', str(ctx.exception))

    @patch('services.document_ingest_service.extract_text')
    def test_successful_upload(self, mock_extract):
        def fake_extract(path, mime):
            return {
                'title': os.path.splitext(os.path.basename(path))[0],
                'content': '본문 내용',
                'source_type': 'document',
                'page_count': 3,
            }

        mock_extract.side_effect = fake_extract
        mock_file = MagicMock()
        mock_file.filename = '보고서.pdf'
        mock_file.content_type = 'application/pdf'

        def save_content(path):
            with open(path, 'wb') as f:
                f.write(b'dummy pdf content here')

        mock_file.save.side_effect = save_content

        result = extract_from_upload(mock_file)
        mock_extract.assert_called_once()
        self.assertEqual(result['title'], '보고서')
        self.assertEqual(result['content'], '본문 내용')


if __name__ == '__main__':
    unittest.main()
