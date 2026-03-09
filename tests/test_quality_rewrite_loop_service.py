"""품질 심사-재작성 루프 서비스 테스트"""
import unittest
from services.quality_rewrite_loop_service import (
    run_quality_loop,
    evaluate_content,
    QualityResult,
    QualityCriteria,
    RewriteIteration,
    _score_readability,
    _score_seo,
    _score_paragraph_count,
    _score_keyword_density,
    _split_long_sentences,
    _add_structure,
    _split_paragraphs,
    _reduce_repetition,
    _check_passed,
)


class TestScoreReadability(unittest.TestCase):
    """가독성 점수 평가 테스트"""

    def test_short_sentences_high_score(self):
        """짧은 문장은 높은 가독성 점수를 받는다"""
        content = "짧은 문장. 또 하나. 세 번째."
        score = _score_readability(content)
        self.assertGreaterEqual(score, 80)

    def test_long_sentences_low_score(self):
        """긴 문장은 낮은 가독성 점수를 받는다"""
        content = "이것은 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 매우 긴 문장입니다 정말로 끝이 없을 정도로 아주 길게 계속 이어지는 문장이라서 읽기가 어렵습니다"
        score = _score_readability(content)
        self.assertLessEqual(score, 50)

    def test_empty_content_zero(self):
        """빈 콘텐츠는 0점"""
        self.assertEqual(_score_readability(""), 0)

    def test_whitespace_only_zero(self):
        """공백만 있는 콘텐츠는 0점"""
        self.assertEqual(_score_readability("   \n  "), 0)


class TestScoreSeo(unittest.TestCase):
    """SEO 점수 평가 테스트"""

    def test_with_headings_and_lists(self):
        """제목과 리스트가 있으면 높은 점수"""
        content = "## 제목\n\n- 항목 1\n- 항목 2\n\n### 소제목\n\n[링크](http://example.com)"
        score = _score_seo(content)
        self.assertGreaterEqual(score, 50)

    def test_plain_text_low_score(self):
        """구조 없는 평문은 낮은 점수"""
        content = "이것은 아무 구조도 없는 평범한 텍스트입니다."
        score = _score_seo(content)
        self.assertEqual(score, 0)

    def test_max_capped_at_100(self):
        """점수 최대 100 제한"""
        content = "\n".join(f"## 제목{i}\n- 항목\n[링크](http://a.com)" for i in range(20))
        score = _score_seo(content)
        self.assertLessEqual(score, 100)


class TestScoreParagraphCount(unittest.TestCase):
    """문단 수 점수 테스트"""

    def test_three_or_more_paragraphs(self):
        """3개 이상 문단이면 100점"""
        content = "첫 문단.\n\n두 번째 문단.\n\n세 번째 문단."
        self.assertEqual(_score_paragraph_count(content), 100)

    def test_two_paragraphs(self):
        """2개 문단이면 60점"""
        content = "첫 문단.\n\n두 번째 문단."
        self.assertEqual(_score_paragraph_count(content), 60)

    def test_one_paragraph(self):
        """1개 문단이면 30점"""
        content = "단일 문단입니다."
        self.assertEqual(_score_paragraph_count(content), 30)

    def test_empty_zero(self):
        """빈 콘텐츠는 0점"""
        self.assertEqual(_score_paragraph_count(""), 0)


class TestScoreKeywordDensity(unittest.TestCase):
    """키워드 밀도 점수 테스트"""

    def test_diverse_words_high_score(self):
        """다양한 단어를 사용하면 높은 점수"""
        content = "사과 바나나 포도 딸기 수박 키위 망고 복숭아 자두 체리"
        score = _score_keyword_density(content)
        self.assertGreaterEqual(score, 80)

    def test_repetitive_words_low_score(self):
        """같은 단어 반복이면 낮은 점수"""
        content = " ".join(["반복"] * 50)
        score = _score_keyword_density(content)
        self.assertLessEqual(score, 20)

    def test_empty_zero(self):
        """빈 콘텐츠는 0점"""
        self.assertEqual(_score_keyword_density(""), 0)


class TestEvaluateContent(unittest.TestCase):
    """통합 평가 함수 테스트"""

    def test_returns_all_criteria_scores(self):
        """criteria에 있는 모든 필드의 점수를 반환"""
        criteria = {"readability": 70, "seo_score": 50}
        scores = evaluate_content("## 제목\n\n짧은 문장.", criteria)
        self.assertIn("readability", scores)
        self.assertIn("seo_score", scores)

    def test_unknown_field_returns_zero(self):
        """알 수 없는 필드는 0점"""
        scores = evaluate_content("텍스트", {"unknown_metric": 50})
        self.assertEqual(scores["unknown_metric"], 0)


class TestCheckPassed(unittest.TestCase):
    """기준 충족 확인 테스트"""

    def test_all_pass(self):
        """모든 점수가 기준 이상이면 True"""
        self.assertTrue(_check_passed({"readability": 80, "seo_score": 70}, {"readability": 70, "seo_score": 60}))

    def test_one_fails(self):
        """하나라도 미달이면 False"""
        self.assertFalse(_check_passed({"readability": 50, "seo_score": 70}, {"readability": 70, "seo_score": 60}))


class TestRewriteTransforms(unittest.TestCase):
    """규칙 기반 재작성 변환 테스트"""

    def test_add_structure_adds_heading(self):
        """제목이 없으면 첫 줄에 ## 추가"""
        content = "제목이 될 줄\n\n본문 내용"
        result = _add_structure(content)
        self.assertTrue(result.startswith("## "))

    def test_add_structure_no_change_if_heading_exists(self):
        """이미 제목이 있으면 변경 없음"""
        content = "## 기존 제목\n\n본문"
        result = _add_structure(content)
        self.assertEqual(result, content)

    def test_reduce_repetition(self):
        """연속 중복 단어 제거"""
        content = "매우 매우 좋은 좋은 결과"
        result = _reduce_repetition(content)
        self.assertIn("매우", result)
        # 연속 중복이 제거됨
        self.assertNotIn("매우 매우", result)


class TestRunQualityLoop(unittest.TestCase):
    """메인 품질 루프 테스트"""

    def test_already_passing_content_returns_immediately(self):
        """이미 기준을 충족하는 콘텐츠는 1회 반복으로 즉시 반환"""
        content = "## 제목\n\n짧은 문장.\n\n두 번째 문단.\n\n- 리스트 항목\n\n사과 바나나 포도 딸기 수박"
        criteria = {"readability": 50, "paragraph_count": 50}
        result = run_quality_loop(content, criteria, max_iterations=3)
        self.assertTrue(result.passed)
        self.assertEqual(result.iterations_run, 1)

    def test_max_iterations_reached(self):
        """기준 미달 시 최대 반복까지 실행"""
        # SEO 점수를 높게 요구하여 통과 불가능하게 설정
        content = "구조 없는 평문 텍스트"
        criteria = {"seo_score": 100}
        result = run_quality_loop(content, criteria, max_iterations=2)
        self.assertEqual(result.iterations_run, 2)
        # seo_score 100은 달성 불가능 → passed=False
        self.assertFalse(result.passed)

    def test_returns_best_score_version(self):
        """최대 반복 후 최고 점수 버전을 반환"""
        content = "텍스트"
        criteria = {"readability": 100}  # 달성 불가능
        result = run_quality_loop(content, criteria, max_iterations=3)
        self.assertGreater(result.best_score, 0)
        self.assertIsNotNone(result.final_content)

    def test_result_has_iterations_history(self):
        """결과에 반복 이력이 포함됨"""
        # seo_score 100은 달성 불가능 → 최대 반복까지 실행
        content = "구조 없는 평문 텍스트"
        criteria = {"seo_score": 100}
        result = run_quality_loop(content, criteria, max_iterations=2)
        self.assertEqual(len(result.iterations), 2)
        self.assertIsInstance(result.iterations[0], RewriteIteration)

    def test_result_id_is_generated(self):
        """결과에 고유 ID가 생성됨"""
        result = run_quality_loop("텍스트", {"readability": 50}, max_iterations=1)
        self.assertIsNotNone(result.result_id)
        self.assertGreater(len(result.result_id), 0)

    def test_criteria_used_recorded(self):
        """사용된 기준이 결과에 기록됨"""
        criteria = {"readability": 70, "seo_score": 60}
        result = run_quality_loop("텍스트", criteria, max_iterations=1)
        self.assertEqual(result.criteria_used, criteria)

    def test_empty_content_raises(self):
        """빈 콘텐츠는 ValueError"""
        with self.assertRaises(ValueError):
            run_quality_loop("", {"readability": 70})

    def test_empty_criteria_raises(self):
        """빈 criteria는 ValueError"""
        with self.assertRaises(ValueError):
            run_quality_loop("텍스트", {})

    def test_invalid_max_iterations_raises(self):
        """max_iterations 범위 초과 시 ValueError"""
        with self.assertRaises(ValueError):
            run_quality_loop("텍스트", {"readability": 70}, max_iterations=0)
        with self.assertRaises(ValueError):
            run_quality_loop("텍스트", {"readability": 70}, max_iterations=11)

    def test_iteration_scores_are_dicts(self):
        """각 반복의 scores가 dict 형태"""
        result = run_quality_loop("내용", {"readability": 100}, max_iterations=1)
        self.assertIsInstance(result.iterations[0].scores, dict)
        self.assertIn("readability", result.iterations[0].scores)

    def test_improvement_across_iterations(self):
        """재작성 후 점수가 개선되거나 유지됨 (악화되지 않음)"""
        # 구조 없는 긴 텍스트 → seo_score 재작성으로 개선 기대
        long_text = "이것은 아주 긴 본문입니다. " * 20
        criteria = {"seo_score": 30}
        result = run_quality_loop(long_text, criteria, max_iterations=3)
        if len(result.iterations) >= 2:
            # 첫 번째보다 두 번째가 같거나 나은 점수
            first_seo = result.iterations[0].scores.get("seo_score", 0)
            second_seo = result.iterations[1].scores.get("seo_score", 0)
            self.assertGreaterEqual(second_seo, first_seo)

    def test_dataclass_defaults(self):
        """QualityResult dataclass 기본값 확인"""
        r = QualityResult()
        self.assertEqual(r.final_content, "")
        self.assertEqual(r.best_score, 0)
        self.assertEqual(r.iterations_run, 0)
        self.assertFalse(r.passed)
        self.assertEqual(r.iterations, [])

    def test_quality_criteria_defaults(self):
        """QualityCriteria dataclass 기본값 확인"""
        c = QualityCriteria()
        self.assertEqual(c.readability, 70)
        self.assertEqual(c.seo_score, 60)
        self.assertEqual(c.paragraph_count, 50)
        self.assertEqual(c.keyword_density, 50)


if __name__ == '__main__':
    unittest.main()
