"""bookmark_import_service 단위 테스트"""
import unittest

from services.data.bookmark_import_service import parse_bookmarks


class TestParseBookmarks(unittest.TestCase):
    """parse_bookmarks 함수 테스트"""

    # ── 정상 케이스 ──

    def test_basic_chrome_bookmarks(self):
        """Chrome 형식 북마크 파싱"""
        html = '''
        <DL><p>
            <DT><A HREF="https://example.com">Example</A>
            <DT><A HREF="https://google.com">Google</A>
        </DL>
        '''
        result = parse_bookmarks(html)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['url'], 'https://example.com')
        self.assertEqual(result[0]['title'], 'Example')

    def test_returns_list_of_dicts(self):
        """반환 형식이 [{'url': ..., 'title': ...}] 인지 확인"""
        html = '<DL><DT><A HREF="https://a.com">A</A></DL>'
        result = parse_bookmarks(html)
        self.assertIsInstance(result, list)
        self.assertIn('url', result[0])
        self.assertIn('title', result[0])

    def test_deduplicates_urls(self):
        """중복 URL 제거"""
        html = '''
        <DL>
            <DT><A HREF="https://dup.com">First</A>
            <DT><A HREF="https://dup.com">Second</A>
            <DT><A HREF="https://other.com">Other</A>
        </DL>
        '''
        result = parse_bookmarks(html)
        urls = [b['url'] for b in result]
        self.assertEqual(len(urls), 2)
        self.assertIn('https://dup.com', urls)

    def test_skips_non_http_urls(self):
        """비HTTP URL(javascript:, ftp: 등) 건너뛰기"""
        html = '''
        <DL>
            <DT><A HREF="javascript:void(0)">JS</A>
            <DT><A HREF="ftp://files.com">FTP</A>
            <DT><A HREF="https://valid.com">Valid</A>
        </DL>
        '''
        result = parse_bookmarks(html)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], 'https://valid.com')

    def test_empty_title_uses_url(self):
        """제목이 없으면 URL을 제목으로 사용"""
        html = '<DL><DT><A HREF="https://notitle.com"></A></DL>'
        result = parse_bookmarks(html)
        self.assertEqual(result[0]['title'], 'https://notitle.com')

    # ── 에러 케이스 ──

    def test_empty_string_raises(self):
        """빈 문자열이면 ValueError"""
        with self.assertRaises(ValueError):
            parse_bookmarks('')

    def test_none_raises(self):
        """None이면 ValueError"""
        with self.assertRaises(ValueError):
            parse_bookmarks(None)

    def test_no_links_raises(self):
        """링크가 없는 HTML이면 ValueError"""
        with self.assertRaises(ValueError):
            parse_bookmarks('<html><body>No links here</body></html>')

    def test_only_non_http_raises(self):
        """HTTP 링크가 하나도 없으면 ValueError"""
        html = '<DL><DT><A HREF="javascript:alert(1)">Bad</A></DL>'
        with self.assertRaises(ValueError):
            parse_bookmarks(html)

    def test_whitespace_only_raises(self):
        """공백만 있으면 ValueError"""
        with self.assertRaises(ValueError):
            parse_bookmarks('   \n\t  ')


if __name__ == '__main__':
    unittest.main()
