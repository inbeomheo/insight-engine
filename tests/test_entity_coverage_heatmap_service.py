"""엔터티 커버리지 히트맵 서비스 테스트"""
import unittest
from services.entity_coverage_heatmap_service import (
    generate_entity_heatmap,
    EntityHeatmap,
    EntityCoverage,
    _extract_entities,
    _count_entity,
)


class TestExtractEntities(unittest.TestCase):
    """엔터티 추출 테스트"""

    def test_english_proper_nouns(self):
        entities = _extract_entities("Google and Microsoft are tech companies.")
        self.assertIn("Google", entities)
        self.assertIn("Microsoft", entities)

    def test_korean_nouns(self):
        entities = _extract_entities("인공지능 기술은 빠르게 발전한다")
        self.assertIn("인공지능", entities)
        # "기술은"은 조사 필터에 걸리므로, 단독 명사 확인
        self.assertIn("발전한다", entities)

    def test_empty_content(self):
        entities = _extract_entities("")
        self.assertEqual(entities, [])


class TestCountEntity(unittest.TestCase):
    """엔터티 카운트 테스트"""

    def test_case_insensitive(self):
        count = _count_entity("Google uses google search.", "google")
        self.assertEqual(count, 2)

    def test_no_match(self):
        count = _count_entity("Hello World", "Python")
        self.assertEqual(count, 0)


class TestGenerateEntityHeatmap(unittest.TestCase):
    """히트맵 생성 테스트"""

    def test_empty_content(self):
        result = generate_entity_heatmap("")
        self.assertIsInstance(result, EntityHeatmap)
        self.assertEqual(result.coverage_score, 0.0)
        self.assertEqual(result.entities, [])

    def test_basic_content(self):
        content = "Python is a popular programming language. Python is used widely."
        result = generate_entity_heatmap(content)
        self.assertGreater(len(result.entities), 0)
        self.assertGreater(result.coverage_score, 0.0)

    def test_with_competitors(self):
        content = "Python is great for data science."
        competitors = [
            {"name": "CompA", "content": "Java and Kotlin are excellent for Android."}
        ]
        result = generate_entity_heatmap(content, competitors)
        # 경쟁사에만 있는 엔터티는 gaps에 포함
        self.assertIsInstance(result.gaps, list)

    def test_coverage_score_range(self):
        content = "Python Java Kotlin Ruby"
        result = generate_entity_heatmap(content)
        self.assertGreaterEqual(result.coverage_score, 0.0)
        self.assertLessEqual(result.coverage_score, 1.0)

    def test_entity_coverage_fields(self):
        content = "TensorFlow is an open source library."
        result = generate_entity_heatmap(content)
        for ec in result.entities:
            self.assertIsInstance(ec, EntityCoverage)
            self.assertIsInstance(ec.entity, str)
            self.assertIsInstance(ec.mentioned, bool)
            self.assertIsInstance(ec.frequency, int)

    def test_competitor_gap_detection(self):
        content = "Python is great."
        competitors = [{"name": "B", "content": "Rust and Go are fast languages."}]
        result = generate_entity_heatmap(content, competitors)
        # Rust 또는 Go 가 gaps에 포함되어야 한다
        gap_entities = set(result.gaps)
        self.assertTrue(
            gap_entities & {"Rust", "Go"},
            f"경쟁사 엔터티가 gaps에 포함되어야 합니다. gaps={result.gaps}"
        )

    def test_no_competitors(self):
        content = "React is a JavaScript library."
        result = generate_entity_heatmap(content, None)
        self.assertEqual(result.gaps, [])

    def test_whitespace_only_content(self):
        result = generate_entity_heatmap("   \n\t  ")
        self.assertEqual(result.coverage_score, 0.0)


if __name__ == "__main__":
    unittest.main()
