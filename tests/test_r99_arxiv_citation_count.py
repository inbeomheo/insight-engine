"""R99: /api/arxiv/paper 응답에 citation_count 필드 포함 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestArxivCitationCount(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service._fetch_citation_count', return_value=1234)
    @patch('services.data.arxiv_service.fetch_paper')
    def test_citation_count_in_response(self, mock_fetch, mock_cite, _mock_sb):
        """citation_count 필드가 응답에 포함된다."""
        mock_fetch.return_value = {
            'title': 'Test Paper',
            'abstract': 'Abstract',
            'authors': ['Author'],
            'url': 'https://arxiv.org/abs/2303.08774',
            'pdf_url': '',
            'arxiv_id': '2303.08774',
            'published': '2023-03-15',
            'category': 'cs.AI',
            'source_type': 'arxiv',
            'citation_count': 1234,
        }
        resp = self.client.post('/api/arxiv/paper',
                                json={'arxiv_id': '2303.08774'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('citation_count', data)
        self.assertEqual(data['citation_count'], 1234)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.arxiv_service._fetch_citation_count', return_value=None)
    @patch('services.data.arxiv_service.fetch_paper')
    def test_citation_count_null_when_unavailable(self, mock_fetch, mock_cite, _mock_sb):
        """Semantic Scholar 조회 실패 시 citation_count는 null."""
        mock_fetch.return_value = {
            'title': 'Test Paper',
            'abstract': 'Abstract',
            'authors': ['Author'],
            'url': 'https://arxiv.org/abs/9999.99999',
            'pdf_url': '',
            'arxiv_id': '9999.99999',
            'published': '2023-01-01',
            'category': 'cs.AI',
            'source_type': 'arxiv',
            'citation_count': None,
        }
        resp = self.client.post('/api/arxiv/paper',
                                json={'arxiv_id': '9999.99999'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('citation_count', data)
        self.assertIsNone(data['citation_count'])

    def test_fetch_citation_count_success(self):
        """_fetch_citation_count가 정상 응답 시 citationCount 반환."""
        from services.data.arxiv_service import _fetch_citation_count
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'citationCount': 567}
        with patch('services.data.arxiv_service.requests.get', return_value=mock_resp):
            result = _fetch_citation_count('2303.08774')
        self.assertEqual(result, 567)

    def test_fetch_citation_count_failure(self):
        """_fetch_citation_count가 실패 시 None 반환."""
        from services.data.arxiv_service import _fetch_citation_count
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch('services.data.arxiv_service.requests.get', return_value=mock_resp):
            result = _fetch_citation_count('nonexistent')
        self.assertIsNone(result)

    def test_fetch_citation_count_empty_id(self):
        """빈 arxiv_id는 None 반환."""
        from services.data.arxiv_service import _fetch_citation_count
        self.assertIsNone(_fetch_citation_count(''))


if __name__ == '__main__':
    unittest.main()
