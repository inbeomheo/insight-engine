"""
학습 지식그래프 서비스 테스트
"""

import unittest

from services.learning_knowledge_graph_service import (
    Concept,
    ConceptEdge,
    LearningGraph,
    add_concept,
    add_relation,
    get_learning_path,
    find_foundational,
    topological_sort,
)


class TestAddConcept(unittest.TestCase):
    """개념 추가 테스트"""

    def test_add_basic(self):
        """기본 개념 추가"""
        graph = LearningGraph()
        graph = add_concept(graph, "변수", "데이터를 저장하는 이름", 1)
        self.assertEqual(len(graph.concepts), 1)
        self.assertEqual(graph.concepts[0].name, "변수")
        self.assertEqual(graph.concepts[0].difficulty, 1)

    def test_add_multiple(self):
        """여러 개념 추가"""
        graph = LearningGraph()
        graph = add_concept(graph, "변수", difficulty=1)
        graph = add_concept(graph, "함수", difficulty=2)
        graph = add_concept(graph, "클래스", difficulty=3)
        self.assertEqual(len(graph.concepts), 3)

    def test_add_invalid_difficulty_low(self):
        """난이도 범위 초과 (하한)"""
        graph = LearningGraph()
        with self.assertRaises(ValueError):
            add_concept(graph, "테스트", difficulty=0)

    def test_add_invalid_difficulty_high(self):
        """난이도 범위 초과 (상한)"""
        graph = LearningGraph()
        with self.assertRaises(ValueError):
            add_concept(graph, "테스트", difficulty=6)

    def test_add_duplicate_name(self):
        """중복 이름 추가 금지"""
        graph = LearningGraph()
        graph = add_concept(graph, "변수")
        with self.assertRaises(ValueError):
            add_concept(graph, "변수")


class TestAddRelation(unittest.TestCase):
    """관계 추가 테스트"""

    def setUp(self):
        self.graph = LearningGraph()
        self.graph = add_concept(self.graph, "변수", difficulty=1)
        self.graph = add_concept(self.graph, "함수", difficulty=2)
        self.graph = add_concept(self.graph, "클래스", difficulty=3)

    def test_add_prerequisite(self):
        """선수조건 관계 추가"""
        self.graph = add_relation(self.graph, "변수", "함수", "prerequisite")
        self.assertEqual(len(self.graph.edges), 1)
        self.assertEqual(self.graph.edges[0].relation, "prerequisite")

    def test_add_by_name(self):
        """이름으로 관계 추가"""
        self.graph = add_relation(self.graph, "변수", "함수", "related")
        self.assertEqual(len(self.graph.edges), 1)

    def test_prerequisite_updates_list(self):
        """prerequisite 관계가 prerequisites 목록에 반영"""
        self.graph = add_relation(self.graph, "변수", "함수", "prerequisite")
        func_concept = next(c for c in self.graph.concepts if c.name == "함수")
        var_concept = next(c for c in self.graph.concepts if c.name == "변수")
        self.assertIn(var_concept.concept_id, func_concept.prerequisites)

    def test_invalid_relation(self):
        """잘못된 관계 유형"""
        with self.assertRaises(ValueError):
            add_relation(self.graph, "변수", "함수", "unknown")

    def test_invalid_source(self):
        """존재하지 않는 소스"""
        with self.assertRaises(ValueError):
            add_relation(self.graph, "없는개념", "함수", "related")

    def test_invalid_target(self):
        """존재하지 않는 타겟"""
        with self.assertRaises(ValueError):
            add_relation(self.graph, "변수", "없는개념", "related")


class TestGetLearningPath(unittest.TestCase):
    """학습 경로 테스트"""

    def setUp(self):
        self.graph = LearningGraph()
        self.graph = add_concept(self.graph, "변수", difficulty=1)
        self.graph = add_concept(self.graph, "함수", difficulty=2)
        self.graph = add_concept(self.graph, "클래스", difficulty=3)
        self.graph = add_concept(self.graph, "상속", difficulty=4)
        # 변수 → 함수 → 클래스 → 상속
        self.graph = add_relation(self.graph, "변수", "함수", "prerequisite")
        self.graph = add_relation(self.graph, "함수", "클래스", "prerequisite")
        self.graph = add_relation(self.graph, "클래스", "상속", "prerequisite")

    def test_full_path(self):
        """전체 경로"""
        path = get_learning_path(self.graph, "변수", "상속")
        self.assertEqual(path, ["변수", "함수", "클래스", "상속"])

    def test_partial_path(self):
        """부분 경로"""
        path = get_learning_path(self.graph, "함수", "상속")
        self.assertEqual(path, ["함수", "클래스", "상속"])

    def test_same_start_goal(self):
        """시작 = 목표"""
        path = get_learning_path(self.graph, "변수", "변수")
        self.assertEqual(path, ["변수"])

    def test_no_path(self):
        """경로 없음"""
        self.graph = add_concept(self.graph, "요리", difficulty=1)
        path = get_learning_path(self.graph, "변수", "요리")
        self.assertEqual(path, [])

    def test_invalid_start(self):
        """잘못된 시작점"""
        path = get_learning_path(self.graph, "없는개념", "상속")
        self.assertEqual(path, [])

    def test_path_with_related(self):
        """related 관계를 통한 경로"""
        graph = LearningGraph()
        graph = add_concept(graph, "A", difficulty=1)
        graph = add_concept(graph, "B", difficulty=2)
        graph = add_relation(graph, "A", "B", "related")
        path = get_learning_path(graph, "A", "B")
        self.assertGreater(len(path), 0)


class TestFindFoundational(unittest.TestCase):
    """기초 개념 찾기 테스트"""

    def test_find_foundational(self):
        """기초 개념 찾기"""
        graph = LearningGraph()
        graph = add_concept(graph, "변수", difficulty=1)
        graph = add_concept(graph, "함수", difficulty=2)
        graph = add_relation(graph, "변수", "함수", "prerequisite")
        foundations = find_foundational(graph)
        names = [c.name for c in foundations]
        self.assertIn("변수", names)
        self.assertNotIn("함수", names)

    def test_all_foundational(self):
        """모두 기초 (관계 없음)"""
        graph = LearningGraph()
        graph = add_concept(graph, "A", difficulty=1)
        graph = add_concept(graph, "B", difficulty=1)
        foundations = find_foundational(graph)
        self.assertEqual(len(foundations), 2)

    def test_empty_graph(self):
        """빈 그래프"""
        graph = LearningGraph()
        foundations = find_foundational(graph)
        self.assertEqual(foundations, [])


class TestTopologicalSort(unittest.TestCase):
    """위상 정렬 테스트"""

    def test_basic_sort(self):
        """기본 위상 정렬"""
        graph = LearningGraph()
        graph = add_concept(graph, "변수", difficulty=1)
        graph = add_concept(graph, "함수", difficulty=2)
        graph = add_concept(graph, "클래스", difficulty=3)
        graph = add_relation(graph, "변수", "함수", "prerequisite")
        graph = add_relation(graph, "함수", "클래스", "prerequisite")
        result = topological_sort(graph)
        self.assertEqual(result.index("변수"), 0)
        self.assertLess(result.index("함수"), result.index("클래스"))

    def test_no_relations(self):
        """관계 없는 그래프"""
        graph = LearningGraph()
        graph = add_concept(graph, "A", difficulty=1)
        graph = add_concept(graph, "B", difficulty=1)
        result = topological_sort(graph)
        self.assertEqual(len(result), 2)

    def test_empty_graph(self):
        """빈 그래프"""
        graph = LearningGraph()
        result = topological_sort(graph)
        self.assertEqual(result, [])

    def test_complex_dependencies(self):
        """복잡한 의존성"""
        graph = LearningGraph()
        graph = add_concept(graph, "기초수학", difficulty=1)
        graph = add_concept(graph, "통계", difficulty=2)
        graph = add_concept(graph, "선형대수", difficulty=2)
        graph = add_concept(graph, "머신러닝", difficulty=3)
        graph = add_relation(graph, "기초수학", "통계", "prerequisite")
        graph = add_relation(graph, "기초수학", "선형대수", "prerequisite")
        graph = add_relation(graph, "통계", "머신러닝", "prerequisite")
        graph = add_relation(graph, "선형대수", "머신러닝", "prerequisite")
        result = topological_sort(graph)
        self.assertEqual(result[0], "기초수학")
        self.assertEqual(result[-1], "머신러닝")


if __name__ == "__main__":
    unittest.main()
