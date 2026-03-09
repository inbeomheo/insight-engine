"""
의미 탐색 서비스 테스트
"""

import unittest

from services.semantic_explorer_service import (
    SemanticNode,
    ExplorationPath,
    build_semantic_map,
    explore,
    find_clusters,
    suggest_expansion,
)


class TestBuildSemanticMap(unittest.TestCase):
    """의미 맵 생성 테스트"""

    def test_basic_map(self):
        """기본 의미 맵 생성"""
        text = "Python programming is fun. Programming with Python makes development easy."
        nodes = build_semantic_map(text)
        self.assertGreater(len(nodes), 0)
        terms = [n.term for n in nodes]
        self.assertIn("python", terms)
        self.assertIn("programming", terms)

    def test_weight_normalization(self):
        """가중치 정규화 (최대 1.0)"""
        text = "Data science uses data analysis. Data processing is important."
        nodes = build_semantic_map(text)
        weights = [n.weight for n in nodes]
        self.assertLessEqual(max(weights), 1.0)
        self.assertGreater(max(weights), 0.0)

    def test_related_terms(self):
        """공출현 관련어"""
        text = "Machine learning uses algorithms. Machine learning processes data."
        nodes = build_semantic_map(text)
        node_map = {n.term: n for n in nodes}
        if "machine" in node_map:
            self.assertIn("learning", node_map["machine"].related)

    def test_empty_text(self):
        """빈 텍스트"""
        nodes = build_semantic_map("")
        self.assertEqual(nodes, [])

    def test_stopwords_filtered(self):
        """불용어 필터링"""
        text = "This is a test. The test is simple."
        nodes = build_semantic_map(text)
        terms = [n.term for n in nodes]
        self.assertNotIn("this", terms)
        self.assertNotIn("the", terms)

    def test_sorted_by_weight(self):
        """가중치 내림차순 정렬"""
        text = "Python code. Python programming. Python data. Java code."
        nodes = build_semantic_map(text)
        if len(nodes) > 1:
            for i in range(len(nodes) - 1):
                self.assertGreaterEqual(nodes[i].weight, nodes[i + 1].weight)

    def test_short_words_filtered(self):
        """짧은 단어 필터링 (2자 미만)"""
        text = "I am a developer. Programming is my job."
        nodes = build_semantic_map(text)
        terms = [n.term for n in nodes]
        # 1자 단어는 제외
        for term in terms:
            self.assertGreaterEqual(len(term), 2)


class TestExplore(unittest.TestCase):
    """의미 탐색 테스트"""

    def setUp(self):
        self.nodes = [
            SemanticNode("1", "python", 1.0, ["programming", "data"]),
            SemanticNode("2", "programming", 0.8, ["python", "code"]),
            SemanticNode("3", "data", 0.7, ["python", "analysis"]),
            SemanticNode("4", "code", 0.5, ["programming"]),
            SemanticNode("5", "analysis", 0.4, ["data"]),
        ]

    def test_explore_basic(self):
        """기본 탐색"""
        path = explore(self.nodes, "python", depth=2)
        self.assertEqual(path.start_term, "python")
        self.assertIn("python", path.path)
        self.assertGreater(len(path.path), 1)

    def test_explore_depth_limit(self):
        """깊이 제한"""
        path = explore(self.nodes, "python", depth=1)
        self.assertIsInstance(path, ExplorationPath)
        self.assertGreater(len(path.path), 0)

    def test_explore_unknown_term(self):
        """알 수 없는 용어"""
        path = explore(self.nodes, "unknown", depth=3)
        self.assertEqual(path.path, [])
        self.assertEqual(path.depth, 0)

    def test_explore_includes_related(self):
        """관련어 포함"""
        path = explore(self.nodes, "python", depth=3)
        # python → programming, data 방문
        self.assertIn("programming", path.path)
        self.assertIn("data", path.path)


class TestFindClusters(unittest.TestCase):
    """클러스터 탐지 테스트"""

    def test_single_cluster(self):
        """모두 연결된 단일 클러스터"""
        nodes = [
            SemanticNode("1", "python", 1.0, ["programming"]),
            SemanticNode("2", "programming", 0.8, ["python"]),
        ]
        clusters = find_clusters(nodes)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 2)

    def test_multiple_clusters(self):
        """여러 클러스터"""
        nodes = [
            SemanticNode("1", "python", 1.0, ["programming"]),
            SemanticNode("2", "programming", 0.8, ["python"]),
            SemanticNode("3", "cooking", 0.5, ["recipe"]),
            SemanticNode("4", "recipe", 0.4, ["cooking"]),
        ]
        clusters = find_clusters(nodes)
        self.assertEqual(len(clusters), 2)

    def test_isolated_nodes(self):
        """고립 노드"""
        nodes = [
            SemanticNode("1", "python", 1.0, []),
            SemanticNode("2", "java", 0.8, []),
        ]
        clusters = find_clusters(nodes)
        self.assertEqual(len(clusters), 2)

    def test_empty_nodes(self):
        """빈 노드 목록"""
        clusters = find_clusters([])
        self.assertEqual(clusters, [])

    def test_clusters_sorted_by_size(self):
        """클러스터 크기 내림차순"""
        nodes = [
            SemanticNode("1", "a", 1.0, ["b", "c"]),
            SemanticNode("2", "b", 0.8, ["a"]),
            SemanticNode("3", "c", 0.7, ["a"]),
            SemanticNode("4", "x", 0.5, []),
        ]
        clusters = find_clusters(nodes)
        for i in range(len(clusters) - 1):
            self.assertGreaterEqual(len(clusters[i]), len(clusters[i + 1]))


class TestSuggestExpansion(unittest.TestCase):
    """용어 확장 제안 테스트"""

    def test_suggest_direct_related(self):
        """직접 관련어 제안"""
        nodes = [
            SemanticNode("1", "python", 1.0, ["programming", "data"]),
            SemanticNode("2", "programming", 0.8, ["python"]),
            SemanticNode("3", "data", 0.7, ["python"]),
        ]
        suggestions = suggest_expansion(nodes, "python")
        self.assertIn("programming", suggestions)
        self.assertIn("data", suggestions)

    def test_suggest_second_order(self):
        """2차 관련어 포함"""
        nodes = [
            SemanticNode("1", "python", 1.0, ["programming"]),
            SemanticNode("2", "programming", 0.8, ["python", "code"]),
            SemanticNode("3", "code", 0.5, ["programming"]),
        ]
        suggestions = suggest_expansion(nodes, "python")
        # code는 programming을 통한 2차 관련어
        self.assertIn("code", suggestions)

    def test_suggest_unknown_term(self):
        """알 수 없는 용어"""
        nodes = [SemanticNode("1", "python", 1.0, [])]
        suggestions = suggest_expansion(nodes, "unknown")
        self.assertEqual(suggestions, [])

    def test_suggest_no_related(self):
        """관련어 없는 용어"""
        nodes = [SemanticNode("1", "python", 1.0, [])]
        suggestions = suggest_expansion(nodes, "python")
        self.assertEqual(suggestions, [])


if __name__ == "__main__":
    unittest.main()
