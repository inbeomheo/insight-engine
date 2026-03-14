"""competitor_analysis_service 단위 테스트"""
import unittest
from unittest.mock import patch


class TestAnalyzeCompetitors(unittest.TestCase):

    def test_empty_keyword_raises(self):
        from services.seo.competitor_analysis_service import analyze_competitors
        with self.assertRaises(ValueError):
            analyze_competitors("")

    def test_whitespace_keyword_raises(self):
        from services.seo.competitor_analysis_service import analyze_competitors
        with self.assertRaises(ValueError):
            analyze_competitors("   ")

    @patch('services.seo.competitor_analysis_service._search_urls', return_value=[])
    def test_no_results(self, mock_search):
        from services.seo.competitor_analysis_service import analyze_competitors
        result = analyze_competitors("매우 희귀한 키워드 xyz123")
        self.assertEqual(result["competitor_count"], 0)
        self.assertEqual(result["keyword"], "매우 희귀한 키워드 xyz123")
        self.assertIn("differentiation_tips", result)

    @patch('services.data.web_scraper_service.scrape_webpage')
    @patch('services.seo.competitor_analysis_service._search_urls')
    def test_with_competitors(self, mock_search, mock_scrape):
        mock_search.return_value = [
            {"url": "https://example.com/1", "title": "제목1"},
            {"url": "https://example.com/2", "title": "제목2"},
        ]
        mock_scrape.side_effect = [
            {"title": "제목1", "content": "# 소제목\n\n" + "Python 프로그래밍 " * 50},
            {"title": "제목2", "content": "# 개요\n\n" + "JavaScript 개발 " * 40},
        ]
        from services.seo.competitor_analysis_service import analyze_competitors
        result = analyze_competitors("프로그래밍")
        self.assertEqual(result["competitor_count"], 2)
        self.assertGreater(result["avg_stats"]["avg_char_count"], 0)

    @patch('services.data.web_scraper_service.scrape_webpage')
    @patch('services.seo.competitor_analysis_service._search_urls')
    def test_with_my_content(self, mock_search, mock_scrape):
        mock_search.return_value = [
            {"url": "https://example.com/1", "title": "경쟁글"},
        ]
        mock_scrape.return_value = {
            "title": "경쟁글",
            "content": "# 소제목\n\n" + "키워드 반복 " * 30,
        }
        from services.seo.competitor_analysis_service import analyze_competitors
        result = analyze_competitors("키워드", my_content="내 짧은 콘텐츠")
        self.assertIsNotNone(result["my_analysis"])
        self.assertIn("structure", result["my_analysis"])

    @patch('services.data.web_scraper_service.scrape_webpage')
    @patch('services.seo.competitor_analysis_service._search_urls')
    def test_scrape_failure_graceful(self, mock_search, mock_scrape):
        mock_search.return_value = [{"url": "https://fail.com", "title": "실패"}]
        mock_scrape.side_effect = Exception("스크래핑 실패")
        from services.seo.competitor_analysis_service import analyze_competitors
        result = analyze_competitors("테스트")
        self.assertEqual(result["competitor_count"], 0)


if __name__ == '__main__':
    unittest.main()
