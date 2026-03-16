"""R79: /api/arxiv/search에 sort_by 파라미터 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestArxivSortBy(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_sort_by_relevance(self, mock_search, _mock_sb):
        """sort_by=relevance가 서비스에 전달된다."""
        mock_search.return_value = {'papers': [], 'total_results': 0}
        self.client.post('/api/arxiv/search',
                         json={'query': 'test', 'sort_by': 'relevance'},
                         headers=_HEADERS)
        mock_search.assert_called_once_with('test', max_results=5, sort_by='relevance')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_sort_by_last_updated(self, mock_search, _mock_sb):
        """sort_by=lastUpdatedDate가 서비스에 전달된다."""
        mock_search.return_value = {'papers': [], 'total_results': 0}
        self.client.post('/api/arxiv/search',
                         json={'query': 'test', 'sort_by': 'lastUpdatedDate'},
                         headers=_HEADERS)
        mock_search.assert_called_once_with('test', max_results=5, sort_by='lastUpdatedDate')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_sort_by_submitted(self, mock_search, _mock_sb):
        """sort_by=submittedDate가 서비스에 전달된다."""
        mock_search.return_value = {'papers': [], 'total_results': 0}
        self.client.post('/api/arxiv/search',
                         json={'query': 'test', 'sort_by': 'submittedDate'},
                         headers=_HEADERS)
        mock_search.assert_called_once_with('test', max_results=5, sort_by='submittedDate')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_invalid_sort_by_fallback(self, mock_search, _mock_sb):
        """유효하지 않은 sort_by는 relevance로 폴백."""
        mock_search.return_value = {'papers': [], 'total_results': 0}
        self.client.post('/api/arxiv/search',
                         json={'query': 'test', 'sort_by': 'invalid_value'},
                         headers=_HEADERS)
        mock_search.assert_called_once_with('test', max_results=5, sort_by='relevance')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_default_sort_by(self, mock_search, _mock_sb):
        """sort_by 미지정 시 기본값 relevance."""
        mock_search.return_value = {'papers': [], 'total_results': 0}
        self.client.post('/api/arxiv/search',
                         json={'query': 'test'},
                         headers=_HEADERS)
        mock_search.assert_called_once_with('test', max_results=5, sort_by='relevance')


if __name__ == '__main__':
    unittest.main()
