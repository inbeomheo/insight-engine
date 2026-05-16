"""word_repetition_service 단위 테스트"""
import unittest

from services.content.word_repetition_service import (
    detect_repetitions,
    _get_suggestions,
)


class TestDetectRepetitions(unittest.TestCase):

    def test_empty_content(self):
        result = detect_repetitions('')
        self.assertEqual(result['total_words'], 0)
        self.assertEqual(result['repetitions'], [])

    def test_none_content(self):
        result = detect_repetitions(None)
        self.assertEqual(result['total_words'], 0)

    def test_repeated_word_detected(self):
        text = '인공지능은 중요합니다. 인공지능은 미래입니다. 인공지능은 발전합니다. 인공지능은 핵심입니다.'
        result = detect_repetitions(text, threshold=3)
        words = [r['word'] for r in result['repetitions']]
        # 한국어 형태소 분리 없이 "인공지능은"이 하나의 단어로 추출됨
        self.assertTrue(any('인공지능' in w for w in words))

    def test_threshold_filtering(self):
        text = '단어A 단어B 단어A 단어B 단어A'
        result_low = detect_repetitions(text, threshold=2)
        result_high = detect_repetitions(text, threshold=4)
        self.assertGreaterEqual(len(result_low['repetitions']), len(result_high['repetitions']))

    def test_stopwords_excluded(self):
        text = '그리고 하지만 그리고 하지만 그리고 하지만 그리고'
        result = detect_repetitions(text, threshold=2)
        words = [r['word'] for r in result['repetitions']]
        self.assertNotIn('그리고', words)
        self.assertNotIn('하지만', words)

    def test_vocabulary_richness(self):
        text = '다양한 단어로 구성된 풍부한 어휘를 사용하는 텍스트입니다.'
        result = detect_repetitions(text)
        self.assertGreater(result['vocabulary_richness'], 0)
        self.assertLessEqual(result['vocabulary_richness'], 1.0)

    def test_density_calculated(self):
        text = '반복 반복 반복 다른단어 또다른단어'
        result = detect_repetitions(text, threshold=2)
        if result['repetitions']:
            self.assertGreater(result['repetitions'][0]['density'], 0)

    def test_unique_words_count(self):
        text = '하나 둘 셋 넷 다섯'
        result = detect_repetitions(text)
        self.assertGreater(result['unique_words'], 0)
        self.assertLessEqual(result['unique_words'], result['total_words'])

    def test_suggestions_included(self):
        text = '중요한 내용입니다. 중요한 포인트입니다. 중요한 결론입니다.'
        result = detect_repetitions(text, threshold=2)
        for rep in result['repetitions']:
            if '중요' in rep['word']:
                self.assertIsInstance(rep['suggestions'], list)

    def test_english_words(self):
        text = 'machine learning machine learning machine learning test'
        result = detect_repetitions(text, threshold=2)
        words = [r['word'] for r in result['repetitions']]
        self.assertTrue(any('machine' in w for w in words))


class TestGetSuggestions(unittest.TestCase):

    def test_exact_match(self):
        suggestions = _get_suggestions('중요')
        self.assertGreater(len(suggestions), 0)

    def test_no_match(self):
        suggestions = _get_suggestions('비행기')
        self.assertIsInstance(suggestions, list)

    def test_synonym_quality(self):
        suggestions = _get_suggestions('사용')
        self.assertIn('활용', suggestions)


if __name__ == '__main__':
    unittest.main()
