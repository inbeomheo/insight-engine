"""headline_optimizer_service 단위 테스트"""
import unittest

from services.headline_optimizer_service import (
    optimize_headline,
    _score_length,
    _score_emotional,
    _score_power_words,
    _score_numbers,
    _detect_pattern,
)


class TestOptimizeHeadline(unittest.TestCase):

    def test_empty_title(self):
        result = optimize_headline('')
        self.assertEqual(result['grade'], 'F')
        self.assertEqual(result['score'], 0)
        self.assertIn('제목이 비어 있습니다.', result['suggestions'])

    def test_none_title(self):
        result = optimize_headline(None)
        self.assertEqual(result['grade'], 'F')

    def test_basic_title(self):
        result = optimize_headline('파이썬 시작하기')
        self.assertIsInstance(result['score'], int)
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D', 'F'))
        self.assertTrue(len(result['analysis']) > 0)

    def test_optimized_titles_generated(self):
        result = optimize_headline('인공지능의 미래')
        self.assertIsInstance(result['optimized_titles'], list)
        self.assertGreater(len(result['optimized_titles']), 0)

    def test_good_title_scores_higher(self):
        good = optimize_headline('10가지 필수 파이썬 팁 — 초보자 가이드')
        bad = optimize_headline('글')
        self.assertGreater(good['score'], bad['score'])

    def test_score_bounded(self):
        result = optimize_headline('테스트 제목입니다')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)


class TestScoreLength(unittest.TestCase):

    def test_optimal_length(self):
        # 15~30자 → 100점
        self.assertEqual(_score_length('이것은 최적 길이의 제목입니다 가이드'), 100)

    def test_too_short(self):
        self.assertLess(_score_length('짧은'), 100)

    def test_too_long(self):
        self.assertLess(_score_length('이것은 매우 매우 매우 매우 매우 매우 매우 매우 매우 긴 제목입니다'), 100)


class TestScoreEmotional(unittest.TestCase):

    def test_emotional_words_boost(self):
        score = _score_emotional('필수 핵심 비밀 가이드')
        self.assertGreater(score, 50)

    def test_no_emotional_words(self):
        score = _score_emotional('일반적인 제목')
        self.assertEqual(score, 30)


class TestScorePowerWords(unittest.TestCase):

    def test_power_words(self):
        score = _score_power_words('실전 가이드 꿀팁')
        self.assertGreater(score, 50)

    def test_no_power_words(self):
        score = _score_power_words('평범한 제목')
        self.assertEqual(score, 30)


class TestScoreNumbers(unittest.TestCase):

    def test_with_numbers(self):
        self.assertEqual(_score_numbers('10가지 방법'), 80)

    def test_without_numbers(self):
        self.assertEqual(_score_numbers('방법 정리'), 40)


class TestDetectPattern(unittest.TestCase):

    def test_question(self):
        self.assertEqual(_detect_pattern('왜 파이썬이 인기일까?'), 'question')

    def test_list(self):
        self.assertEqual(_detect_pattern('10가지 팁'), 'list')

    def test_how_to(self):
        self.assertEqual(_detect_pattern('블로그 시작하는 방법'), 'how_to')

    def test_comparison(self):
        self.assertEqual(_detect_pattern('React vs Vue 비교'), 'comparison')

    def test_statement(self):
        self.assertEqual(_detect_pattern('인공지능의 미래'), 'statement')


if __name__ == '__main__':
    unittest.main()
