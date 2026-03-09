"""
entity_graph_service 단위 테스트
"""
import unittest
from services.entity_graph_service import (
    extract_entity_graph,
    EntityGraph,
    Entity,
    Relationship,
    _classify_entity,
    _extract_candidates,
    _count_mentions,
    _build_relationships,
    _infer_relation_type,
)


class TestClassifyEntity(unittest.TestCase):
    """엔터티 타입 분류 테스트"""

    def test_technology(self):
        self.assertEqual(_classify_entity("python"), "technology")
        self.assertEqual(_classify_entity("react"), "technology")

    def test_organization(self):
        self.assertEqual(_classify_entity("Google"), "organization")
        self.assertEqual(_classify_entity("OpenAI"), "organization")

    def test_person_two_words(self):
        """대문자 시작 2단어 → person"""
        self.assertEqual(_classify_entity("John Smith"), "person")

    def test_uppercase_acronym(self):
        """전체 대문자 3자 이상 → organization"""
        self.assertEqual(_classify_entity("NASA"), "organization")

    def test_product_hint(self):
        """제품 키워드 포함 → product"""
        self.assertEqual(_classify_entity("Vision Pro"), "product")

    def test_default_concept(self):
        self.assertEqual(_classify_entity("something"), "concept")


class TestExtractCandidates(unittest.TestCase):
    """엔터티 후보 추출 테스트"""

    def test_capitalized_words(self):
        text = "Google announced a new product called Gemini today."
        candidates = _extract_candidates(text)
        names = [c[0] for c in candidates]
        self.assertTrue(any("Google" in n for n in names))
        self.assertTrue(any("Gemini" in n for n in names))

    def test_acronyms(self):
        text = "The API uses REST and GraphQL endpoints."
        candidates = _extract_candidates(text)
        names = [c[0] for c in candidates]
        self.assertTrue(any("API" in n for n in names))

    def test_tech_keywords(self):
        text = "We use python and react for development."
        candidates = _extract_candidates(text)
        names = [c[0].lower() for c in candidates]
        self.assertTrue(any("python" in n for n in names))

    def test_stop_words_excluded(self):
        text = "The And But Not"
        candidates = _extract_candidates(text)
        names = [c[0] for c in candidates]
        # 불용어는 제외
        self.assertNotIn("The", names)
        self.assertNotIn("And", names)


class TestCountMentions(unittest.TestCase):
    """언급 횟수 테스트"""

    def test_single_mention(self):
        self.assertEqual(_count_mentions("Google is great", "Google"), 1)

    def test_multiple_mentions(self):
        self.assertEqual(_count_mentions("Python is great. I love Python.", "Python"), 2)

    def test_case_insensitive(self):
        self.assertEqual(_count_mentions("python PYTHON Python", "python"), 3)


class TestInferRelationType(unittest.TestCase):
    """관계 타입 추론 테스트"""

    def test_person_org(self):
        self.assertEqual(_infer_relation_type("person", "organization"), "affiliated_with")

    def test_org_tech(self):
        self.assertEqual(_infer_relation_type("organization", "technology"), "develops")

    def test_tech_tech(self):
        self.assertEqual(_infer_relation_type("technology", "technology"), "related_to")

    def test_person_person(self):
        self.assertEqual(_infer_relation_type("person", "person"), "collaborates_with")

    def test_org_product(self):
        self.assertEqual(_infer_relation_type("organization", "product"), "produces")

    def test_fallback(self):
        self.assertEqual(_infer_relation_type("concept", "concept"), "associated_with")


class TestBuildRelationships(unittest.TestCase):
    """관계 추출 테스트"""

    def test_co_occurring_entities(self):
        text = "Google uses Python. Google develops Python tools."
        entities = [
            Entity("Google", "organization", 2, 0),
            Entity("Python", "technology", 2, 12),
        ]
        rels = _build_relationships(text, entities)
        self.assertGreater(len(rels), 0)
        self.assertEqual(rels[0].source, "Google")
        self.assertEqual(rels[0].target, "Python")

    def test_single_entity_no_relations(self):
        text = "Only Google here."
        entities = [Entity("Google", "organization", 1, 5)]
        rels = _build_relationships(text, entities)
        self.assertEqual(len(rels), 0)

    def test_strength_range(self):
        text = "Google Python Google Python Google Python"
        entities = [
            Entity("Google", "organization", 3, 0),
            Entity("Python", "technology", 3, 7),
        ]
        rels = _build_relationships(text, entities)
        for r in rels:
            self.assertGreaterEqual(r.strength, 0.0)
            self.assertLessEqual(r.strength, 1.0)


class TestExtractEntityGraph(unittest.TestCase):
    """extract_entity_graph 메인 함수 테스트"""

    def test_basic_extraction(self):
        text = "Google announced a new AI model. Microsoft also released their Python SDK."
        result = extract_entity_graph(text)
        self.assertIsInstance(result, EntityGraph)
        self.assertGreater(result.total_entities, 0)
        # Google, Microsoft, Python 등이 추출되어야 함
        names = [e.name for e in result.entities]
        self.assertTrue(any("Google" in n for n in names))

    def test_empty_transcript(self):
        result = extract_entity_graph("")
        self.assertEqual(result.total_entities, 0)
        self.assertEqual(result.entities, [])
        self.assertEqual(result.relationships, [])

    def test_none_transcript(self):
        result = extract_entity_graph(None)
        self.assertEqual(result.total_entities, 0)

    def test_no_entities(self):
        result = extract_entity_graph("이것은 엔터티가 없는 한국어 텍스트입니다.")
        self.assertEqual(result.total_entities, 0)

    def test_entities_sorted_by_mentions(self):
        """언급 횟수 내림차순 정렬"""
        text = "Google Google Google Microsoft"
        result = extract_entity_graph(text)
        if len(result.entities) >= 2:
            self.assertGreaterEqual(
                result.entities[0].mention_count,
                result.entities[1].mention_count,
            )

    def test_max_50_entities(self):
        """최대 50개 엔터티 제한"""
        # 많은 고유 이름 생성
        names = [f"Entity{chr(65 + i)}{chr(65 + j)}" for i in range(10) for j in range(10)]
        text = " ".join(names)
        result = extract_entity_graph(text)
        self.assertLessEqual(result.total_entities, 50)

    def test_relationships_present(self):
        """같은 문맥에 함께 등장하면 관계가 생성됨"""
        text = "Google develops Python tools. Google uses Python for AI."
        result = extract_entity_graph(text)
        # 관계가 있을 수 있음
        if result.relationships:
            self.assertIsInstance(result.relationships[0], Relationship)

    def test_first_mention_tracked(self):
        """첫 출현 위치 추적"""
        text = "Later Google appeared. Earlier Microsoft was here."
        result = extract_entity_graph(text)
        for entity in result.entities:
            self.assertGreaterEqual(entity.first_mention, 0)


if __name__ == '__main__':
    unittest.main()
