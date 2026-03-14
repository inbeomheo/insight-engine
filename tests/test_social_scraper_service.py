"""social_scraper_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

import requests

from services.platform.social_scraper_service import (
    _make_twitter_title,
    _NITTER_INSTANCES,
    _REDDIT_COMMENT_RE,
    _HN_ITEM_RE,
    _SO_QUESTION_RE,
    _HN_API_BASE,
    _SE_API_BASE,
    _REQUEST_TIMEOUT,
    scrape_twitter_thread,
    scrape_reddit_post,
    scrape_hackernews,
    scrape_stackoverflow,
)


class TestConstants(unittest.TestCase):

    def test_nitter_instances(self):
        """Nitter 인스턴스 목록"""
        self.assertGreater(len(_NITTER_INSTANCES), 0)

    def test_timeout(self):
        """요청 타임아웃"""
        self.assertEqual(_REQUEST_TIMEOUT, 15)

    def test_hn_api_base(self):
        """HN API 베이스"""
        self.assertIn('firebaseio', _HN_API_BASE)

    def test_se_api_base(self):
        """SE API 베이스"""
        self.assertIn('stackexchange', _SE_API_BASE)


class TestRegexPatterns(unittest.TestCase):

    def test_reddit_comment_re(self):
        """Reddit URL 패턴"""
        match = _REDDIT_COMMENT_RE.search('https://www.reddit.com/r/python/comments/abc123/title')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'python')
        self.assertEqual(match.group(2), 'abc123')

    def test_hn_item_re(self):
        """HN URL 패턴"""
        match = _HN_ITEM_RE.search('https://news.ycombinator.com/item?id=12345')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '12345')

    def test_so_question_re(self):
        """SO URL 패턴"""
        match = _SO_QUESTION_RE.search('https://stackoverflow.com/questions/67890/title')
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '67890')

    def test_no_match(self):
        """매칭 안 되는 URL"""
        self.assertIsNone(_REDDIT_COMMENT_RE.search('https://example.com'))
        self.assertIsNone(_HN_ITEM_RE.search('https://example.com'))
        self.assertIsNone(_SO_QUESTION_RE.search('https://example.com'))


class TestMakeTwitterTitle(unittest.TestCase):

    def test_with_handle(self):
        """핸들 포함 URL"""
        result = _make_twitter_title('https://twitter.com/testuser/status/123')
        self.assertEqual(result, '@testuser 트윗')

    def test_x_domain(self):
        """x.com 도메인"""
        result = _make_twitter_title('https://x.com/user123/status/456')
        self.assertEqual(result, '@user123 트윗')


class TestScrapeTwitterThread(unittest.TestCase):

    @patch('services.platform.social_scraper_service._extract_with_trafilatura')
    def test_nitter_success(self, mock_extract):
        """Nitter 추출 성공"""
        mock_extract.return_value = ('제목', 'A' * 50)
        result = scrape_twitter_thread('https://twitter.com/user/status/123')
        self.assertEqual(result['source_type'], 'twitter')
        self.assertIn('content', result)

    @patch('services.platform.social_scraper_service._extract_with_trafilatura', return_value=('', ''))
    def test_all_fail(self, mock_extract):
        """모든 추출 실패 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            scrape_twitter_thread('https://twitter.com/user/status/123')
        self.assertIn('본문을 추출할 수 없습니다', str(ctx.exception))


class TestScrapeRedditPost(unittest.TestCase):

    @patch('services.platform.social_scraper_service.requests.get')
    def test_success(self, mock_get):
        """Reddit 포스트 성공"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {'data': {'children': [{'data': {'title': '질문', 'selftext': '본문 내용'}}]}},
            {'data': {'children': [
                {'kind': 't1', 'data': {'body': '댓글1'}},
            ]}},
        ]
        mock_get.return_value = mock_resp

        result = scrape_reddit_post('https://reddit.com/r/python/comments/abc/title')
        self.assertEqual(result['title'], '질문')
        self.assertEqual(result['source_type'], 'reddit')
        self.assertIn('본문 내용', result['content'])

    @patch('services.platform.social_scraper_service.requests.get')
    def test_request_error(self, mock_get):
        """네트워크 오류 → ValueError"""
        mock_get.side_effect = requests.RequestException('network')
        with self.assertRaises(ValueError):
            scrape_reddit_post('https://reddit.com/r/test/comments/abc/t')

    @patch('services.platform.social_scraper_service.requests.get')
    def test_empty_content(self, mock_get):
        """빈 본문 + 빈 댓글 → ValueError"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {'data': {'children': [{'data': {'title': '제목', 'selftext': ''}}]}},
            {'data': {'children': []}},
        ]
        mock_get.return_value = mock_resp
        with self.assertRaises(ValueError):
            scrape_reddit_post('https://reddit.com/r/test/comments/abc/t')


class TestScrapeHackernews(unittest.TestCase):

    def test_invalid_url(self):
        """유효하지 않은 URL → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            scrape_hackernews('https://example.com')
        self.assertIn('유효하지 않은', str(ctx.exception))

    @patch('services.platform.social_scraper_service.requests.get')
    def test_success(self, mock_get):
        """HN 아이템 성공"""
        mock_resp_item = MagicMock()
        mock_resp_item.json.return_value = {
            'title': 'Show HN: 프로젝트',
            'text': '본문 텍스트',
            'url': 'https://project.com',
            'kids': [],
        }
        mock_get.return_value = mock_resp_item

        result = scrape_hackernews('https://news.ycombinator.com/item?id=99999')
        self.assertEqual(result['title'], 'Show HN: 프로젝트')
        self.assertEqual(result['source_type'], 'hackernews')

    @patch('services.platform.social_scraper_service.requests.get')
    def test_item_none(self, mock_get):
        """아이템 없음 → ValueError"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = None
        mock_get.return_value = mock_resp
        with self.assertRaises(ValueError):
            scrape_hackernews('https://news.ycombinator.com/item?id=99999')


class TestScrapeStackoverflow(unittest.TestCase):

    def test_invalid_url(self):
        """유효하지 않은 URL → ValueError"""
        with self.assertRaises(ValueError):
            scrape_stackoverflow('https://example.com')

    @patch('services.platform.social_scraper_service.requests.get')
    def test_success(self, mock_get):
        """SO 질문 성공"""
        mock_resp_q = MagicMock()
        mock_resp_q.json.return_value = {
            'items': [{
                'title': 'Python 질문',
                'body': '<p>어떻게 하나요?</p>',
            }]
        }
        mock_resp_a = MagicMock()
        mock_resp_a.json.return_value = {
            'items': [{
                'body': '<p>이렇게 합니다.</p>',
                'score': 10,
                'is_accepted': True,
            }]
        }
        mock_get.side_effect = [mock_resp_q, mock_resp_a]

        result = scrape_stackoverflow('https://stackoverflow.com/questions/12345/title')
        self.assertEqual(result['title'], 'Python 질문')
        self.assertEqual(result['source_type'], 'stackoverflow')
        self.assertIn('어떻게 하나요', result['content'])


if __name__ == '__main__':
    unittest.main()
