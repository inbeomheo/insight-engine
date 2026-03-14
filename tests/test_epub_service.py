"""EPUB 서비스 단위 테스트"""
import zipfile
import io
import unittest

from services.export.epub_service import create_epub


class TestEpubService(unittest.TestCase):
    """EPUB 생성 기능 테스트"""

    def test_create_epub_returns_bytes(self):
        """EPUB 생성 시 bytes 반환"""
        result = create_epub('테스트 제목', '# 헤딩\n\n본문 내용')
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_epub_is_valid_zip(self):
        """EPUB 파일이 유효한 ZIP 구조"""
        result = create_epub('제목', '내용')
        buf = io.BytesIO(result)
        self.assertTrue(zipfile.is_zipfile(buf))

    def test_epub_contains_required_files(self):
        """EPUB에 필수 파일 포함"""
        result = create_epub('제목', '내용')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            self.assertIn('mimetype', names)
            self.assertIn('META-INF/container.xml', names)
            self.assertIn('OEBPS/content.opf', names)
            self.assertIn('OEBPS/toc.ncx', names)
            self.assertIn('OEBPS/chapter.xhtml', names)
            self.assertIn('OEBPS/style.css', names)

    def test_epub_mimetype_first_entry(self):
        """mimetype이 ZIP의 첫 번째 엔트리"""
        result = create_epub('제목', '내용')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            self.assertEqual(zf.namelist()[0], 'mimetype')

    def test_epub_mimetype_uncompressed(self):
        """mimetype 파일이 압축 없이 저장됨"""
        result = create_epub('제목', '내용')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            info = zf.getinfo('mimetype')
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_epub_title_in_content(self):
        """제목이 XHTML에 포함"""
        result = create_epub('나의 책', '본문')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            xhtml = zf.read('OEBPS/chapter.xhtml').decode('utf-8')
            self.assertIn('나의 책', xhtml)

    def test_epub_markdown_converted(self):
        """마크다운이 HTML로 변환"""
        result = create_epub('제목', '**볼드** 텍스트')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            xhtml = zf.read('OEBPS/chapter.xhtml').decode('utf-8')
            self.assertIn('<strong>볼드</strong>', xhtml)

    def test_epub_author_included(self):
        """저자 정보가 OPF에 포함"""
        result = create_epub('제목', '내용', author='홍길동')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            opf = zf.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('홍길동', opf)

    def test_epub_no_author(self):
        """저자 없이도 생성 가능"""
        result = create_epub('제목', '내용')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            opf = zf.read('OEBPS/content.opf').decode('utf-8')
            self.assertNotIn('<dc:creator>', opf)

    def test_epub_xml_escaping(self):
        """특수문자가 XML 이스케이프 처리"""
        result = create_epub('제목 <&> "인용"', '내용')
        buf = io.BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            opf = zf.read('OEBPS/content.opf').decode('utf-8')
            self.assertIn('&lt;', opf)
            self.assertIn('&amp;', opf)


if __name__ == '__main__':
    unittest.main()
