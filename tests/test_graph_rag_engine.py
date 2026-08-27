"""
GraphRAGEngine 단위 테스트
"""
import tempfile
import unittest
from unittest.mock import patch

from services.rag.graph_store import GraphStore
from services.rag.graph_rag_engine import GraphRAGEngine


class TestGraphRAGEngine(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = GraphStore(store_path=self.tmpdir)
        self.engine = GraphRAGEngine(store=self.store, model="test-model")

    @patch('services.rag.graph_rag_engine.extract_graph')
    def test_ingest(self, mock_extract):
        mock_extract.return_value = {
            "entities": [
                {"name": "Python", "type": "technology", "description": "언어"},
                {"name": "Flask", "type": "technology", "description": "프레임워크"},
            ],
            "relations": [
                {"source": "Python", "target": "Flask", "relation": "사용", "weight": 0.9},
            ],
        }
        result = self.engine.ingest("user1", "Python과 Flask를 사용한 웹 개발")
        self.assertEqual(result["entities_added"], 2)
        self.assertEqual(result["relations_added"], 1)
        stats = self.store.get_stats("user1")
        self.assertEqual(stats["node_count"], 2)
        self.assertEqual(stats["edge_count"], 1)

    @patch('services.rag.graph_rag_engine.extract_graph')
    def test_ingest_empty_result(self, mock_extract):
        mock_extract.return_value = {"entities": [], "relations": []}
        result = self.engine.ingest("user1", "빈 텍스트")
        self.assertEqual(result["entities_added"], 0)
        self.assertEqual(result["relations_added"], 0)

    @patch('services.rag.graph_rag_engine.extract_graph')
    def test_ingest_uses_custom_model(self, mock_extract):
        mock_extract.return_value = {"entities": [], "relations": []}
        self.engine.ingest("user1", "text")
        mock_extract.assert_called_once_with("text", model="test-model")

    @patch('services.rag.graph_rag_engine.extract_graph')
    def test_ingest_forwards_cost_callback(self, mock_extract):
        mock_extract.return_value = {"entities": [], "relations": []}
        callback = unittest.mock.MagicMock()

        self.engine.ingest("user1", "text", on_cost_start=callback)

        mock_extract.assert_called_once_with(
            "text",
            model="test-model",
            on_cost_start=callback,
        )

    def test_local_search(self):
        self.store.add_entities("user1", [
            {"name": "A", "type": "concept", "description": ""},
            {"name": "B", "type": "concept", "description": ""},
        ])
        self.store.add_relations("user1", [
            {"source": "A", "target": "B", "relation": "관련"},
        ])
        results = self.engine.local_search("user1", ["A"])
        names = [r["name"] for r in results]
        self.assertIn("A", names)
        self.assertIn("B", names)

    def test_local_search_empty_graph(self):
        results = self.engine.local_search("user1", ["X"])
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
