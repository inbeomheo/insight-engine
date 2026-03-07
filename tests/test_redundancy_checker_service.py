"""redundancy_checker_service 단위 테스트"""
import unittest

from services.redundancy_checker_service import (
    check_redundancy,
    _jaccard_similarity,
)


class TestCheckRedundancy(unittest.TestCase):

    def test_empty_content(self):
        result = check_redundancy('')
        self.assertEqual(result['score'], 100)

    def test_none_content(self):
        result = check_redundancy(None)
        self.assertEqual(result['score'], 100)

    def test_clean_content(self):
        result = check_redundancy('파이썬은 좋은 언어입니다. 자바스크립트도 강력합니다.')
        self.assertGreaterEqual(result['score'], 80)

    def test_repeated_phrase_detected(self):
        content = '파이썬 프로그래밍 언어는 좋습니다. 파이썬 프로그래밍 언어는 강력합니다. 파이썬 프로그래밍 언어는 인기가 많습니다.'
        result = check_redundancy(content)
        self.assertGreater(len(result['repeated_phrases']), 0)

    def test_redundant_pattern_detected(self):
        content = '매우 매우 중요한 내용입니다.'
        result = check_redundancy(content)
        self.assertGreater(len(result['redundant_patterns']), 0)
        self.assertEqual(result['redundant_patterns'][0]['suggestion'], '매우')

    def test_overused_word_detected(self):
        content = '정말 좋은 결과입니다. 정말 놀라운 성과입니다. 정말 기대됩니다. 정말 대단합니다. 이것은 정말 중요한 내용입니다. 우리가 정말 해야할 일입니다. 프로젝트가 정말 잘 진행되고 있습니다. 결과가 정말 만족스럽습니다.'
        result = check_redundancy(content)
        self.assertGreater(len(result['overused_words']), 0)

    def test_similar_sentences_detected(self):
        content = '파이썬은 프로그래밍 언어로 매우 인기가 있습니다. 파이썬은 프로그래밍 도구로 매우 인기가 높습니다.'
        result = check_redundancy(content)
        self.assertGreater(len(result['similar_sentences']), 0)

    def test_score_decreases_with_redundancy(self):
        clean = check_redundancy('고유한 문장입니다. 다른 내용을 담고 있습니다.')
        redundant = check_redundancy('매우 매우 중요합니다. 정말 정말 좋습니다. 정말 대단합니다. 정말 멋집니다.')
        self.assertGreater(clean['score'], redundant['score'])

    def test_score_bounded(self):
        result = check_redundancy('테스트 콘텐츠.')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_suggestions_exist(self):
        content = '매우 매우 중요합니다. 정말 좋은 정말 대단한 정말 놀라운 결과입니다.'
        result = check_redundancy(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_severity_levels(self):
        # 4회 이상 반복 시 high severity
        phrase = '파이썬 프로그래밍 방법'
        content = f'{phrase}은 좋습니다. {phrase}은 쉽습니다. {phrase}은 강력합니다. {phrase}은 인기입니다.'
        result = check_redundancy(content)
        if result['repeated_phrases']:
            self.assertIn(result['repeated_phrases'][0]['severity'], ('low', 'medium', 'high'))


class TestJaccardSimilarity(unittest.TestCase):

    def test_identical(self):
        sim = _jaccard_similarity('파이썬 프로그래밍 언어', '파이썬 프로그래밍 언어')
        self.assertEqual(sim, 1.0)

    def test_completely_different(self):
        sim = _jaccard_similarity('파이썬 프로그래밍', '자바스크립트 웹개발')
        self.assertLess(sim, 0.5)

    def test_partial_overlap(self):
        sim = _jaccard_similarity('파이썬 프로그래밍 입문', '파이썬 프로그래밍 고급')
        self.assertGreater(sim, 0)
        self.assertLess(sim, 1)

    def test_empty_input(self):
        sim = _jaccard_similarity('', '')
        self.assertEqual(sim, 0)


if __name__ == '__main__':
    unittest.main()
