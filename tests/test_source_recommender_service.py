"""source_recommender_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services import source_recommender_service


class TestSourceRecommenderService(unittest.TestCase):
    """소스 추천 서비스 테스트"""

    def test_empty_topic_raises(self):
        """빈 주제 시 ValueError"""
        with self.assertRaises(ValueError):
            source_recommender_service.recommend_sources('')

    def test_none_topic_raises(self):
        """None 주제 시 ValueError"""
        with self.assertRaises(ValueError):
            source_recommender_service.recommend_sources(None)

    @patch.object(source_recommender_service, '_search_web', return_value=[])
    @patch.object(source_recommender_service, '_search_youtube', return_value=[])
    def test_no_results(self, mock_yt, mock_web):
        """검색 결과 없을 때 빈 리스트"""
        result = source_recommender_service.recommend_sources('없는주제')
        self.assertEqual(result, [])

    @patch.object(source_recommender_service, '_search_web', return_value=[])
    @patch.object(source_recommender_service, '_search_youtube', return_value=[
        {'url': 'https://youtube.com/watch?v=abc', 'title': 'Test', 'source_type': 'youtube', 'relevance_score': 1.0},
    ])
    def test_youtube_results(self, mock_yt, mock_web):
        """YouTube 결과 포함"""
        result = source_recommender_service.recommend_sources('Python')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['source_type'], 'youtube')

    @patch.object(source_recommender_service, '_search_youtube', return_value=[])
    @patch.object(source_recommender_service, '_search_web', return_value=[
        {'url': 'https://example.com', 'title': 'Web', 'source_type': 'webpage', 'relevance_score': 0.9},
    ])
    def test_web_results(self, mock_web, mock_yt):
        """웹 결과 포함"""
        result = source_recommender_service.recommend_sources('Python')
        self.assertEqual(result[0]['source_type'], 'webpage')

    @patch.object(source_recommender_service, '_search_web', return_value=[
        {'url': 'https://web.com', 'title': 'Web', 'source_type': 'webpage', 'relevance_score': 0.5},
    ])
    @patch.object(source_recommender_service, '_search_youtube', return_value=[
        {'url': 'https://yt.com', 'title': 'YT', 'source_type': 'youtube', 'relevance_score': 1.0},
    ])
    def test_sorted_by_relevance(self, mock_yt, mock_web):
        """관련도 순 정렬"""
        result = source_recommender_service.recommend_sources('Python')
        self.assertGreaterEqual(result[0]['relevance_score'], result[-1]['relevance_score'])

    @patch('os.getenv', return_value='')
    def test_youtube_no_api_key(self, mock_env):
        """YOUTUBE_API_KEY 없으면 빈 리스트"""
        result = source_recommender_service._search_youtube('Python')
        self.assertEqual(result, [])

    def test_web_search_import_error_handled(self):
        """duckduckgo_search 미설치 시 빈 리스트 (graceful)"""
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == 'duckduckgo_search':
                raise ImportError('mocked')
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            result = source_recommender_service._search_web('Python')
            self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
