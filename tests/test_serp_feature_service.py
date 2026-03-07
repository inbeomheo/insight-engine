"""
SERP Feature Opportunity Analyzer 서비스 단위 테스트
"""
import unittest

from services.serp_feature_service import analyze_serp_features


class TestSerpFeatureService(unittest.TestCase):
    """analyze_serp_features 함수의 동작을 검증한다."""

    # ── 1. 빈 콘텐츠 ──
    def test_empty_content(self):
        """빈 문자열 입력 시 기본 결과를 반환한다."""
        result = analyze_serp_features("")
        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["overall_serp_score"], 0.0)
        self.assertEqual(result["best_opportunity"], "")
        self.assertFalse(result["content_format_analysis"]["has_definition"])
        self.assertTrue(len(result["suggestions"]) > 0)

    # ── 2. None 콘텐츠 ──
    def test_none_content(self):
        """None 입력 시 빈 결과를 반환한다."""
        result = analyze_serp_features(None)
        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["overall_serp_score"], 0.0)
        self.assertEqual(result["best_opportunity"], "")

    # ── 3. Featured Snippet — 정의형 콘텐츠 ──
    def test_featured_snippet(self):
        """정의형 문장이 포함된 콘텐츠는 featured_snippet readiness가 높다."""
        # 40-60자 정의형 문장 + 첫 2문장 + 헤딩-답변 구조
        content = (
            "## 머신러닝이란 무엇인가\n"
            "머신러닝이란 컴퓨터가 데이터를 학습하여 패턴을 인식하고 예측하는 기술을 의미한다.\n"
            "이 기술은 다양한 분야에서 활용됩니다.\n"
            "## 주요 특징\n"
            "지도학습, 비지도학습, 강화학습이 있습니다."
        )
        result = analyze_serp_features(content)

        snippet_opp = next(
            o for o in result["opportunities"] if o["feature"] == "featured_snippet"
        )
        self.assertGreaterEqual(snippet_opp["current_readiness"], 40)
        self.assertIn(snippet_opp["probability"], ["high", "medium"])

    # ── 4. List Snippet — 목록형 콘텐츠 ──
    def test_list_snippet(self):
        """순서/비순서 목록이 포함된 콘텐츠는 list_snippet readiness가 높다."""
        content = (
            "## TOP 10 추천 프레임워크\n"
            "1. React - UI 라이브러리\n"
            "2. Vue - 프로그레시브 프레임워크\n"
            "3. Angular - 풀스택 프레임워크\n"
            "4. Svelte - 컴파일러 기반\n"
            "- 경량 옵션 A\n"
            "- 경량 옵션 B\n"
            "- 경량 옵션 C\n"
            "- 경량 옵션 D\n"
            "- 경량 옵션 E\n"
        )
        result = analyze_serp_features(content)

        list_opp = next(
            o for o in result["opportunities"] if o["feature"] == "list_snippet"
        )
        # 순서 목록 4개(>=3), 비순서 목록 5개(>=5), TOP+추천 키워드 = 100
        self.assertEqual(list_opp["current_readiness"], 100.0)
        self.assertEqual(list_opp["probability"], "high")

    # ── 5. Table Snippet — 표 포함 콘텐츠 ──
    def test_table_snippet(self):
        """마크다운 테이블이 포함되면 table_snippet readiness가 높다."""
        content = (
            "## 프레임워크 비교표\n"
            "| 프레임워크 | 성능 | 가격 |\n"
            "| --- | --- | --- |\n"
            "| React | 빠름 | 무료 |\n"
            "| Vue | 빠름 | 무료 |\n"
        )
        result = analyze_serp_features(content)

        table_opp = next(
            o for o in result["opportunities"] if o["feature"] == "table_snippet"
        )
        # 테이블 +50, 비교+구조 +30, 가격 +20 = 100
        self.assertEqual(table_opp["current_readiness"], 100.0)
        self.assertEqual(table_opp["probability"], "high")

    # ── 6. How-to — 단계별 가이드 ──
    def test_how_to(self):
        """단계별 설명이 포함된 콘텐츠는 how_to_rich_result readiness가 높다."""
        content = (
            "## Git 사용 방법 가이드\n"
            "1단계: Git을 설치합니다. 공식 사이트에서 다운로드하세요.\n"
            "2단계: 저장소를 초기화합니다. git init 명령어를 실행합니다.\n"
            "3단계: 변경사항을 커밋합니다. git commit -m 메시지를 입력합니다.\n"
        )
        result = analyze_serp_features(content)

        howto_opp = next(
            o for o in result["opportunities"] if o["feature"] == "how_to_rich_result"
        )
        # 단계 3개 +40, 방법/가이드 키워드 +30, 단계별 설명 +30 = 100
        self.assertEqual(howto_opp["current_readiness"], 100.0)
        self.assertEqual(howto_opp["probability"], "high")

    # ── 7. FAQ 형식 ──
    def test_faq_format(self):
        """FAQ 형식 콘텐츠는 faq_rich_result readiness가 높다."""
        content = (
            "## FAQ 자주 묻는 질문\n"
            "Q: Python은 무엇인가요?\n"
            "A: Python은 범용 프로그래밍 언어입니다.\n"
            "Q: Python은 어디에 사용되나요?\n"
            "A: 웹 개발, 데이터 분석, AI 등에 사용됩니다.\n"
            "Q: Python은 배우기 쉬운가요?\n"
            "A: 네, 초보자에게 가장 추천되는 언어입니다.\n"
        )
        result = analyze_serp_features(content)

        faq_opp = next(
            o for o in result["opportunities"] if o["feature"] == "faq_rich_result"
        )
        # Q&A 패턴 +40, 질문 3개+ +30, FAQ 헤딩 +30 = 100
        self.assertEqual(faq_opp["current_readiness"], 100.0)
        self.assertEqual(faq_opp["probability"], "high")

    # ── 8. PAA 형식 ──
    def test_paa_format(self):
        """질문형 헤딩과 답변이 있는 콘텐츠는 people_also_ask readiness가 높다."""
        content = (
            "## FAQ\n"
            "## React는 무엇인가요?\n"
            "React는 Facebook이 만든 UI 라이브러리입니다.\n"
            "컴포넌트 기반으로 UI를 구성합니다.\n"
            "가상 DOM을 사용합니다.\n"
            "## Vue는 배우기 쉬운가요?\n"
            "Vue는 러닝커브가 낮습니다.\n"
            "공식 문서가 매우 잘 되어 있습니다.\n"
            "커뮤니티 지원도 활발합니다.\n"
        )
        result = analyze_serp_features(content)

        paa_opp = next(
            o for o in result["opportunities"] if o["feature"] == "people_also_ask"
        )
        # 질문형 헤딩 2개+ +40, 질문 후 2-3문장 +30, FAQ 헤딩 +30 = 100
        self.assertEqual(paa_opp["current_readiness"], 100.0)
        self.assertEqual(paa_opp["probability"], "high")

    # ── 9. overall_score 범위 검증 ──
    def test_overall_score_range(self):
        """overall_serp_score는 항상 0-100 범위이다."""
        # 일반 콘텐츠
        result = analyze_serp_features("간단한 텍스트입니다.")
        self.assertGreaterEqual(result["overall_serp_score"], 0)
        self.assertLessEqual(result["overall_serp_score"], 100)

        # 풍부한 콘텐츠
        rich_content = (
            "## FAQ\n"
            "Q: 테스트란?\n"
            "A: 소프트웨어 검증 과정입니다.\n"
            "1. 첫 번째 항목\n"
            "2. 두 번째 항목\n"
            "3. 세 번째 항목\n"
            "| A | B |\n"
            "| --- | --- |\n"
        )
        result2 = analyze_serp_features(rich_content)
        self.assertGreaterEqual(result2["overall_serp_score"], 0)
        self.assertLessEqual(result2["overall_serp_score"], 100)

    # ── 10. best_opportunity 반환 검증 ──
    def test_best_opportunity(self):
        """best_opportunity는 가장 높은 readiness를 가진 feature를 반환한다."""
        # 테이블이 확실히 우세한 콘텐츠
        content = (
            "## 가격 비교표\n"
            "| 제품 | 가격 | 스펙 |\n"
            "| --- | --- | --- |\n"
            "| A | 10000 | 좋음 |\n"
            "| B | 20000 | 매우 좋음 |\n"
        )
        result = analyze_serp_features(content)
        self.assertEqual(result["best_opportunity"], "table_snippet")

    # ── 11. content_format_analysis 불리언 검증 ──
    def test_content_format_analysis(self):
        """content_format_analysis에 올바른 불리언 값이 반환된다."""
        content = (
            "머신러닝이란 데이터를 학습하는 인공지능의 한 분야를 의미한다.\n"
            "1. 첫 번째\n"
            "2. 두 번째\n"
            "| A | B |\n"
            "| --- | --- |\n"
            "1단계: 설치\n"
            "## FAQ\n"
            "Q: 무엇?\n"
            "A: 답변.\n"
            "방법을 알아봅시다.\n"
        )
        result = analyze_serp_features(content)
        fmt = result["content_format_analysis"]

        self.assertIsInstance(fmt["has_definition"], bool)
        self.assertTrue(fmt["has_definition"])
        self.assertTrue(fmt["has_lists"])
        self.assertTrue(fmt["has_tables"])
        self.assertTrue(fmt["has_steps"])
        self.assertTrue(fmt["has_faq"])
        self.assertTrue(fmt["has_how_to"])

    # ── 12. probability 레벨 검증 ──
    def test_probability_levels(self):
        """probability는 항상 high/medium/low 중 하나이다."""
        content = "간단한 텍스트. 구조가 없습니다."
        result = analyze_serp_features(content)

        valid_levels = {"high", "medium", "low"}
        for opp in result["opportunities"]:
            self.assertIn(opp["probability"], valid_levels)

    # ── 13. suggestions 제안 목록 검증 ──
    def test_suggestions(self):
        """suggestions는 비어 있지 않은 문자열 리스트이다."""
        # 구조가 부족한 콘텐츠 → 개선 제안이 나와야 함
        content = "아무런 구조가 없는 평범한 텍스트입니다."
        result = analyze_serp_features(content)

        self.assertIsInstance(result["suggestions"], list)
        self.assertTrue(len(result["suggestions"]) > 0)
        for suggestion in result["suggestions"]:
            self.assertIsInstance(suggestion, str)
            self.assertTrue(len(suggestion) > 0)

        # 풍부한 콘텐츠도 제안을 반환해야 함
        rich_content = (
            "## 가이드 방법 튜토리얼\n"
            "1단계: 설치합니다. 다운로드 후 실행하세요.\n"
            "2단계: 설정합니다. 환경을 구성하세요.\n"
        )
        result2 = analyze_serp_features(rich_content)
        self.assertIsInstance(result2["suggestions"], list)
        self.assertTrue(len(result2["suggestions"]) > 0)


if __name__ == "__main__":
    unittest.main()
