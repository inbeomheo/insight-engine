"""vector_store 단위 테스트 — VectorStore CRUD 검증"""
import unittest
from unittest.mock import patch, MagicMock


class TestVectorStore(unittest.TestCase):
    """VectorStore: ChromaDB 래퍼 CRUD"""

    @patch('services.rag.vector_store.chromadb')
    @patch('services.rag.vector_store.os.makedirs')
    def _make_store(self, mock_makedirs, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        from services.rag.vector_store import VectorStore
        store = VectorStore(db_path='/tmp/test_chroma')
        return store, mock_client

    def test_add_document(self):
        store, mock_client = self._make_store()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store.add_document('user1', 'doc1', ['chunk1', 'chunk2'], {'filename': 'test.txt'})

        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args
        self.assertEqual(len(call_kwargs[1]['ids']), 2)
        self.assertEqual(call_kwargs[1]['documents'], ['chunk1', 'chunk2'])

    def test_search_empty_collection(self):
        store, mock_client = self._make_store()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection

        result = store.search('user1', 'query')
        self.assertEqual(result, [])

    def test_search_with_results(self):
        store, mock_client = self._make_store()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            'documents': [['chunk text 1', 'chunk text 2']],
            'metadatas': [[{'doc_id': 'd1'}, {'doc_id': 'd1'}]],
            'distances': [[0.1, 0.5]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        results = store.search('user1', 'test query', top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['text'], 'chunk text 1')
        self.assertAlmostEqual(results[0]['distance'], 0.1)

    def test_delete_document(self):
        store, mock_client = self._make_store()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {'ids': ['doc1_chunk_0', 'doc1_chunk_1', 'doc2_chunk_0']}
        mock_client.get_or_create_collection.return_value = mock_collection

        store.delete_document('user1', 'doc1')
        mock_collection.delete.assert_called_once_with(ids=['doc1_chunk_0', 'doc1_chunk_1'])

    def test_list_documents(self):
        store, mock_client = self._make_store()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            'metadatas': [
                {'doc_id': 'doc1', 'filename': 'a.txt', 'uploaded_at': '2026-01-01'},
                {'doc_id': 'doc1', 'filename': 'a.txt', 'uploaded_at': '2026-01-01'},
                {'doc_id': 'doc2', 'filename': 'b.pdf', 'uploaded_at': '2026-01-02'},
            ]
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        docs = store.list_documents('user1')
        self.assertEqual(len(docs), 2)
        doc1 = next(d for d in docs if d['id'] == 'doc1')
        self.assertEqual(doc1['chunk_count'], 2)


if __name__ == '__main__':
    unittest.main()
