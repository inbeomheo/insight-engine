"""
GraphStore 단위 테스트
"""
import json
import os
import tempfile
import unittest

from services.rag.graph_store import GraphStore


class TestGraphStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = GraphStore(store_path=self.tmpdir)
        self.user_id = "test-user-1"

    def test_add_entities(self):
        entities = [
            {"name": "Python", "type": "technology", "description": "프로그래밍 언어"},
            {"name": "Django", "type": "technology", "description": "웹 프레임워크"},
        ]
        self.store.add_entities(self.user_id, entities)
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 2)

    def test_add_entities_skips_empty_name(self):
        entities = [
            {"name": "", "type": "concept"},
            {"name": "Valid", "type": "concept"},
        ]
        self.store.add_entities(self.user_id, entities)
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 1)

    def test_add_entities_updates_existing(self):
        self.store.add_entities(self.user_id, [{"name": "A", "type": "t", "description": "v1"}])
        self.store.add_entities(self.user_id, [{"name": "A", "type": "t", "description": "v2"}])
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 1)

    def test_add_relations(self):
        relations = [
            {"source": "A", "target": "B", "relation": "depends_on", "weight": 0.8},
        ]
        self.store.add_relations(self.user_id, relations)
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 2)  # 자동 생성
        self.assertEqual(stats["edge_count"], 1)

    def test_add_relations_skips_empty(self):
        relations = [
            {"source": "", "target": "B", "relation": "r"},
            {"source": "A", "target": "", "relation": "r"},
        ]
        self.store.add_relations(self.user_id, relations)
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["edge_count"], 0)

    def test_search_related_empty_graph(self):
        results = self.store.search_related(self.user_id, ["X"])
        self.assertEqual(results, [])

    def test_search_related_exact_match(self):
        self.store.add_entities(self.user_id, [
            {"name": "Python", "type": "tech", "description": "언어"},
            {"name": "Django", "type": "tech", "description": "프레임워크"},
        ])
        self.store.add_relations(self.user_id, [
            {"source": "Python", "target": "Django", "relation": "사용"},
        ])
        results = self.store.search_related(self.user_id, ["Python"])
        names = [r["name"] for r in results]
        self.assertIn("Python", names)
        self.assertIn("Django", names)

    def test_search_related_partial_match(self):
        self.store.add_entities(self.user_id, [
            {"name": "Python3", "type": "tech", "description": ""},
        ])
        results = self.store.search_related(self.user_id, ["python"])
        self.assertTrue(len(results) > 0)

    def test_get_subgraph_not_found(self):
        result = self.store.get_subgraph(self.user_id, "없는엔티티")
        self.assertEqual(result["nodes"], [])
        self.assertEqual(result["edges"], [])

    def test_get_subgraph(self):
        self.store.add_entities(self.user_id, [
            {"name": "A", "type": "t", "description": ""},
            {"name": "B", "type": "t", "description": ""},
            {"name": "C", "type": "t", "description": ""},
        ])
        self.store.add_relations(self.user_id, [
            {"source": "A", "target": "B", "relation": "r1"},
            {"source": "A", "target": "C", "relation": "r2"},
        ])
        result = self.store.get_subgraph(self.user_id, "A")
        self.assertEqual(result["center"], "A")
        self.assertEqual(len(result["nodes"]), 3)
        self.assertEqual(len(result["edges"]), 2)

    def test_clear(self):
        self.store.add_entities(self.user_id, [{"name": "X", "type": "t"}])
        self.store.clear(self.user_id)
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 0)

    def test_persistence_save_and_reload(self):
        self.store.add_entities(self.user_id, [
            {"name": "Node1", "type": "tech", "description": "desc"},
        ])
        # 새 인스턴스로 로드
        store2 = GraphStore(store_path=self.tmpdir)
        stats = store2.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 1)

    def test_graph_file_sanitizes_user_id(self):
        path = self.store._graph_file("user/with:special@chars")
        self.assertNotIn("/", os.path.basename(path).replace(".json", ""))
        self.assertNotIn(":", os.path.basename(path).replace(".json", ""))

    def test_corrupted_json_file(self):
        """손상된 JSON 파일은 빈 그래프로 초기화"""
        fpath = self.store._graph_file(self.user_id)
        with open(fpath, "w") as f:
            f.write("{invalid json")
        stats = self.store.get_stats(self.user_id)
        self.assertEqual(stats["node_count"], 0)


if __name__ == "__main__":
    unittest.main()
