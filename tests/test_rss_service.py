"""rss_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from services.platform.rss_service import parse_feed, get_latest_entries, _clean_html, _parse_published_dt


class TestCleanHtml(unittest.TestCase):
    """_clean_html 테스트"""

    def test_strips_tags(self):
        """HTML 태그 제거"""
        self.assertEqual(_clean_html('<p>안녕</p>'), '안녕')

    def test_empty_input(self):
        """빈 입력"""
        self.assertEqual(_clean_html(''), '')

    def test_collapses_newlines(self):
        """연속 개행 축소"""
        result = _clean_html('<p>A</p>\n\n\n\n<p>B</p>')
        self.assertNotIn('\n\n\n', result)


class TestParsePublishedDt(unittest.TestCase):
    """_parse_published_dt 테스트"""

    def test_rfc2822(self):
        """RFC 2822 형식 파싱"""
        result = _parse_published_dt('Tue, 01 Jan 2026 00:00:00 +0000')
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)

    def test_empty_string(self):
        """빈 문자열"""
        self.assertIsNone(_parse_published_dt(''))

    def test_invalid_string(self):
        """파싱 불가 문자열"""
        self.assertIsNone(_parse_published_dt('not a date'))


class TestParseFeed(unittest.TestCase):
    """parse_feed 테스트"""

    @patch('services.platform.rss_service.fetch_public_url')
    @patch('services.platform.rss_service.feedparser.parse')
    def test_success(self, mock_parse, mock_fetch):
        """정상 파싱"""
        mock_fetch.return_value = MagicMock(
            content=b'<rss/>',
            headers={'Content-Type': 'application/rss+xml'},
            url='https://example.com/final-feed',
        )
        entry = MagicMock()
        entry.content = [{'value': '<p>본문</p>'}]
        entry.summary = 'summary'
        entry.published = 'Tue, 01 Jan 2026 00:00:00 +0000'
        entry.get = lambda k, d='': {'title': '제목', 'link': 'https://example.com'}.get(k, d)
        mock_parse.return_value = MagicMock(bozo=False, entries=[entry])

        result = parse_feed('https://example.com/feed')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], '제목')
        self.assertEqual(result[0]['source_type'], 'rss')

        mock_parse.assert_called_once_with(
            b'<rss/>',
            response_headers={
                'Content-Type': 'application/rss+xml',
                'Content-Location': 'https://example.com/final-feed',
            },
        )

    @patch('services.platform.rss_service.fetch_public_url')
    @patch('services.platform.rss_service.feedparser.parse')
    def test_bozo_no_entries_raises(self, mock_parse, mock_fetch):
        """bozo + 엔트리 없으면 ValueError"""
        mock_fetch.return_value = MagicMock(content=b'<bad>')
        mock_parse.return_value = MagicMock(bozo=True, entries=[], bozo_exception='bad')
        with self.assertRaises(ValueError):
            parse_feed('https://bad.com/feed')

    @patch('services.platform.rss_service.fetch_public_url')
    @patch('services.platform.rss_service.feedparser.parse')
    def test_max_items(self, mock_parse, mock_fetch):
        """max_items 제한"""
        mock_fetch.return_value = MagicMock(content=b'<rss/>')
        entries = [MagicMock(content=[], summary='s', published='', get=lambda k, d='': d) for _ in range(20)]
        for e in entries:
            e.content = []
            e.get = lambda k, d='': d
        mock_parse.return_value = MagicMock(bozo=False, entries=entries)

        result = parse_feed('https://example.com/feed', max_items=5)
        self.assertEqual(len(result), 5)


class TestGetLatestEntries(unittest.TestCase):
    """get_latest_entries 테스트"""

    @patch('services.platform.rss_service.parse_feed')
    def test_filters_old_entries(self, mock_parse):
        """오래된 엔트리 필터링"""
        now = datetime.now(timezone.utc)
        recent_dt = (now - timedelta(days=2)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        old_dt = (now - timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S +0000')

        mock_parse.return_value = [
            {'title': 'recent', 'published': recent_dt},
            {'title': 'old', 'published': old_dt},
        ]
        result = get_latest_entries('https://example.com/feed', since_days=7)
        titles = [e['title'] for e in result]
        self.assertIn('recent', titles)
        self.assertNotIn('old', titles)

    @patch('services.platform.rss_service.parse_feed')
    def test_includes_unparseable_dates(self, mock_parse):
        """날짜 파싱 불가 엔트리 포함"""
        mock_parse.return_value = [
            {'title': 'no-date', 'published': ''},
        ]
        result = get_latest_entries('https://example.com/feed')
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
