"""
멀티소스 콘텐츠 수집 통합 테스트
- web_scraper_service, rss_service, arxiv_service, multi_source_collector 검증
- HTTP 요청은 모두 Mock으로 대체 (실제 네트워크 불필요)
"""
import unittest
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────────
# P4-22D: detect_source_type 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestDetectSourceType(unittest.TestCase):
    """detect_source_type() 소스 타입 자동 감지 검증"""

    def _detect(self, url):
        from services.multi_source_collector import detect_source_type
        return detect_source_type(url)

    def test_youtube_watch(self):
        self.assertEqual(self._detect('https://www.youtube.com/watch?v=abcd1234'), 'youtube')

    def test_youtube_short(self):
        self.assertEqual(self._detect('https://youtu.be/abcd1234'), 'youtube')

    def test_youtube_shorts(self):
        self.assertEqual(self._detect('https://www.youtube.com/shorts/abcd1234'), 'youtube')

    def test_arxiv_abs_url(self):
        self.assertEqual(self._detect('https://arxiv.org/abs/2303.08774'), 'arxiv')

    def test_arxiv_pdf_url(self):
        self.assertEqual(self._detect('https://arxiv.org/pdf/2303.08774'), 'arxiv')

    def test_arxiv_bare_id(self):
        self.assertEqual(self._detect('2303.08774'), 'arxiv')

    def test_rss_feed_path(self):
        self.assertEqual(self._detect('https://example.com/feed'), 'rss')

    def test_rss_xml_extension(self):
        self.assertEqual(self._detect('https://example.com/rss.xml'), 'rss')

    def test_rss_atom(self):
        self.assertEqual(self._detect('https://example.com/atom'), 'rss')

    def test_webpage_default(self):
        self.assertEqual(self._detect('https://example.com/blog/post'), 'webpage')

    def test_webpage_news(self):
        self.assertEqual(self._detect('https://news.ycombinator.com/item?id=12345'), 'webpage')


# ──────────────────────────────────────────────────────────────
# P4-22A: web_scraper_service 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestWebScraperService(unittest.TestCase):
    """scrape_webpage() 웹페이지 스크래핑 검증"""

    def _make_mock_response(self, html: str, encoding: str = 'utf-8'):
        """requests.get 반환값 Mock 생성 헬퍼"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.apparent_encoding = encoding
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch('services.web_scraper_service._is_crawl_allowed', return_value=True)
    @patch('services.web_scraper_service.requests.get')
    def test_scrape_extracts_article_content(self, mock_get, _mock_robots):
        """article 태그 본문이 올바르게 추출되는지 검증"""
        html = """
        <html>
          <head><title>테스트 페이지</title></head>
          <body>
            <nav>네비게이션</nav>
            <article>
              <h1>본문 제목</h1>
              <p>이것은 테스트 본문입니다. 충분히 긴 내용을 위해 추가합니다.</p>
            </article>
            <footer>푸터</footer>
          </body>
        </html>
        """
        mock_get.return_value = self._make_mock_response(html)

        from services.web_scraper_service import scrape_webpage
        result = scrape_webpage('https://example.com/article')

        self.assertEqual(result['source_type'], 'webpage')
        self.assertEqual(result['url'], 'https://example.com/article')
        self.assertIn('본문 제목', result['content'])
        self.assertIn('테스트 본문', result['content'])
        # 네비게이션/푸터가 제거되었는지 확인
        self.assertNotIn('네비게이션', result['content'])

    @patch('services.web_scraper_service._is_crawl_allowed', return_value=True)
    @patch('services.web_scraper_service.requests.get')
    def test_og_title_preferred_over_title_tag(self, mock_get, _mock_robots):
        """OG title이 <title> 태그보다 우선되는지 검증"""
        html = """
        <html>
          <head>
            <title>사이트명 - 기사 제목</title>
            <meta property="og:title" content="OG 제목" />
          </head>
          <body><article><p>긴 본문 내용입니다.</p></article></body>
        </html>
        """
        mock_get.return_value = self._make_mock_response(html)

        from services.web_scraper_service import scrape_webpage
        result = scrape_webpage('https://example.com')

        self.assertEqual(result['title'], 'OG 제목')

    @patch('services.web_scraper_service._is_crawl_allowed', return_value=False)
    def test_robots_txt_blocked_raises_value_error(self, _mock_robots):
        """robots.txt에서 차단된 URL은 ValueError 발생"""
        from services.web_scraper_service import scrape_webpage
        with self.assertRaises(ValueError):
            scrape_webpage('https://blocked.example.com/page')


# ──────────────────────────────────────────────────────────────
# P4-22B: rss_service 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestRssService(unittest.TestCase):
    """parse_feed() RSS 파싱 검증"""

    def _make_feedparser_entry(self, title: str, link: str, summary: str, published: str):
        """feedparser 엔트리 동작을 흉내내는 dict-like 객체 생성 헬퍼.

        feedparser의 FeedParserDict는 dict + attribute 접근을 모두 지원하므로
        실제 dict를 사용해 .get()과 attribute 접근을 모두 모킹합니다.
        """
        import feedparser as fp_module

        class _FakeEntry:
            """feedparser entry를 흉내내는 최소 구현체"""
            def __init__(self, d):
                self._d = d

            def get(self, key, default=None):
                return self._d.get(key, default)

            def __getattr__(self, key):
                return self._d.get(key, '')

        return _FakeEntry({
            'title': title,
            'link': link,
            'summary': summary,
            'published': published,
            'content': None,
        })

    def _make_mock_feed(self):
        """feedparser.parse() 반환값 Mock 생성 헬퍼"""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            self._make_feedparser_entry(
                title='RSS 첫 번째 글',
                link='https://example.com/post/1',
                summary='<p>요약 내용입니다.</p>',
                published='Mon, 01 Jan 2024 00:00:00 +0000',
            )
        ]
        return mock_feed

    @patch('services.rss_service.feedparser.parse')
    def test_parse_feed_returns_entry_list(self, mock_parse):
        """parse_feed가 엔트리 목록을 반환하는지 검증"""
        mock_parse.return_value = self._make_mock_feed()

        from services.rss_service import parse_feed
        result = parse_feed('https://example.com/feed')

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        entry = result[0]
        self.assertEqual(entry['source_type'], 'rss')
        self.assertEqual(entry['title'], 'RSS 첫 번째 글')
        self.assertIn('요약 내용', entry['content'])

    @patch('services.rss_service.feedparser.parse')
    def test_parse_feed_respects_max_items(self, mock_parse):
        """max_items 파라미터가 동작하는지 검증"""
        feed = MagicMock()
        feed.bozo = False

        # 5개 엔트리 생성
        entries = [
            self._make_feedparser_entry(f'글 {i}', f'https://example.com/{i}', f'내용 {i}', '')
            for i in range(5)
        ]
        feed.entries = entries
        mock_parse.return_value = feed

        from services.rss_service import parse_feed
        result = parse_feed('https://example.com/feed', max_items=3)

        self.assertEqual(len(result), 3)

    @patch('services.rss_service.feedparser.parse')
    def test_parse_feed_raises_on_bozo_without_entries(self, mock_parse):
        """bozo 피드이고 엔트리도 없으면 ValueError 발생"""
        feed = MagicMock()
        feed.bozo = True
        feed.bozo_exception = Exception('파싱 오류')
        feed.entries = []
        mock_parse.return_value = feed

        from services.rss_service import parse_feed
        with self.assertRaises(ValueError):
            parse_feed('https://invalid.example.com/feed')


# ──────────────────────────────────────────────────────────────
# P4-22C: arxiv_service 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestArxivService(unittest.TestCase):
    """fetch_paper(), search_papers() arXiv 논문 추출 검증"""

    _SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2303.08774v1</id>
    <title>GPT-4 Technical Report</title>
    <summary>We report the development of GPT-4, a large-scale multimodal model.</summary>
    <author><name>OpenAI</name></author>
    <published>2023-03-15T00:00:00Z</published>
    <link href="https://arxiv.org/abs/2303.08774" rel="alternate" type="text/html"/>
    <link href="https://arxiv.org/pdf/2303.08774" rel="related" title="pdf"/>
    <arxiv:primary_category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""

    @patch('services.arxiv_service.requests.get')
    def test_fetch_paper_returns_dict(self, mock_get):
        """fetch_paper가 올바른 딕셔너리를 반환하는지 검증"""
        mock_resp = MagicMock()
        mock_resp.content = self._SAMPLE_ATOM.encode('utf-8')
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from services.arxiv_service import fetch_paper
        result = fetch_paper('2303.08774')

        self.assertEqual(result['source_type'], 'arxiv')
        self.assertEqual(result['arxiv_id'], '2303.08774v1')
        self.assertIn('GPT-4', result['title'])
        self.assertIn('OpenAI', result['authors'])
        self.assertIn('GPT-4', result['content'])  # 콘텐츠에 제목 포함
        self.assertEqual(result['category'], 'cs.AI')
        self.assertEqual(result['published'], '2023-03-15')

    @patch('services.arxiv_service.requests.get')
    def test_fetch_paper_no_entry_raises_value_error(self, mock_get):
        """결과가 없으면 ValueError 발생"""
        empty_feed = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
        mock_resp = MagicMock()
        mock_resp.content = empty_feed
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from services.arxiv_service import fetch_paper
        with self.assertRaises(ValueError):
            fetch_paper('9999.99999')

    @patch('services.arxiv_service.requests.get')
    def test_search_papers_returns_list(self, mock_get):
        """search_papers가 목록을 반환하는지 검증"""
        mock_resp = MagicMock()
        mock_resp.content = self._SAMPLE_ATOM.encode('utf-8')
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from services.arxiv_service import search_papers
        result = search_papers('machine learning', max_results=5)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['source_type'], 'arxiv')


# ──────────────────────────────────────────────────────────────
# P4-22D: collect_content 통합 테스트
# ──────────────────────────────────────────────────────────────

class TestCollectContent(unittest.TestCase):
    """collect_content() 통합 수집 인터페이스 검증"""

    @patch('services.multi_source_collector._collect_webpage')
    def test_collect_webpage_delegates(self, mock_scrape):
        """웹페이지 URL이 _collect_webpage로 위임되는지 검증"""
        mock_scrape.return_value = {
            'title': '웹 제목', 'content': '웹 본문', 'url': 'https://example.com', 'source_type': 'webpage'
        }

        from services.multi_source_collector import collect_content
        result = collect_content('https://example.com/article', source_type='webpage')

        mock_scrape.assert_called_once_with('https://example.com/article')
        self.assertEqual(result['source_type'], 'webpage')

    @patch('services.multi_source_collector._collect_arxiv')
    def test_collect_arxiv_delegates(self, mock_arxiv):
        """arXiv URL이 _collect_arxiv로 위임되는지 검증"""
        mock_arxiv.return_value = {
            'title': '논문 제목', 'content': '초록', 'url': 'https://arxiv.org/abs/2303.08774',
            'authors': ['저자'], 'source_type': 'arxiv'
        }

        from services.multi_source_collector import collect_content
        result = collect_content('https://arxiv.org/abs/2303.08774', source_type='arxiv')

        mock_arxiv.assert_called_once()
        self.assertEqual(result['source_type'], 'arxiv')

    @patch('services.multi_source_collector._collect_rss')
    def test_collect_rss_delegates(self, mock_rss):
        """RSS URL이 _collect_rss로 위임되는지 검증"""
        mock_rss.return_value = {
            'title': '피드 제목', 'content': '피드 내용', 'url': 'https://example.com/post/1',
            'source_type': 'rss'
        }

        from services.multi_source_collector import collect_content
        result = collect_content('https://example.com/feed', source_type='rss')

        mock_rss.assert_called_once_with('https://example.com/feed')
        self.assertEqual(result['source_type'], 'rss')

    def test_collect_content_empty_url_raises(self):
        """빈 URL은 ValueError 발생"""
        from services.multi_source_collector import collect_content
        with self.assertRaises(ValueError):
            collect_content('')

    def test_collect_content_invalid_source_type_raises(self):
        """허용되지 않는 source_type은 ValueError 발생"""
        from services.multi_source_collector import collect_content
        with self.assertRaises(ValueError):
            collect_content('https://example.com', source_type='unknown_type')


if __name__ == '__main__':
    unittest.main()
