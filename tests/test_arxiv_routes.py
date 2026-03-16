"""arXiv 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

# CSRF 우회용 헤더
_HEADERS = {'Origin': 'http://localhost:3000'}


class TestArxivRoutes(unittest.TestCase):
    """arXiv 검색/조회 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_search_returns_papers(self, mock_search, _mock_sb):
        """검색어로 논문 목록 반환."""
        mock_search.return_value = {
            'papers': [
                {'title': 'Attention Is All You Need', 'arxiv_id': '1706.03762'}
            ],
            'total_results': 12345,
        }
        resp = self.client.post('/api/arxiv/search',
                                json={'query': 'transformer', 'max_results': 3},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['papers']), 1)
        self.assertEqual(data['total_results'], 12345)
        mock_search.assert_called_once_with('transformer', max_results=3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.search_papers')
    def test_search_total_results_field(self, mock_search, _mock_sb):
        """total_results 필드가 응답에 포함됨."""
        mock_search.return_value = {
            'papers': [],
            'total_results': 0,
        }
        resp = self.client.post('/api/arxiv/search',
                                json={'query': 'nonexistent'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_results', data)
        self.assertEqual(data['total_results'], 0)
        self.assertEqual(data['count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_search_empty_query_returns_400(self, _mock_sb):
        """빈 검색어는 400 에러."""
        resp = self.client.post('/api/arxiv/search', json={'query': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.fetch_paper')
    def test_paper_returns_metadata(self, mock_fetch, _mock_sb):
        """논문 ID로 메타데이터 반환."""
        mock_fetch.return_value = {
            'title': 'GPT-4 Technical Report',
            'arxiv_id': '2303.08774',
            'abstract': 'We report the development...',
        }
        resp = self.client.post('/api/arxiv/paper',
                                json={'arxiv_id': '2303.08774'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['arxiv_id'], '2303.08774')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service.fetch_paper', side_effect=ValueError('논문을 찾을 수 없습니다'))
    def test_paper_not_found_returns_404(self, mock_fetch, _mock_sb):
        """존재하지 않는 논문은 404."""
        resp = self.client.post('/api/arxiv/paper',
                                json={'arxiv_id': '0000.00000'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_paper_empty_id_returns_400(self, _mock_sb):
        """빈 ID는 400 에러."""
        resp = self.client.post('/api/arxiv/paper', json={'arxiv_id': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
