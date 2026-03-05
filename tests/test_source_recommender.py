"""
소스 추천 서비스 단위 테스트

YouTube API와 DuckDuckGo 검색을 모킹하여 소스 추천을 테스트합니다.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestRecommendSources(unittest.TestCase):
    """recommend_sources 단위 테스트"""

    def test_raises_on_empty_topic(self):
        """빈 주제에서 ValueError 발생"""
        from services.source_recommender_service import recommend_sources

        with self.assertRaises(ValueError):
            recommend_sources("")

        with self.assertRaises(ValueError):
            recommend_sources("   ")

    @patch("services.source_recommender_service._search_web")
    @patch("services.source_recommender_service._search_youtube")
    def test_combines_youtube_and_web(self, mock_yt, mock_web):
        """YouTube + 웹 검색 결과 통합"""
        mock_yt.return_value = [
            {"url": "https://youtube.com/watch?v=abc", "title": "YT 영상",
             "source_type": "youtube", "relevance_score": 1.0},
        ]
        mock_web.return_value = [
            {"url": "https://example.com/article", "title": "웹 기사",
             "source_type": "webpage", "relevance_score": 0.9},
        ]

        from services.source_recommender_service import recommend_sources

        results = recommend_sources("파이썬 웹 개발")

        self.assertEqual(len(results), 2)
        # 관련도 순 정렬
        self.assertEqual(results[0]["relevance_score"], 1.0)
        self.assertEqual(results[1]["relevance_score"], 0.9)

    @patch("services.source_recommender_service._search_web")
    @patch("services.source_recommender_service._search_youtube")
    def test_graceful_when_youtube_fails(self, mock_yt, mock_web):
        """YouTube 검색 실패 시에도 웹 결과 반환"""
        mock_yt.return_value = []
        mock_web.return_value = [
            {"url": "https://example.com/1", "title": "결과 1",
             "source_type": "webpage", "relevance_score": 0.9},
        ]

        from services.source_recommender_service import recommend_sources

        results = recommend_sources("테스트 주제")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_type"], "webpage")


class TestSearchYoutube(unittest.TestCase):
    """_search_youtube 단위 테스트"""

    @patch.dict("os.environ", {"YOUTUBE_API_KEY": ""})
    def test_returns_empty_without_api_key(self):
        """API 키 없으면 빈 리스트 반환"""
        from services.source_recommender_service import _search_youtube

        results = _search_youtube("테스트")
        self.assertEqual(results, [])

    @patch("services.source_recommender_service.os.getenv", return_value="fake-key")
    @patch("googleapiclient.discovery.build")
    def test_returns_youtube_results(self, mock_build, mock_getenv):
        """YouTube 검색 결과 반환"""
        # googleapiclient.discovery.build 모킹
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        mock_search = MagicMock()
        mock_youtube.search.return_value = mock_search
        mock_list = MagicMock()
        mock_search.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {"title": "테스트 영상"},
                },
            ]
        }

        from services.source_recommender_service import _search_youtube

        results = _search_youtube("파이썬")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_type"], "youtube")
        self.assertIn("abc123", results[0]["url"])
        self.assertEqual(results[0]["relevance_score"], 1.0)


class TestSearchWeb(unittest.TestCase):
    """_search_web 단위 테스트"""

    @patch("duckduckgo_search.DDGS")
    def test_returns_web_results(self, mock_ddgs_cls):
        """웹 검색 결과 반환"""
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"href": "https://example.com/1", "title": "결과 1"},
            {"href": "https://example.com/2", "title": "결과 2"},
        ]
        mock_ddgs_cls.return_value = mock_ddgs

        from services.source_recommender_service import _search_web

        results = _search_web("파이썬 웹 개발")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["source_type"], "webpage")
        self.assertGreater(results[0]["relevance_score"], results[1]["relevance_score"])

    @patch("duckduckgo_search.DDGS")
    def test_returns_empty_on_error(self, mock_ddgs_cls):
        """검색 오류 시 빈 리스트 반환"""
        mock_ddgs_cls.side_effect = Exception("Search failed")

        from services.source_recommender_service import _search_web

        results = _search_web("테스트")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
