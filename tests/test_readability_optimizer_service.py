"""readability_optimizer_service 단위 테스트"""
import unittest

from services.content.readability_optimizer_service import (
    analyze_readability,
    get_readability_levels,
    SUPPORTED_LEVELS,
    _calculate_score,
    _generate_suggestions,
    _split_sentences,
    _count_chars_no_space,
)


class TestAnalyzeReadability(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_readability('')
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = analyze_readability(None)
        self.assertEqual(result['score'], 0.0)

    def test_simple_text(self):
        text = '짧은 문장입니다. 읽기 쉽습니다. 간결합니다.'
        result = analyze_readability(text)
        self.assertIn(result['level'], SUPPORTED_LEVELS)
        self.assertGreater(result['score'], 0.5)

    def test_complex_text(self):
        text = ('이 문장은 매우 복잡하고 여러 가지 부연 설명이 포함되어 있으며 '
                '독자가 이해하기 어려울 수 있는 전문 용어와 긴 절이 반복되는 '
                '형태로 구성되어 있는 것으로 판단되는 것이 일반적인 견해이다.')
        result = analyze_readability(text)
        self.assertLessEqual(result['score'], 0.8)

    def test_long_sentences_detected(self):
        long_sent = '아' * 60 + '.'
        text = f'{long_sent} 짧은 문장입니다.'
        result = analyze_readability(text)
        self.assertGreater(len(result['long_sentences']), 0)

    def test_complex_expressions_detected(self):
        text = '이 기능에 있어서 여러 문제가 발생하는 것으로 나타났다. 조치를 실시하다 보면 해결할 필요가 있다.'
        result = analyze_readability(text)
        # _SIMPLIFICATION_MAP의 키가 텍스트에 포함되어야 함
        # '~에 있어서' 패턴 감지
        found = any(
            '있어서' in e['original']
            for e in result['complex_expressions']
        )
        self.assertTrue(found)

    def test_suggestions_generated(self):
        long_text = ('이 문장은 매우 길고 복잡한 구조를 가지고 있습니다. ' * 5 +
                     '짧은 문장입니다.')
        result = analyze_readability(long_text)
        self.assertGreater(len(result['suggestions']), 0)

    def test_good_text_positive_suggestion(self):
        text = '짧습니다. 간결합니다. 읽기 쉽습니다.'
        result = analyze_readability(text)
        if result['score'] >= 0.7:
            self.assertTrue(any('좋습니다' in s or '유지' in s for s in result['suggestions']))

    def test_paragraph_stats(self):
        text = '첫 문단 내용입니다.\n\n두 번째 문단 내용입니다.\n\n세 번째 문단입니다.'
        result = analyze_readability(text)
        self.assertGreaterEqual(result['paragraph_stats']['count'], 2)

    def test_avg_sentence_length(self):
        text = '10자짜리입니다. 20자짜리 문장을 만듭니다.'
        result = analyze_readability(text)
        self.assertGreater(result['avg_sentence_length'], 0)

    def test_long_sentences_max_10(self):
        long_sents = '. '.join(['아' * 60] * 15)
        result = analyze_readability(long_sents)
        self.assertLessEqual(len(result['long_sentences']), 10)

    def test_score_range(self):
        text = '일반적인 텍스트입니다.'
        result = analyze_readability(text)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 1.0)


class TestCalculateScore(unittest.TestCase):

    def test_short_sentences_high_score(self):
        score = _calculate_score(20, 0, 10, [])
        self.assertGreater(score, 0.7)

    def test_long_sentences_low_score(self):
        score = _calculate_score(70, 8, 10, [])
        self.assertLess(score, 0.5)

    def test_complex_expressions_penalty(self):
        score_clean = _calculate_score(30, 0, 10, [])
        score_complex = _calculate_score(30, 0, 10, [{'a': 'b'}] * 5)
        self.assertGreater(score_clean, score_complex)

    def test_score_bounds(self):
        score = _calculate_score(100, 100, 100, [{}] * 20)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestGenerateSuggestions(unittest.TestCase):

    def test_long_avg_suggestion(self):
        suggestions = _generate_suggestions(45, [], [], 3, 'standard')
        self.assertTrue(any('길' in s for s in suggestions))

    def test_long_sentence_suggestion(self):
        long = [{'text': 'x' * 60, 'length': 60, 'index': 0}]
        suggestions = _generate_suggestions(30, long, [], 3, 'standard')
        self.assertTrue(any('50자' in s or '초과' in s for s in suggestions))

    def test_no_issues(self):
        suggestions = _generate_suggestions(25, [], [], 3, 'easy')
        self.assertTrue(any('좋습니다' in s for s in suggestions))


class TestSplitSentences(unittest.TestCase):

    def test_basic(self):
        sents = _split_sentences('첫째. 둘째! 셋째?')
        self.assertEqual(len(sents), 3)

    def test_empty(self):
        self.assertEqual(_split_sentences(''), [])


class TestCountCharsNoSpace(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(_count_chars_no_space('a b c'), 3)

    def test_korean(self):
        self.assertEqual(_count_chars_no_space('한 글'), 2)


class TestGetReadabilityLevels(unittest.TestCase):

    def test_returns_all_levels(self):
        levels = get_readability_levels()
        self.assertEqual(len(levels), len(SUPPORTED_LEVELS))
        for level in levels:
            self.assertIn('id', level)
            self.assertIn('label', level)
            self.assertIn('description', level)


if __name__ == '__main__':
    unittest.main()
