"""GraphRAG 엔진 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestGraphRAGRoutes(unittest.TestCase):
    """GraphRAG API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ingest_missing_text_returns_400(self, _mock_sb):
        """text 누락 시 400."""
        resp = self.client.post('/api/rag/graph/ingest',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.rag.graph_rag_engine.GraphRAGEngine.ingest')
    def test_ingest_rejects_non_string_without_engine(self, mock_ingest, _mock_sb):
        resp = self.client.post(
            '/api/rag/graph/ingest',
            json={'text': ['not', 'text']},
            headers=_HEADERS,
        )

        self.assertEqual(resp.status_code, 400)
        mock_ingest.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.rag.graph_rag_engine.GraphRAGEngine.ingest')
    def test_ingest_success(self, mock_ingest, _mock_sb):
        """인제스트 성공."""
        mock_ingest.return_value = {'entities_added': 3, 'relations_added': 2}
        resp = self.client.post('/api/rag/graph/ingest',
                                json={'text': 'Python은 프로그래밍 언어입니다.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['entities_added'], 3)


if __name__ == '__main__':
    unittest.main()
