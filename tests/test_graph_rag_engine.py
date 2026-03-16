"""
GraphRAGEngine 단위 테스트
"""
import tempfile
import unittest
from unittest.mock import patch, MagicMock

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

    def test_global_search_empty(self):
        result = self.engine.global_search("user1")
        self.assertEqual(result["nodes"], [])
        self.assertEqual(result["stats"]["node_count"], 0)

    def test_global_search_returns_top_nodes(self):
        self.store.add_entities("user1", [
            {"name": "Hub", "type": "concept"},
            {"name": "Leaf1", "type": "concept"},
            {"name": "Leaf2", "type": "concept"},
            {"name": "Leaf3", "type": "concept"},
        ])
        self.store.add_relations("user1", [
            {"source": "Hub", "target": "Leaf1", "relation": "r"},
            {"source": "Hub", "target": "Leaf2", "relation": "r"},
            {"source": "Hub", "target": "Leaf3", "relation": "r"},
        ])
        result = self.engine.global_search("user1", top_n=2)
        self.assertEqual(len(result["nodes"]), 2)
        # Hub는 degree 3으로 최상위
        self.assertEqual(result["nodes"][0]["name"], "Hub")

    def test_build_context_empty(self):
        result = self.engine.build_context("user1", ["X"])
        self.assertEqual(result, "")

    def test_build_context_with_data(self):
        self.store.add_entities("user1", [
            {"name": "Python", "type": "tech", "description": "프로그래밍 언어"},
            {"name": "Django", "type": "tech", "description": "웹 프레임워크"},
        ])
        self.store.add_relations("user1", [
            {"source": "Python", "target": "Django", "relation": "기반 기술"},
        ])
        result = self.engine.build_context("user1", ["Python"])
        self.assertIn("Python", result)
        self.assertIn("tech", result)
        self.assertIn("프로그래밍 언어", result)

    def test_build_context_relation_display(self):
        self.store.add_entities("user1", [
            {"name": "A", "type": "t"},
            {"name": "B", "type": "t"},
        ])
        self.store.add_relations("user1", [
            {"source": "A", "target": "B", "relation": "사용"},
        ])
        result = self.engine.build_context("user1", ["A"])
        self.assertIn("→", result)  # outgoing 관계 표시


if __name__ == "__main__":
    unittest.main()
