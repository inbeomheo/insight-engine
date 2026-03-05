"""
북마크 가져오기 서비스 단위 테스트
"""
import unittest

from services.bookmark_import_service import parse_bookmarks


# Chrome 북마크 내보내기 샘플
CHROME_BOOKMARK_HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file. -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3>즐겨찾기 바</H3>
    <DL><p>
        <DT><A HREF="https://www.google.com" ADD_DATE="1700000000">Google</A>
        <DT><A HREF="https://github.com" ADD_DATE="1700000001">GitHub</A>
        <DT><A HREF="https://arxiv.org/abs/2303.08774" ADD_DATE="1700000002">GPT-4 논문</A>
    </DL><p>
    <DT><H3>기타</H3>
    <DL><p>
        <DT><A HREF="https://youtube.com/watch?v=abc123" ADD_DATE="1700000003">좋은 영상</A>
    </DL><p>
</DL><p>
"""


class TestBookmarkImport(unittest.TestCase):
    """북마크 HTML 파싱 테스트"""

    def test_parse_chrome_bookmarks(self):
        """Chrome 북마크 파싱 성공"""
        result = parse_bookmarks(CHROME_BOOKMARK_HTML)
        self.assertEqual(len(result), 4)
        urls = [b['url'] for b in result]
        self.assertIn('https://www.google.com', urls)
        self.assertIn('https://github.com', urls)
        self.assertIn('https://arxiv.org/abs/2303.08774', urls)
        self.assertIn('https://youtube.com/watch?v=abc123', urls)

    def test_title_extraction(self):
        """제목 추출"""
        result = parse_bookmarks(CHROME_BOOKMARK_HTML)
        google = next(b for b in result if 'google.com' in b['url'])
        self.assertEqual(google['title'], 'Google')

    def test_duplicate_removal(self):
        """중복 URL 제거"""
        html = """
        <DL>
            <DT><A HREF="https://example.com">Site 1</A>
            <DT><A HREF="https://example.com">Site 1 Duplicate</A>
            <DT><A HREF="https://other.com">Other</A>
        </DL>
        """
        result = parse_bookmarks(html)
        self.assertEqual(len(result), 2)

    def test_skip_non_http(self):
        """비HTTP URL 건너뜀 (javascript:, chrome:// 등)"""
        html = """
        <DL>
            <DT><A HREF="javascript:void(0)">JS Link</A>
            <DT><A HREF="chrome://settings">Settings</A>
            <DT><A HREF="https://valid.com">Valid</A>
        </DL>
        """
        result = parse_bookmarks(html)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], 'https://valid.com')

    def test_empty_file(self):
        """빈 파일 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            parse_bookmarks('')
        self.assertIn('빈 파일', str(ctx.exception))

    def test_no_bookmarks(self):
        """링크 없는 HTML → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            parse_bookmarks('<html><body><p>No bookmarks here</p></body></html>')
        self.assertIn('북마크를 찾을 수 없습니다', str(ctx.exception))

    def test_no_valid_urls(self):
        """유효 URL 없음 → ValueError"""
        html = '<DL><DT><A HREF="javascript:void(0)">Bad</A></DL>'
        with self.assertRaises(ValueError) as ctx:
            parse_bookmarks(html)
        self.assertIn('유효한 북마크 URL', str(ctx.exception))

    def test_missing_title_uses_url(self):
        """제목이 비어있으면 URL 사용"""
        html = '<DL><DT><A HREF="https://example.com"></A></DL>'
        result = parse_bookmarks(html)
        self.assertEqual(result[0]['title'], 'https://example.com')


if __name__ == '__main__':
    unittest.main()
