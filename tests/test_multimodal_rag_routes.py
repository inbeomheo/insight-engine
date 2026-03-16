"""멀티모달 RAG 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestMultimodalRAGRoutes(unittest.TestCase):
    """멀티모달 RAG API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.rag.multimodal_rag.MultimodalRAG._init_vector_store')
    def test_detect_type_image(self, _mock_vs, _mock_sb):
        """이미지 확장자 감지."""
        resp = self.client.post('/api/rag/multimodal/detect-type',
                                json={'file_path': '/tmp/photo.jpg'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['file_type'], 'image')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.rag.multimodal_rag.MultimodalRAG._init_vector_store')
    def test_detect_type_pdf(self, _mock_vs, _mock_sb):
        """PDF 확장자 감지."""
        resp = self.client.post('/api/rag/multimodal/detect-type',
                                json={'file_path': '/tmp/doc.pdf'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['file_type'], 'pdf')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_detect_type_missing_path_returns_400(self, _mock_sb):
        """file_path 누락 시 400."""
        resp = self.client.post('/api/rag/multimodal/detect-type',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_query_missing_query_returns_400(self, _mock_sb):
        """query 누락 시 400."""
        resp = self.client.post('/api/rag/multimodal/query',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ingest_missing_file_path_returns_400(self, _mock_sb):
        """file_path 누락 시 400."""
        resp = self.client.post('/api/rag/multimodal/ingest',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
