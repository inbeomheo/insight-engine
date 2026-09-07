"""웹 리서치 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.usage.usage_lock import UsageLockUnavailable
from utils.url_safety import PublicFetchTooLarge, UnsafeURLError


class TestExtractKeywords(unittest.TestCase):

    @patch('services.data.web_research_service.ai_service')
    def test_extract_keywords(self, mock_ai):
        mock_ai.create_content.return_value = {
            'content': 'React, 상태관리, Zustand, 성능최적화',
            'usage': {'total_tokens': 50}
        }
        from services.data.web_research_service import extract_keywords
        keywords = extract_keywords(
            transcripts=['React 19의 새로운 기능에 대해 알아봅시다'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)

    @patch('services.data.web_research_service.ai_service')
    def test_cost_callback_runs_immediately_before_provider(self, mock_ai):
        events = []

        def create_content(**kwargs):
            kwargs['on_cost_start']()
            events.append('provider')
            return {'content': 'keyword'}

        mock_ai.create_content.side_effect = create_content
        from services.data.web_research_service import extract_keywords

        extract_keywords(
            transcripts=['content'],
            model='model',
            on_cost_start=lambda: events.append('callback'),
        )

        self.assertEqual(events, ['callback', 'provider'])

    @patch('services.data.web_research_service.ai_service')
    def test_cost_callback_failure_is_not_downgraded(self, mock_ai):
        from services.data.web_research_service import extract_keywords

        def reject_cost():
            raise UsageLockUnavailable('lease lost')

        mock_ai.create_content.side_effect = (
            lambda **kwargs: kwargs['on_cost_start']()
        )

        with self.assertRaises(UsageLockUnavailable):
            extract_keywords(
                transcripts=['content'],
                model='model',
                on_cost_start=reject_cost,
            )

        mock_ai.create_content.assert_called_once()


class TestSearchWeb(unittest.TestCase):

    @patch('services.data.web_research_service.DDGS')
    def test_search_web(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {'title': 'Article 1', 'href': 'http://ex.com/1', 'body': 'desc 1'},
            {'title': 'Article 2', 'href': 'http://ex.com/2', 'body': 'desc 2'},
        ]
        mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

        from services.data.web_research_service import search_web
        results = search_web(['React 상태관리'])
        self.assertIsInstance(results, list)


class TestCrawlArticle(unittest.TestCase):

    @patch('services.data.web_research_service.fetch_public_url')
    @patch('services.data.web_research_service.trafilatura')
    def test_crawl_article_success(self, mock_traf, mock_safe_fetch):
        response = MagicMock()
        response.content = b'<html>safe article</html>'
        mock_safe_fetch.return_value = response
        mock_traf.fetch_url.return_value = '<html>...</html>'
        mock_traf.extract.return_value = '기사 본문 내용입니다.'
        from services.data.web_research_service import crawl_article
        text = crawl_article('http://example.com/article')
        self.assertEqual(text, '기사 본문 내용입니다.')

        mock_safe_fetch.assert_called_once_with(
            'http://example.com/article',
            headers={
                'User-Agent': 'InsightEngine/1.0 (web research)',
                'Accept': 'text/html,application/xhtml+xml',
            },
            timeout=(5, 10),
            max_bytes=1024 * 1024,
            max_redirects=3,
        )
        response.raise_for_status.assert_called_once_with()
        mock_traf.extract.assert_called_once_with(b'<html>safe article</html>')
        mock_traf.fetch_url.assert_not_called()

    @patch('services.data.web_research_service.fetch_public_url')
    @patch('services.data.web_research_service.trafilatura')
    def test_crawl_article_failure(self, mock_traf, mock_safe_fetch):
        response = MagicMock()
        response.content = b''
        mock_safe_fetch.return_value = response
        mock_traf.fetch_url.return_value = None
        from services.data.web_research_service import crawl_article
        text = crawl_article('http://example.com/blocked')
        self.assertIsNone(text)

    @patch('services.data.web_research_service.trafilatura.extract')
    @patch('services.data.web_research_service.fetch_public_url')
    def test_blocked_target_is_skipped(self, mock_safe_fetch, mock_extract):
        mock_safe_fetch.side_effect = UnsafeURLError('private target')
        from services.data.web_research_service import crawl_article

        self.assertIsNone(crawl_article('http://example.com/blocked'))
        mock_extract.assert_not_called()

    @patch('services.data.web_research_service.trafilatura.extract')
    @patch('services.data.web_research_service.fetch_public_url')
    def test_oversized_response_is_skipped(self, mock_safe_fetch, mock_extract):
        mock_safe_fetch.side_effect = PublicFetchTooLarge('too large')
        from services.data.web_research_service import crawl_article

        self.assertIsNone(crawl_article('https://example.com/large'))
        mock_extract.assert_not_called()

    def test_private_and_link_local_literals_are_blocked(self):
        from services.data.web_research_service import crawl_article

        for url in (
            'http://127.0.0.1/private',
            'http://10.0.0.1/private',
            'http://169.254.169.254/latest/meta-data/',
            'http://[::1]/private',
        ):
            with self.subTest(url=url):
                self.assertIsNone(crawl_article(url))


class TestCrawlArticles(unittest.TestCase):

    @patch('services.data.web_research_service.crawl_article')
    def test_failure_of_one_result_does_not_discard_others(self, mock_crawl):
        def crawl(url):
            if url.endswith('/blocked'):
                raise UnsafeURLError('redirect pivot')
            return 'safe article'

        mock_crawl.side_effect = crawl
        from services.data.web_research_service import _crawl_articles

        articles = _crawl_articles([
            {'title': 'Blocked', 'url': 'https://example.com/blocked'},
            {'title': 'Safe', 'url': 'https://example.com/safe'},
        ])

        self.assertEqual(articles, [{
            'title': 'Safe',
            'url': 'https://example.com/safe',
            'text': 'safe article',
        }])


class TestResearchTopic(unittest.TestCase):

    @patch('services.data.web_research_service.crawl_article')
    @patch('services.data.web_research_service.search_web')
    @patch('services.data.web_research_service.extract_keywords')
    @patch('services.data.web_research_service.ai_service')
    def test_research_topic_full_pipeline(self, mock_ai, mock_kw, mock_search, mock_crawl):
        mock_kw.return_value = ['React', '상태관리']
        mock_search.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com/1'},
        ]
        mock_crawl.return_value = '기사 본문'
        mock_ai.create_content.return_value = {
            'content': '기사 요약 내용',
            'usage': {'total_tokens': 100}
        }
        from services.data.web_research_service import research_topic
        result = research_topic(
            transcripts=['자막 내용'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn('title', result[0])
        self.assertIn('summary', result[0])
        self.assertIn('url', result[0])

    @patch('services.data.web_research_service.extract_keywords')
    def test_research_topic_no_keywords(self, mock_kw):
        mock_kw.return_value = []
        from services.data.web_research_service import research_topic
        result = research_topic(
            transcripts=['짧은 자막'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertEqual(result, [])

    @patch('services.data.web_research_service.ai_service')
    def test_each_article_rechecks_cost_boundary(self, mock_ai):
        from services.data.web_research_service import _summarize_articles

        on_cost_start = MagicMock()

        def create_content(**kwargs):
            kwargs['on_cost_start']()
            return {'content': 'summary'}

        mock_ai.create_content.side_effect = create_content
        articles = [
            {'title': f'Article {index}', 'url': f'https://ex.com/{index}', 'text': 'body'}
            for index in range(4)
        ]

        results = _summarize_articles(
            articles,
            'model',
            on_cost_start=on_cost_start,
        )

        self.assertEqual(len(results), 4)
        self.assertEqual(on_cost_start.call_count, 4)
        self.assertEqual(mock_ai.create_content.call_count, 4)

    @patch('services.data.web_research_service.ai_service')
    def test_article_cost_rejection_prevents_provider_calls(self, mock_ai):
        from services.data.web_research_service import _summarize_articles

        def reject_cost():
            raise UsageLockUnavailable('lease lost')

        mock_ai.create_content.side_effect = (
            lambda **kwargs: kwargs['on_cost_start']()
        )

        with self.assertRaises(UsageLockUnavailable):
            _summarize_articles(
                [{'title': 'Article', 'url': 'https://ex.com', 'text': 'body'}],
                'model',
                on_cost_start=reject_cost,
            )

        mock_ai.create_content.assert_called_once()


if __name__ == '__main__':
    unittest.main()
