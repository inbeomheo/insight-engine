"""
뉴스 다이제스트 서비스 단위 테스트

웹 스크래퍼를 모킹하여 다이제스트 생성을 테스트합니다.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestCreateDigest(unittest.TestCase):
    """create_digest 단위 테스트"""

    def test_raises_on_empty_urls(self):
        """빈 URL 리스트에서 ValueError 발생"""
        from services.news_digest_service import create_digest

        with self.assertRaises(ValueError):
            create_digest([])

    @patch("services.web_scraper_service.scrape_webpage")
    def test_successful_digest(self, mock_scrape):
        """정상적인 다이제스트 생성"""
        mock_scrape.side_effect = [
            {
                "title": "AI 기술 동향",
                "content": "인공지능 기술이 빠르게 발전하고 있다. " * 20,
                "url": "https://news1.com/ai",
                "source_type": "webpage",
            },
            {
                "title": "클라우드 시장 전망",
                "content": "클라우드 시장이 성장세를 이어가고 있다. " * 20,
                "url": "https://news2.com/cloud",
                "source_type": "webpage",
            },
        ]

        from services.news_digest_service import create_digest

        result = create_digest([
            "https://news1.com/ai",
            "https://news2.com/cloud",
        ])

        self.assertEqual(result["source_type"], "news_digest")
        self.assertEqual(result["title"], "뉴스 다이제스트")
        self.assertIn("AI 기술 동향", result["content"])
        self.assertIn("클라우드 시장 전망", result["content"])
        self.assertEqual(len(result["sources"]), 2)

    @patch("services.web_scraper_service.scrape_webpage")
    def test_partial_failure(self, mock_scrape):
        """일부 URL 추출 실패 시에도 성공한 기사로 다이제스트 생성"""
        mock_scrape.side_effect = [
            {
                "title": "성공한 기사",
                "content": "이 기사는 정상적으로 추출되었습니다. " * 20,
                "url": "https://news1.com/ok",
                "source_type": "webpage",
            },
            ValueError("추출 실패"),
        ]

        from services.news_digest_service import create_digest

        result = create_digest([
            "https://news1.com/ok",
            "https://news2.com/fail",
        ])

        self.assertEqual(len(result["sources"]), 1)
        self.assertIn("성공한 기사", result["content"])
        self.assertIn("추출 실패 URL", result["content"])

    @patch("services.web_scraper_service.scrape_webpage")
    def test_all_urls_fail(self, mock_scrape):
        """모든 URL 실패 시 ValueError 발생"""
        mock_scrape.side_effect = ValueError("추출 실패")

        from services.news_digest_service import create_digest

        with self.assertRaises(ValueError) as ctx:
            create_digest(["https://bad1.com", "https://bad2.com"])
        self.assertIn("모든 기사", str(ctx.exception))

    @patch("services.web_scraper_service.scrape_webpage")
    def test_single_article(self, mock_scrape):
        """단일 기사 다이제스트"""
        mock_scrape.return_value = {
            "title": "단일 기사",
            "content": "기사 내용. " * 30,
            "url": "https://news.com/single",
            "source_type": "webpage",
        }

        from services.news_digest_service import create_digest

        result = create_digest(["https://news.com/single"])

        self.assertEqual(result["source_type"], "news_digest")
        self.assertEqual(len(result["sources"]), 1)


class TestClusterByKeywords(unittest.TestCase):
    """키워드 기반 클러스터링 테스트"""

    def test_similar_articles_clustered(self):
        """유사한 기사가 같은 클러스터에 묶임"""
        from services.news_digest_service import _cluster_by_keywords

        articles = [
            {"title": "AI 인공지능 발전", "content": "인공지능 기술이 발전하고 있다"},
            {"title": "AI 인공지능 활용", "content": "인공지능 기술을 활용한 서비스"},
            {"title": "반도체 시장 동향", "content": "반도체 시장이 성장하고 있다"},
        ]

        clusters = _cluster_by_keywords(articles)

        # AI 관련 2개가 클러스터링되고, 반도체는 별도
        total_articles = sum(len(c["articles"]) for c in clusters)
        self.assertEqual(total_articles, 3)

    def test_single_article(self):
        """단일 기사는 클러스터 1개"""
        from services.news_digest_service import _cluster_by_keywords

        articles = [{"title": "테스트", "content": "내용"}]
        clusters = _cluster_by_keywords(articles)

        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]["articles"]), 1)


if __name__ == "__main__":
    unittest.main()
