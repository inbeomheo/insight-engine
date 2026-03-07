"""reading_time_service 단위 테스트"""
import unittest

from services.reading_time_service import (
    estimate_reading_time,
    _analyze_difficulty,
)


class TestEstimateReadingTime(unittest.TestCase):

    def test_empty_content(self):
        result = estimate_reading_time('')
        self.assertEqual(result['reading_time']['minutes'], 0)
        self.assertEqual(result['word_stats']['char_count'], 0)

    def test_none_content(self):
        result = estimate_reading_time(None)
        self.assertEqual(result['reading_time']['minutes'], 0)

    def test_short_content(self):
        result = estimate_reading_time('짧은 글입니다.')
        self.assertEqual(result['reading_time']['minutes'], 0)
        self.assertGreater(result['reading_time']['seconds'], 0)
        self.assertIn('초', result['reading_time']['display'])

    def test_medium_content(self):
        content = '한국어 콘텐츠 테스트 문장입니다. ' * 100  # ~2000자
        result = estimate_reading_time(content)
        self.assertGreater(result['reading_time']['minutes'], 0)
        self.assertIn('분', result['reading_time']['display'])

    def test_word_stats(self):
        content = '첫 번째 문장입니다. 두 번째 문장입니다.\n\n새 문단입니다.'
        result = estimate_reading_time(content)
        stats = result['word_stats']
        self.assertGreater(stats['char_count'], 0)
        self.assertGreater(stats['word_count'], 0)
        self.assertGreater(stats['sentence_count'], 0)
        self.assertGreater(stats['paragraph_count'], 0)

    def test_reading_range(self):
        content = '콘텐츠 ' * 200
        result = estimate_reading_time(content)
        self.assertIn('slow', result['reading_time']['range'])
        self.assertIn('fast', result['reading_time']['range'])

    def test_content_type_affects_time(self):
        content = '기술적 콘텐츠 테스트입니다. ' * 100
        general = estimate_reading_time(content, 'general')
        technical = estimate_reading_time(content, 'technical')
        # 기술 콘텐츠는 더 오래 걸림
        g_total = general['reading_time']['minutes'] * 60 + general['reading_time']['seconds']
        t_total = technical['reading_time']['minutes'] * 60 + technical['reading_time']['seconds']
        self.assertGreater(t_total, g_total)

    def test_invalid_type_defaults(self):
        result = estimate_reading_time('테스트', 'invalid')
        self.assertIsNotNone(result['reading_time'])

    def test_difficulty_included(self):
        result = estimate_reading_time('간단한 글입니다.')
        self.assertIn('level', result['difficulty'])
        self.assertIn('score', result['difficulty'])
        self.assertIn(result['difficulty']['level'], ('easy', 'medium', 'hard'))

    def test_recommendations(self):
        result = estimate_reading_time('짧음.')
        self.assertIsInstance(result['recommendations'], list)
        self.assertGreater(len(result['recommendations']), 0)


class TestAnalyzeDifficulty(unittest.TestCase):

    def test_easy_content(self):
        sentences = ['짧은 문장입니다', '쉬운 내용입니다']
        result = _analyze_difficulty('짧은 문장입니다 쉬운 내용입니다', sentences, 30)
        self.assertIn(result['level'], ('easy', 'medium'))

    def test_hard_content(self):
        text = 'This is a complex algorithmic implementation with O(n log n) complexity using Python. ' * 5
        sentences = [text]
        result = _analyze_difficulty(text, sentences, len(text))
        self.assertEqual(result['level'], 'hard')
        self.assertGreater(len(result['factors']), 0)

    def test_score_bounded(self):
        result = _analyze_difficulty('test', ['test'], 4)
        self.assertGreaterEqual(result['score'], 1)
        self.assertLessEqual(result['score'], 10)


if __name__ == '__main__':
    unittest.main()
