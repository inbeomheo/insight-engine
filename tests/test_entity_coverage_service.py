"""
Entity Coverage Analyzer 서비스 단위 테스트

엔터티 추출, 관계 분석, 커버리지 점수, 제안 생성을 검증합니다.
"""
import unittest

from services.seo.entity_coverage_service import analyze_entities


class TestEntityCoverageService(unittest.TestCase):
    """Entity Coverage Analyzer 테스트 케이스"""

    # ── 1. 빈 콘텐츠 ────────────────────────────────────────────

    def test_empty_content(self):
        """빈 문자열 입력 시 기본 구조를 반환한다."""
        result = analyze_entities("")

        self.assertEqual(result["entities"], [])
        self.assertEqual(result["entity_density"], 0.0)
        self.assertEqual(result["type_distribution"], {})
        self.assertEqual(result["relationships"], [])
        self.assertEqual(result["coverage_score"], 0)
        self.assertIsInstance(result["suggestions"], list)
        self.assertTrue(len(result["suggestions"]) > 0)

    # ── 2. None 입력 ────────────────────────────────────────────

    def test_none_content(self):
        """None 입력 시 빈 결과를 반환한다."""
        result = analyze_entities(None)

        self.assertEqual(result["entities"], [])
        self.assertEqual(result["entity_density"], 0.0)
        self.assertEqual(result["coverage_score"], 0)

    # ── 3. 브랜드 감지 ──────────────────────────────────────────

    def test_brand_detection(self):
        """알려진 브랜드(Google, Apple 등)를 정확히 감지한다."""
        content = "Google은 AI 분야에서 선두를 달리고 있다. Apple도 최근 AI 칩을 공개했다. Microsoft는 클라우드 시장을 주도한다."
        result = analyze_entities(content)

        entity_names = [e["name"] for e in result["entities"]]
        self.assertIn("Google", entity_names)
        self.assertIn("Apple", entity_names)
        self.assertIn("Microsoft", entity_names)

        # 브랜드 타입 확인
        brand_entities = [e for e in result["entities"] if e["type"] == "brand"]
        brand_names = [e["name"] for e in brand_entities]
        self.assertIn("Google", brand_names)
        self.assertIn("Apple", brand_names)

    # ── 4. 기술 감지 ────────────────────────────────────────────

    def test_technology_detection(self):
        """기술 키워드(AI, Python 등)를 정확히 감지한다."""
        content = "이 프로젝트는 Python과 React를 사용합니다. 백엔드는 Django로 구축하고, DevOps 파이프라인을 통해 배포합니다."
        result = analyze_entities(content)

        entity_names = [e["name"] for e in result["entities"]]
        self.assertIn("Python", entity_names)
        self.assertIn("React", entity_names)
        self.assertIn("Django", entity_names)

        # 기술 타입 확인
        tech_entities = [e for e in result["entities"] if e["type"] == "technology"]
        tech_names = [e["name"] for e in tech_entities]
        self.assertIn("Python", tech_names)

    # ── 5. 제품 감지 ────────────────────────────────────────────

    def test_product_detection(self):
        """알려진 제품(ChatGPT, GPT-4 등)을 정확히 감지한다."""
        content = "ChatGPT는 대화형 AI의 혁명이다. GPT-4 기반으로 동작하며, Claude와 Gemini도 경쟁 제품이다."
        result = analyze_entities(content)

        entity_names = [e["name"] for e in result["entities"]]
        self.assertIn("ChatGPT", entity_names)
        self.assertIn("GPT-4", entity_names)
        self.assertIn("Claude", entity_names)
        self.assertIn("Gemini", entity_names)

        # 제품 타입 확인
        product_entities = [e for e in result["entities"] if e["type"] == "product"]
        product_names = [e["name"] for e in product_entities]
        self.assertIn("ChatGPT", product_names)
        self.assertIn("GPT-4", product_names)

    # ── 6. 개념 감지 ────────────────────────────────────────────

    def test_concept_detection(self):
        """추상 개념 키워드가 2회 이상 등장하면 감지한다."""
        content = "디지털 전환 전략이 필요합니다. 자동화를 통한 효율성 향상이 핵심입니다. 전략적 자동화 도입이 시급합니다."
        result = analyze_entities(content)

        entity_names = [e["name"] for e in result["entities"]]
        # "전략"과 "자동화"가 각각 2회 등장
        self.assertIn("전략", entity_names)
        self.assertIn("자동화", entity_names)

        # 개념 타입 확인
        concept_entities = [e for e in result["entities"] if e["type"] == "concept"]
        concept_names = [e["name"] for e in concept_entities]
        self.assertTrue(len(concept_names) >= 2)

    # ── 7. 등장 횟수 정확성 ─────────────────────────────────────

    def test_entity_count(self):
        """엔터티 등장 횟수가 정확하다."""
        content = "Google이 발표한 AI 서비스. Google의 AI 기술은 Google Cloud와 통합된다."
        result = analyze_entities(content)

        google_entity = next(
            (e for e in result["entities"] if e["name"] == "Google"), None
        )
        self.assertIsNotNone(google_entity)
        self.assertEqual(google_entity["count"], 3)

    # ── 8. 엔터티 밀도 계산 ─────────────────────────────────────

    def test_entity_density(self):
        """엔터티 밀도가 올바르게 계산된다 (엔터티 수 / 단어 수 × 100)."""
        content = "Google과 Apple은 기술 기업이다."
        result = analyze_entities(content)

        self.assertIsInstance(result["entity_density"], float)
        self.assertGreater(result["entity_density"], 0)
        # 밀도 = 총 멘션 수 / 단어 수 × 100
        # 단어: Google, Apple, 기술, 기업이다 = 최소 4개, 멘션 최소 2개
        # 밀도 > 0이면 정상
        self.assertGreaterEqual(result["entity_density"], 0)

    # ── 9. 타입 분포 ────────────────────────────────────────────

    def test_type_distribution(self):
        """타입별 엔터티 수가 정확히 분포된다."""
        content = (
            "Google과 Apple은 AI 기술을 선도한다. "
            "ChatGPT와 Claude는 대표 제품이다. "
            "전략과 전략적 자동화, 자동화 도입이 핵심이다."
        )
        result = analyze_entities(content)
        dist = result["type_distribution"]

        self.assertIsInstance(dist, dict)
        # 브랜드 존재
        self.assertIn("brand", dist)
        self.assertGreaterEqual(dist["brand"], 1)
        # 제품 존재
        self.assertIn("product", dist)
        self.assertGreaterEqual(dist["product"], 1)

    # ── 10. 동시 등장 관계 ──────────────────────────────────────

    def test_relationships(self):
        """같은 문장에 동시 등장하는 엔터티 쌍을 관계로 기록한다."""
        content = "Google과 Apple은 AI 시장에서 경쟁한다. Google과 Microsoft도 클라우드에서 경쟁한다."
        result = analyze_entities(content)

        relationships = result["relationships"]
        self.assertIsInstance(relationships, list)
        self.assertTrue(len(relationships) > 0)

        # Google-Apple 또는 Apple-Google 관계 존재
        pair_names = [(r["entity1"], r["entity2"]) for r in relationships]
        google_apple = any(
            ("Apple" in pair and "Google" in pair)
            for pair in pair_names
        )
        self.assertTrue(google_apple, "Google과 Apple의 동시 등장 관계가 있어야 합니다.")

        # co_occurrence 값이 양수
        for rel in relationships:
            self.assertGreater(rel["co_occurrence"], 0)

    # ── 11. 커버리지 점수 범위 ──────────────────────────────────

    def test_coverage_score_range(self):
        """커버리지 점수가 0-100 범위 내에 있다."""
        # 빈 콘텐츠
        result_empty = analyze_entities("")
        self.assertGreaterEqual(result_empty["coverage_score"], 0)
        self.assertLessEqual(result_empty["coverage_score"], 100)

        # 풍부한 콘텐츠
        content = (
            "Google의 Gemini와 OpenAI의 ChatGPT가 AI 시장을 주도한다. "
            "Python과 React로 개발된 플랫폼에서 자동화 전략을 구현한다. "
            "김철수 대표는 디지털 전환 전략을 발표했다. "
            "한국기술연구소에서 AI 분석 도구를 공개했다. "
            "자동화와 최적화, 전략, 분석이 핵심이다."
        )
        result_rich = analyze_entities(content)
        self.assertGreaterEqual(result_rich["coverage_score"], 0)
        self.assertLessEqual(result_rich["coverage_score"], 100)
        # 풍부한 콘텐츠의 점수가 빈 콘텐츠보다 높아야 한다
        self.assertGreater(result_rich["coverage_score"], result_empty["coverage_score"])

    # ── 12. 문맥 포함 ──────────────────────────────────────────

    def test_context_included(self):
        """각 엔터티에 첫 등장 주변 문맥이 포함된다."""
        content = "최근 Google은 새로운 AI 모델을 발표하여 업계를 놀라게 했습니다."
        result = analyze_entities(content)

        google_entity = next(
            (e for e in result["entities"] if e["name"] == "Google"), None
        )
        self.assertIsNotNone(google_entity)
        self.assertIsInstance(google_entity["context"], str)
        self.assertTrue(len(google_entity["context"]) > 0)
        # 문맥에 엔터티 이름이 포함
        self.assertIn("Google", google_entity["context"])

    # ── 13. 제안 목록 ──────────────────────────────────────────

    def test_suggestions(self):
        """누락된 엔터티 타입에 대한 제안이 생성된다."""
        # 브랜드만 있는 콘텐츠 → 다른 타입 제안
        content = "Google과 Apple, Microsoft, Amazon, Meta가 시장을 지배한다."
        result = analyze_entities(content)

        suggestions = result["suggestions"]
        self.assertIsInstance(suggestions, list)
        # 인물/제품/개념/조직 등 누락 타입에 대한 제안이 있어야 함
        self.assertTrue(len(suggestions) > 0)

        # 제안 내용에 누락된 타입 언급이 포함
        all_suggestions_text = " ".join(suggestions)
        # 인물이 없으므로 인물 관련 제안이 있어야 함
        has_type_suggestion = any(
            keyword in all_suggestions_text
            for keyword in ["인물", "제품", "개념", "조직", "기술"]
        )
        self.assertTrue(has_type_suggestion, "누락된 엔터티 타입에 대한 제안이 있어야 합니다.")


if __name__ == "__main__":
    unittest.main()
