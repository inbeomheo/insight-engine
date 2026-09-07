"""document_ingest_service 단위 테스트"""
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch, MagicMock

from services.content.document_ingest_service import (
    ALLOWED_MIME_TYPES, EXTENSION_TO_MIME, MAX_FILE_SIZE,
    _extract_pdf, _extract_pdf_payload, _validate_ooxml_archive, extract_text,
)


class TestConstants(unittest.TestCase):

    def test_allowed_mime_types(self):
        """허용 MIME 타입 3종"""
        self.assertIn('application/pdf', ALLOWED_MIME_TYPES)
        self.assertIn('application/vnd.openxmlformats-officedocument.wordprocessingml.document', ALLOWED_MIME_TYPES)
        self.assertIn('application/vnd.openxmlformats-officedocument.presentationml.presentation', ALLOWED_MIME_TYPES)

    def test_extension_to_mime_pdf(self):
        """.pdf 확장자 매핑"""
        self.assertEqual(EXTENSION_TO_MIME['.pdf'], 'application/pdf')

    def test_extension_to_mime_docx(self):
        """.docx 확장자 매핑"""
        self.assertIn('.docx', EXTENSION_TO_MIME)

    def test_extension_to_mime_pptx(self):
        """.pptx 확장자 매핑"""
        self.assertIn('.pptx', EXTENSION_TO_MIME)

    def test_max_file_size(self):
        """최대 파일 크기 10MB"""
        self.assertEqual(MAX_FILE_SIZE, 10 * 1024 * 1024)


class TestExtractText(unittest.TestCase):

    def test_unsupported_mime_type(self):
        """지원하지 않는 MIME 타입 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            extract_text('/fake/path.txt', 'text/plain')
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch('services.content.document_ingest_service._extract_pdf')
    def test_dispatch_pdf(self, mock_pdf):
        """PDF MIME → _extract_pdf 호출"""
        mock_pdf.return_value = {'title': 'T', 'content': 'C', 'source_type': 'document', 'page_count': 1}
        result = extract_text('/fake/doc.pdf', 'application/pdf')
        mock_pdf.assert_called_once_with('/fake/doc.pdf')
        self.assertEqual(result['title'], 'T')

    @patch('services.content.document_ingest_service._extract_docx')
    def test_dispatch_docx(self, mock_docx):
        """DOCX MIME → _extract_docx 호출"""
        mock_docx.return_value = {'title': 'D', 'content': 'X', 'source_type': 'document', 'page_count': 5}
        result = extract_text(
            '/fake/doc.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        mock_docx.assert_called_once_with('/fake/doc.docx')
        self.assertEqual(result['title'], 'D')

    @patch('services.content.document_ingest_service._extract_pptx')
    def test_dispatch_pptx(self, mock_pptx):
        """PPTX MIME → _extract_pptx 호출"""
        mock_pptx.return_value = {'title': 'P', 'content': 'S', 'source_type': 'document', 'page_count': 10}
        result = extract_text(
            '/fake/pres.pptx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        mock_pptx.assert_called_once_with('/fake/pres.pptx')
        self.assertEqual(result['title'], 'P')


class TestOoxmlArchiveSafety(unittest.TestCase):

    def _make_archive(self, entries):
        tmp = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries:
                archive.writestr(name, content)
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        return tmp.name

    def test_rejects_extreme_compression_ratio(self):
        path = self._make_archive([('word/document.xml', b'A' * (1024 * 1024))])

        with self.assertRaisesRegex(ValueError, '압축률'):
            _validate_ooxml_archive(path)

    def test_rejects_excessive_entry_count(self):
        path = self._make_archive([
            ('word/a.xml', b'a'),
            ('word/b.xml', b'b'),
            ('word/c.xml', b'c'),
        ])

        with patch('services.content.document_ingest_service.MAX_OOXML_ENTRIES', 2):
            with self.assertRaisesRegex(ValueError, '파일 수'):
                _validate_ooxml_archive(path)

    def test_rejects_parent_directory_member(self):
        path = self._make_archive([('../outside.xml', b'x')])

        with self.assertRaisesRegex(ValueError, '경로'):
            _validate_ooxml_archive(path)


class TestPdfSafety(unittest.TestCase):

    def _empty_file(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.write(b'%PDF-test')
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        return tmp.name

    @patch('pypdf.PdfReader')
    def test_rejects_excessive_page_count_before_extraction(self, reader):
        reader.return_value.is_encrypted = False
        reader.return_value.pages = [MagicMock(), MagicMock(), MagicMock()]

        with patch('services.content.document_ingest_service.MAX_PDF_PAGES', 2):
            with self.assertRaisesRegex(ValueError, '페이지 수'):
                _extract_pdf_payload(self._empty_file())

        for page in reader.return_value.pages:
            page.extract_text.assert_not_called()

    @patch('pypdf.PdfReader')
    def test_rejects_extracted_text_growth(self, reader):
        page_one = MagicMock()
        page_one.extract_text.return_value = 'a' * 100
        page_two = MagicMock()
        page_two.extract_text.return_value = 'b' * 100
        reader.return_value.is_encrypted = False
        reader.return_value.pages = [page_one, page_two]

        with patch(
            'services.content.document_ingest_service.MAX_EXTRACTED_TEXT_CHARS',
            150,
        ):
            with self.assertRaisesRegex(ValueError, '추출 텍스트'):
                _extract_pdf_payload(self._empty_file())

    def test_untrusted_pdf_runs_in_worker_and_returns_sanitized_error(self):
        from pypdf import PdfWriter

        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(tmp.name, 'wb') as handle:
            writer.write(handle)
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))

        with self.assertRaisesRegex(ValueError, '텍스트를 추출'):
            _extract_pdf(tmp.name)


class TestExtractFromUpload(unittest.TestCase):

    @patch('services.content.document_ingest_service.extract_text')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024)
    @patch('os.close')
    @patch('os.unlink')
    @patch('tempfile.mkstemp', return_value=(5, '/tmp/test.pdf'))
    def test_valid_pdf_upload(self, mock_mkstemp, mock_unlink, mock_close, mock_size, mock_exists, mock_extract):
        """유효한 PDF 업로드 처리"""
        from services.content.document_ingest_service import extract_from_upload

        mock_extract.return_value = {
            'title': 'test',
            'content': '테스트 내용',
            'source_type': 'document',
            'page_count': 3
        }
        mock_file = MagicMock()
        mock_file.filename = '보고서.pdf'
        mock_file.content_type = 'application/pdf'
        mock_file.save = MagicMock()

        result = extract_from_upload(mock_file)
        self.assertEqual(result['title'], '보고서')

    @patch('services.content.document_ingest_service.extract_text')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024)
    @patch('os.close')
    @patch('os.unlink')
    @patch('tempfile.mkstemp', return_value=(5, '/tmp/test.docx'))
    def test_upload_prefers_extension_over_content_type(
        self,
        mock_mkstemp,
        mock_unlink,
        mock_close,
        mock_size,
        mock_exists,
        mock_extract,
    ):
        """DOCX 확장자는 클라이언트 Content-Type이 PDF여도 DOCX 파서로 보냄"""
        from services.content.document_ingest_service import extract_from_upload

        docx_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        mock_extract.return_value = {
            'title': 'test',
            'content': '테스트 내용',
            'source_type': 'document',
            'page_count': 3
        }
        mock_file = MagicMock()
        mock_file.filename = 'sample.docx'
        mock_file.content_type = 'application/pdf'
        mock_file.save = MagicMock()

        result = extract_from_upload(mock_file)

        mock_extract.assert_called_once_with('/tmp/test.docx', docx_mime)
        self.assertEqual(result['title'], 'sample')

    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=20 * 1024 * 1024)
    @patch('os.close')
    @patch('os.unlink')
    @patch('tempfile.mkstemp', return_value=(5, '/tmp/test.pdf'))
    def test_file_too_large(self, mock_mkstemp, mock_unlink, mock_close, mock_size, mock_exists):
        """파일 크기 초과 → ValueError"""
        from services.content.document_ingest_service import extract_from_upload

        mock_file = MagicMock()
        mock_file.filename = 'big.pdf'
        mock_file.content_type = 'application/pdf'
        mock_file.save = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('초과', str(ctx.exception))

    def test_unsupported_extension(self):
        """지원하지 않는 확장자 → ValueError"""
        from services.content.document_ingest_service import extract_from_upload

        mock_file = MagicMock()
        mock_file.filename = 'readme.txt'
        mock_file.content_type = 'text/plain'

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=0)
    @patch('os.close')
    @patch('os.unlink')
    @patch('tempfile.mkstemp', return_value=(5, '/tmp/test.pdf'))
    def test_empty_file(self, mock_mkstemp, mock_unlink, mock_close, mock_size, mock_exists):
        """빈 파일 → ValueError"""
        from services.content.document_ingest_service import extract_from_upload

        mock_file = MagicMock()
        mock_file.filename = 'empty.pdf'
        mock_file.content_type = 'application/pdf'
        mock_file.save = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            extract_from_upload(mock_file)
        self.assertIn('빈 파일', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
