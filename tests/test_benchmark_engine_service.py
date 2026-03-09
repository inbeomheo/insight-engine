"""
벤치마크 엔진 서비스 단위 테스트
"""
import unittest
from services.benchmark_engine_service import (
    benchmark_against,
    BenchmarkScore,
    DEFAULT_RUBRIC,
    _score_length,
    _score_structure,
    _score_readability,
    _score_engagement,
    _assign_grade,
)


class TestBenchmarkEngineService(unittest.TestCase):
    """benchmark_against 함수 단위 테스트"""

    def test_basic_benchmark(self):
        """기본 벤치마크 채점"""
        content = """## 제목

이것은 테스트 콘텐츠입니다. 여러 문장이 포함되어 있습니다.

### 소제목

- 항목 1
- 항목 2
- 항목 3

본문 내용이 여기에 들어갑니다. **강조** 표현도 있습니다.

질문이 있으신가요? 댓글로 남겨주세요!
"""
        result = benchmark_against(content, content_id="test_1")
        self.assertIsInstance(result, BenchmarkScore)
        self.assertEqual(result.content_id, "test_1")
        self.assertGreater(result.overall, 0)
        self.assertIn(result.grade, ["A+", "A", "B+", "B", "C+", "C", "D", "F"])
        self.assertTrue(len(result.scores) > 0)

    def test_empty_content(self):
        """빈 콘텐츠 — F 등급"""
        result = benchmark_against("")
        self.assertEqual(result.overall, 0.0)
        self.assertEqual(result.grade, "F")
        self.assertIn("콘텐츠가 비어 있습니다", result.recommendations)

    def test_whitespace_content(self):
        """공백만 있는 콘텐츠"""
        result = benchmark_against("   \n  \t  ")
        self.assertEqual(result.grade, "F")

    def test_score_length_short(self):
        """짧은 글 길이 점수"""
        self.assertEqual(_score_length("짧은"), 20.0)

    def test_score_length_optimal(self):
        """최적 길이 점수"""
        text = "가" * 2000
        self.assertEqual(_score_length(text), 100.0)

    def test_score_length_long(self):
        """긴 글 길이 점수"""
        text = "가" * 6000
        self.assertEqual(_score_length(text), 60.0)

    def test_score_structure_with_headings(self):
        """구조 점수 — 헤딩 포함"""
        text = "## 제목1\n\n내용\n\n## 제목2\n\n내용\n\n## 제목3\n\n내용"
        score = _score_structure(text)
        self.assertGreater(score, 40)

    def test_score_structure_flat(self):
        """구조 점수 — 구조 없는 평문"""
        text = "평범한 텍스트입니다"
        score = _score_structure(text)
        self.assertLess(score, 50)

    def test_score_readability_optimal(self):
        """가독성 — 적정 문장 길이"""
        # 평균 ~30자 문장
        text = "이것은 적정 길이의 문장입니다. 이 정도 길이가 읽기 좋습니다. 가독성이 높은 글을 씁시다."
        score = _score_readability(text)
        self.assertGreaterEqual(score, 70)

    def test_score_engagement_with_questions(self):
        """인게이지먼트 — 질문 포함"""
        text = "어떻게 생각하시나요? 궁금하지 않으신가요? **구독** 부탁드립니다!"
        score = _score_engagement(text)
        self.assertGreater(score, 30)

    def test_assign_grade(self):
        """등급 할당"""
        self.assertEqual(_assign_grade(95), "A+")
        self.assertEqual(_assign_grade(85), "A")
        self.assertEqual(_assign_grade(75), "B+")
        self.assertEqual(_assign_grade(65), "B")
        self.assertEqual(_assign_grade(55), "C+")
        self.assertEqual(_assign_grade(45), "C")
        self.assertEqual(_assign_grade(35), "D")
        self.assertEqual(_assign_grade(20), "F")

    def test_custom_rubric(self):
        """커스텀 루브릭 사용"""
        custom = {
            "length": {"weight": 0.5, "description": "길이"},
            "readability": {"weight": 0.5, "description": "가독성"},
        }
        text = "가" * 2000  # 최적 길이
        result = benchmark_against(text, rubric=custom, content_id="custom")
        self.assertEqual(len(result.scores), 2)
        self.assertIn("length", result.scores)
        self.assertIn("readability", result.scores)

    def test_recommendations_for_low_scores(self):
        """낮은 점수 항목에 대한 추천 생성"""
        # 매우 짧고 구조 없는 텍스트
        result = benchmark_against("짧음")
        self.assertTrue(len(result.recommendations) > 0)

    def test_default_rubric_weights_sum(self):
        """기본 루브릭 가중치 합 = 1.0"""
        total = sum(v["weight"] for v in DEFAULT_RUBRIC.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_content_id_default(self):
        """content_id 기본값은 빈 문자열"""
        result = benchmark_against("테스트 콘텐츠입니다")
        self.assertEqual(result.content_id, "")


if __name__ == '__main__':
    unittest.main()
