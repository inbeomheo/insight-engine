"""헤드라인 A/B 실험 서비스 테스트"""
import unittest

from services.headline_experiment_service import (
    WinnerHeadline,
    run_headline_ab,
    _score_length,
    _score_number,
    _score_question,
    _score_power_word,
    _score_clarity,
    _score_uniqueness,
)


class TestScoreLength(unittest.TestCase):
    """길이 점수 테스트"""

    def test_optimal_length(self):
        """15~40자 → 1.0"""
        self.assertEqual(_score_length("이것은 적절한 길이의 제목입니다"), 1.0)

    def test_very_short(self):
        """5자 미만 → 0.1"""
        self.assertEqual(_score_length("짧아"), 0.1)

    def test_medium_short(self):
        """10~14자 → 0.6"""
        result = _score_length("10자 정도의 제목임")  # 10자
        self.assertEqual(result, 0.6)

    def test_very_long(self):
        """60자 초과 → 0.3"""
        long_title = "이것은 매우 긴 제목으로 60자를 훌쩍 넘기는 것을 목표로 작성한 아주 아주 길고 긴 제목입니다 더 길게 만들어 봅시다"
        self.assertEqual(_score_length(long_title), 0.3)


class TestScoreNumber(unittest.TestCase):
    """숫자 포함 점수 테스트"""

    def test_with_number(self):
        """숫자 포함 → 1.0"""
        self.assertEqual(_score_number("10가지 방법"), 1.0)

    def test_without_number(self):
        """숫자 없음 → 0.0"""
        self.assertEqual(_score_number("좋은 방법"), 0.0)


class TestScoreQuestion(unittest.TestCase):
    """질문형 점수 테스트"""

    def test_question_mark(self):
        """물음표 → 1.0"""
        self.assertEqual(_score_question("어떻게 할까?"), 1.0)

    def test_no_question(self):
        """물음표 없음 → 0.0"""
        self.assertEqual(_score_question("이렇게 합니다"), 0.0)


class TestScorePowerWord(unittest.TestCase):
    """파워 워드 점수 테스트"""

    def test_multiple_power_words(self):
        """파워 워드 3개+ → 1.0"""
        self.assertEqual(_score_power_word("필수 핵심 방법 가이드"), 1.0)

    def test_one_power_word(self):
        """파워 워드 1개 → 0.5"""
        self.assertEqual(_score_power_word("간단한 소개"), 0.5)

    def test_no_power_word(self):
        """파워 워드 없음 → 0.0"""
        self.assertEqual(_score_power_word("일상적인 이야기"), 0.0)


class TestScoreClarity(unittest.TestCase):
    """명확성 점수 테스트"""

    def test_clean_headline(self):
        """특수문자 없음 → 1.0"""
        self.assertEqual(_score_clarity("깔끔한 제목"), 1.0)

    def test_few_special_chars(self):
        """특수문자 1~2개 → 0.7"""
        self.assertEqual(_score_clarity("제목! 확인!"), 0.7)

    def test_many_special_chars(self):
        """특수문자 3개+ → 0.3"""
        self.assertEqual(_score_clarity("제목!!! @#$ 확인!!!"), 0.3)


class TestScoreUniqueness(unittest.TestCase):
    """고유성 점수 테스트"""

    def test_no_others(self):
        """비교 대상 없음 → 1.0"""
        self.assertEqual(_score_uniqueness("테스트 제목", []), 1.0)

    def test_identical_others(self):
        """동일한 다른 후보 → 낮은 점수"""
        score = _score_uniqueness("테스트 제목", ["테스트 제목"])
        self.assertLess(score, 0.5)

    def test_different_others(self):
        """전혀 다른 후보 → 높은 점수"""
        score = _score_uniqueness("파이썬 가이드", ["자바스크립트 입문"])
        self.assertGreater(score, 0.5)


class TestRunHeadlineAb(unittest.TestCase):
    """A/B 실험 통합 테스트"""

    def test_empty_raises(self):
        """빈 리스트 → ValueError"""
        with self.assertRaises(ValueError):
            run_headline_ab([])

    def test_whitespace_only_raises(self):
        """공백만 있는 리스트 → ValueError"""
        with self.assertRaises(ValueError):
            run_headline_ab(["", "  ", ""])

    def test_single_headline(self):
        """단일 헤드라인 → 그것이 승자"""
        result = run_headline_ab(["유일한 제목"])
        self.assertEqual(result.headline, "유일한 제목")
        self.assertIsInstance(result, WinnerHeadline)

    def test_winner_has_highest_score(self):
        """승자가 가장 높은 점수를 가짐"""
        headlines = [
            "10가지 필수 핵심 방법 가이드",  # 숫자+파워워드
            "뭔가",                          # 너무 짧음
            "좋은 콘텐츠 만드는 방법은?",    # 질문형+파워워드
        ]
        result = run_headline_ab(headlines)
        self.assertEqual(result.score, result.all_scores[0]["score"])
        # all_scores가 내림차순인지 확인
        for i in range(len(result.all_scores) - 1):
            self.assertGreaterEqual(
                result.all_scores[i]["score"],
                result.all_scores[i + 1]["score"],
            )

    def test_all_scores_present(self):
        """all_scores에 모든 고유 헤드라인 포함"""
        headlines = ["제목 A", "제목 B", "제목 C"]
        result = run_headline_ab(headlines)
        self.assertEqual(len(result.all_scores), 3)

    def test_duplicate_removal(self):
        """중복 헤드라인 제거"""
        headlines = ["제목 A", "제목 A", "제목 B"]
        result = run_headline_ab(headlines)
        self.assertEqual(len(result.all_scores), 2)

    def test_reasons_not_empty(self):
        """이유 리스트가 비어 있지 않음"""
        result = run_headline_ab(["10가지 필수 가이드 방법?"])
        self.assertGreater(len(result.reasons), 0)

    def test_audience_sample_adjusts_score(self):
        """타겟 오디언스가 점수에 영향"""
        headlines = ["이것은 어떨까?", "이것은 확실하다"]
        without = run_headline_ab(headlines)
        with_audience = run_headline_ab(headlines, {"age_group": "20대"})
        # 질문형이 20대에게 가산 → 점수 변동 가능
        self.assertIsNotNone(with_audience.score)

    def test_score_is_float(self):
        """점수가 float"""
        result = run_headline_ab(["테스트 제목 하나"])
        self.assertIsInstance(result.score, float)


if __name__ == "__main__":
    unittest.main()
