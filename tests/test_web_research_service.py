"""웹 리서치 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestExtractKeywords(unittest.TestCase):

    @patch('services.web_research_service.ai_service')
    def test_extract_keywords(self, mock_ai):
        mock_ai.create_content.return_value = {
            'content': 'React, 상태관리, Zustand, 성능최적화',
            'usage': {'total_tokens': 50}
        }
        from services.web_research_service import extract_keywords
        keywords = extract_keywords(
            transcripts=['React 19의 새로운 기능에 대해 알아봅시다'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)


class TestSearchWeb(unittest.TestCase):

    @patch('services.web_research_service.DDGS')
    def test_search_web(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {'title': 'Article 1', 'href': 'http://ex.com/1', 'body': 'desc 1'},
            {'title': 'Article 2', 'href': 'http://ex.com/2', 'body': 'desc 2'},
        ]
        mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

        from services.web_research_service import search_web
        results = search_web(['React 상태관리'])
        self.assertIsInstance(results, list)


class TestCrawlArticle(unittest.TestCase):

    @patch('services.web_research_service.trafilatura')
    def test_crawl_article_success(self, mock_traf):
        mock_traf.fetch_url.return_value = '<html>...</html>'
        mock_traf.extract.return_value = '기사 본문 내용입니다.'
        from services.web_research_service import crawl_article
        text = crawl_article('http://example.com/article')
        self.assertEqual(text, '기사 본문 내용입니다.')

    @patch('services.web_research_service.trafilatura')
    def test_crawl_article_failure(self, mock_traf):
        mock_traf.fetch_url.return_value = None
        from services.web_research_service import crawl_article
        text = crawl_article('http://example.com/blocked')
        self.assertIsNone(text)


class TestResearchTopic(unittest.TestCase):

    @patch('services.web_research_service.crawl_article')
    @patch('services.web_research_service.search_web')
    @patch('services.web_research_service.extract_keywords')
    @patch('services.web_research_service.ai_service')
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
        from services.web_research_service import research_topic
        result = research_topic(
            transcripts=['자막 내용'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn('title', result[0])
        self.assertIn('summary', result[0])
        self.assertIn('url', result[0])

    @patch('services.web_research_service.extract_keywords')
    def test_research_topic_no_keywords(self, mock_kw):
        mock_kw.return_value = []
        from services.web_research_service import research_topic
        result = research_topic(
            transcripts=['짧은 자막'],
            model='gemini/gemini-3-flash-preview'
        )
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
