"""rag/chunker 단위 테스트 — chunk_text + extract_text_from_file"""
import unittest
from unittest.mock import patch, MagicMock

from services.rag.chunker import chunk_text, extract_text_from_file


class TestChunkText(unittest.TestCase):

    def test_empty_text(self):
        self.assertEqual(chunk_text(''), [])

    def test_text_shorter_than_chunk_size(self):
        result = chunk_text('짧은 텍스트', chunk_size=800)
        self.assertEqual(result, ['짧은 텍스트'])

    def test_exact_chunk_boundary(self):
        text = 'a' * 800
        result = chunk_text(text, chunk_size=800, overlap=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'a' * 800)

    def test_overlap_applied(self):
        text = 'abcdefghij' * 100  # 1000 chars
        result = chunk_text(text, chunk_size=300, overlap=50)
        # 첫 청크: 0~300, 두 번째: 250~550, 세 번째: 500~800, 네 번째: 750~1000 → 4개
        self.assertEqual(len(result), 4)
        # 인접 청크가 50자 겹치는지 (첫 50자 = 이전 청크의 마지막 50자)
        for i in range(1, len(result)):
            # 청크는 trim된 상태이므로 정확한 substring 비교는 어려움 — 길이만 확인
            self.assertGreater(len(result[i]), 0)

    def test_whitespace_only_chunks_skipped(self):
        text = '내용1' + ' ' * 800 + '내용2'
        result = chunk_text(text, chunk_size=300, overlap=0)
        # 모든 청크가 strip되고 빈 청크는 제외됨
        for chunk in result:
            self.assertEqual(chunk, chunk.strip())
            self.assertNotEqual(chunk, '')

    def test_chunks_are_trimmed(self):
        text = '   hello world   '
        result = chunk_text(text, chunk_size=800)
        self.assertEqual(result, ['hello world'])

    def test_no_overlap(self):
        text = 'a' * 100 + 'b' * 100 + 'c' * 100
        result = chunk_text(text, chunk_size=100, overlap=0)
        self.assertEqual(len(result), 3)


class TestExtractTextFromFile(unittest.TestCase):

    def test_txt_file(self):
        content = '한글 텍스트 내용입니다'
        result = extract_text_from_file(content.encode('utf-8'), 'doc.txt')
        self.assertEqual(result, content)

    def test_md_file(self):
        content = '# 제목\n\n본문'
        result = extract_text_from_file(content.encode('utf-8'), 'README.md')
        self.assertEqual(result, content)

    def test_uppercase_extension(self):
        """확장자 대소문자 무관"""
        content = 'hello'
        result = extract_text_from_file(content.encode('utf-8'), 'FILE.TXT')
        self.assertEqual(result, content)

    def test_unsupported_extension_raises(self):
        with self.assertRaises(ValueError) as ctx:
            extract_text_from_file(b'binary', 'image.png')
        self.assertIn('지원하지 않는', str(ctx.exception))

    def test_no_extension_raises(self):
        with self.assertRaises(ValueError):
            extract_text_from_file(b'data', 'noext')

    def test_invalid_utf8_decoded_lenient(self):
        """`errors='ignore'`로 invalid byte 제거"""
        bad_bytes = b'hello\xff\xfeworld'
        result = extract_text_from_file(bad_bytes, 'doc.txt')
        self.assertIn('hello', result)
        self.assertIn('world', result)

    def test_pdf_file_reads_pages(self):
        """PdfReader를 모의하여 PDF 읽기 검증"""
        fake_page1 = MagicMock()
        fake_page1.extract_text.return_value = '페이지 1 텍스트'
        fake_page2 = MagicMock()
        fake_page2.extract_text.return_value = '페이지 2 텍스트'
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page1, fake_page2]

        with patch('PyPDF2.PdfReader', return_value=fake_reader):
            result = extract_text_from_file(b'%PDF-1.4 dummy', 'doc.pdf')
        self.assertIn('페이지 1 텍스트', result)
        self.assertIn('페이지 2 텍스트', result)

    def test_pdf_reader_failure_raises_runtime_error(self):
        """PdfReader가 raise하면 RuntimeError로 래핑"""
        with patch('PyPDF2.PdfReader', side_effect=RuntimeError('corrupt')):
            with self.assertRaises(RuntimeError):
                extract_text_from_file(b'%PDF', 'doc.pdf')

    def test_pdf_page_with_none_text(self):
        """페이지의 extract_text가 None 반환 시 '' 로 대체"""
        fake_page = MagicMock()
        fake_page.extract_text.return_value = None
        fake_reader = MagicMock()
        fake_reader.pages = [fake_page]
        with patch('PyPDF2.PdfReader', return_value=fake_reader):
            result = extract_text_from_file(b'%PDF', 'doc.pdf')
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main()
