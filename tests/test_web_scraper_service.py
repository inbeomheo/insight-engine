"""web_scraper_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.data.web_scraper_service import (
    _clean_wikipedia_title,
    scrape_webpage,
    _extract_with_trafilatura,
    _extract_with_scrapling,
    _REQUEST_TIMEOUT,
    _WIKIPEDIA_RE,
)


class TestCleanWikipediaTitle(unittest.TestCase):

    def test_korean_suffix(self):
        """한국어 위키백과 접미사 제거"""
        result = _clean_wikipedia_title('파이썬 - 위키백과, 우리 모두의 백과사전')
        self.assertEqual(result, '파이썬')

    def test_english_suffix(self):
        """영어 Wikipedia 접미사 제거"""
        result = _clean_wikipedia_title('Python – Wikipedia')
        self.assertEqual(result, 'Python')

    def test_no_suffix(self):
        """접미사 없음 → 그대로"""
        result = _clean_wikipedia_title('일반 페이지 제목')
        self.assertEqual(result, '일반 페이지 제목')

    def test_empty(self):
        """빈 문자열"""
        result = _clean_wikipedia_title('')
        self.assertEqual(result, '')

    def test_japanese_suffix(self):
        """일본어 위키 접미사 제거"""
        result = _clean_wikipedia_title('Python — ウィキペディア')
        self.assertEqual(result, 'Python')


class TestWikipediaRegex(unittest.TestCase):

    def test_matches_wikipedia(self):
        """wikipedia.org URL 매칭"""
        self.assertTrue(_WIKIPEDIA_RE.search('https://en.wikipedia.org/wiki/Python'))

    def test_matches_ko_wikipedia(self):
        """한국어 위키 매칭"""
        self.assertTrue(_WIKIPEDIA_RE.search('https://ko.wikipedia.org/wiki/파이썬'))

    def test_no_match(self):
        """일반 URL 비매칭"""
        self.assertFalse(_WIKIPEDIA_RE.search('https://example.com'))


class TestConstants(unittest.TestCase):

    def test_timeout(self):
        """타임아웃 상수"""
        self.assertEqual(_REQUEST_TIMEOUT, 15)


class TestExtractWithTrafilatura(unittest.TestCase):

    @patch('services.web_scraper_service.trafilatura')
    def test_success(self, mock_traf):
        """정상 추출"""
        mock_traf.fetch_url.return_value = '<html><body>content</body></html>'
        mock_traf.extract.return_value = '본문 텍스트입니다. 충분히 긴 텍스트.'
        mock_meta = MagicMock()
        mock_meta.title = '페이지 제목'
        mock_traf.metadata.extract_metadata.return_value = mock_meta

        title, content = _extract_with_trafilatura('https://example.com')
        self.assertEqual(title, '페이지 제목')
        self.assertIn('본문', content)

    @patch('services.web_scraper_service.trafilatura')
    def test_fetch_fails(self, mock_traf):
        """fetch 실패 → 빈 결과"""
        mock_traf.fetch_url.return_value = None
        title, content = _extract_with_trafilatura('https://fail.com')
        self.assertEqual(title, '')
        self.assertEqual(content, '')

    @patch('services.web_scraper_service.trafilatura')
    def test_exception(self, mock_traf):
        """예외 → 빈 결과"""
        mock_traf.fetch_url.side_effect = Exception('network')
        title, content = _extract_with_trafilatura('https://error.com')
        self.assertEqual(title, '')
        self.assertEqual(content, '')


class TestScrapeWebpage(unittest.TestCase):

    @patch('services.web_scraper_service._extract_with_trafilatura')
    def test_trafilatura_success(self, mock_traf):
        """trafilatura 성공 → 즉시 반환"""
        mock_traf.return_value = ('제목', 'A' * 100)
        result = scrape_webpage('https://example.com')
        self.assertEqual(result['title'], '제목')
        self.assertEqual(result['source_type'], 'webpage')
        self.assertEqual(result['url'], 'https://example.com')

    @patch('services.web_scraper_service._extract_with_scrapling')
    @patch('services.web_scraper_service._extract_with_trafilatura')
    def test_scrapling_fallback(self, mock_traf, mock_scrap):
        """trafilatura 실패 → scrapling 폴백"""
        mock_traf.return_value = ('', '')
        mock_scrap.return_value = ('폴백 제목', 'B' * 100)
        result = scrape_webpage('https://spa-site.com')
        self.assertEqual(result['title'], '폴백 제목')

    @patch('services.web_scraper_service._extract_with_scrapling')
    @patch('services.web_scraper_service._extract_with_trafilatura')
    def test_both_fail(self, mock_traf, mock_scrap):
        """둘 다 실패 → ValueError"""
        mock_traf.return_value = ('', '')
        mock_scrap.return_value = ('', '')
        with self.assertRaises(ValueError) as ctx:
            scrape_webpage('https://empty.com')
        self.assertIn('본문을 추출할 수 없습니다', str(ctx.exception))

    @patch('services.web_scraper_service._extract_with_trafilatura')
    def test_wikipedia_title_cleaned(self, mock_traf):
        """위키피디아 URL → 제목 정리"""
        mock_traf.return_value = ('파이썬 - 위키백과, 우리 모두의 백과사전', 'C' * 100)
        result = scrape_webpage('https://ko.wikipedia.org/wiki/파이썬')
        self.assertEqual(result['title'], '파이썬')

    @patch('services.web_scraper_service._extract_with_trafilatura')
    def test_no_title_uses_url(self, mock_traf):
        """제목 없음 → URL 사용"""
        mock_traf.return_value = ('', 'D' * 100)
        result = scrape_webpage('https://notitle.com')
        self.assertEqual(result['title'], 'https://notitle.com')


if __name__ == '__main__':
    unittest.main()
