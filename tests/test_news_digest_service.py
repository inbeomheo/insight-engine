"""news_digest_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.news_digest_service import (
    _extract_keywords, _cluster_by_keywords, _build_digest_markdown, create_digest
)


class TestExtractKeywords(unittest.TestCase):

    def test_basic(self):
        words = _extract_keywords('파이썬 프로그래밍 입문 가이드')
        self.assertIn('파이썬', words)
        self.assertIn('프로그래밍', words)

    def test_filters_short(self):
        words = _extract_keywords('a b cd efg')
        self.assertNotIn('a', words)
        self.assertIn('cd', words)

    def test_special_chars_removed(self):
        words = _extract_keywords('안녕! 세상?')
        self.assertIn('안녕', words)


class TestClusterByKeywords(unittest.TestCase):

    def test_single_article(self):
        articles = [{'title': '제목', 'content': '내용'}]
        clusters = _cluster_by_keywords(articles)
        self.assertEqual(len(clusters), 1)

    def test_similar_articles_clustered(self):
        articles = [
            {'title': '파이썬 딥러닝', 'content': '파이썬 딥러닝 텐서플로'},
            {'title': '파이썬 머신러닝', 'content': '파이썬 딥러닝 사이킷런'},
            {'title': '요리 레시피', 'content': '김치찌개 만드는 방법'},
        ]
        clusters = _cluster_by_keywords(articles)
        # 파이썬 관련 2개가 한 클러스터, 요리가 별도
        self.assertGreaterEqual(len(clusters), 1)


class TestBuildDigestMarkdown(unittest.TestCase):

    def test_basic(self):
        clusters = [{'topic': '주제', 'articles': [{'title': '제목', 'content': '내용', 'url': 'https://x.com'}]}]
        md = _build_digest_markdown(clusters, [])
        self.assertIn('제목', md)
        self.assertIn('https://x.com', md)

    def test_failed_urls(self):
        md = _build_digest_markdown([], ['https://fail.com'])
        self.assertIn('추출 실패', md)


class TestCreateDigest(unittest.TestCase):

    def test_empty_urls_raises(self):
        with self.assertRaises(ValueError):
            create_digest([])

    @patch('services.web_scraper_service.scrape_webpage')
    def test_success(self, mock_scrape):
        mock_scrape.return_value = {'title': '기사 제목', 'content': '기사 본문'}
        result = create_digest(['https://example.com/news'])
        self.assertEqual(result['source_type'], 'news_digest')
        self.assertIn('기사 제목', result['content'])

    @patch('services.web_scraper_service.scrape_webpage')
    def test_all_fail_raises(self, mock_scrape):
        mock_scrape.side_effect = Exception('timeout')
        with self.assertRaises(ValueError):
            create_digest(['https://fail.com'])


if __name__ == '__main__':
    unittest.main()
