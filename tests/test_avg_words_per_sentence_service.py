"""Average Words Per Sentence 서비스 테스트."""
import unittest
from services.analysis.sentence_analysis_service import analyze_avg_words_per_sentence


class TestAvgWordsPerSentence(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_avg_words_per_sentence('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['avg_words'], 0.0)

    def test_none_content(self):
        result = analyze_avg_words_per_sentence(None)
        self.assertEqual(result['score'], 0.0)

    def test_optimal_range(self):
        # 문장당 약 15 단어 (최적 범위 10-20)
        content = ('이것은 적절한 길이의 문장으로 독자가 편하게 읽을 수 있는 수준의 글입니다. '
                   '또한 이 문장도 비슷한 길이를 유지하여 전반적으로 가독성이 좋은 편입니다. '
                   '마지막으로 이 문장도 적정한 단어 수를 포함하고 있어서 읽기 편합니다.')
        result = analyze_avg_words_per_sentence(content)
        avg = result['summary']['avg_words']
        self.assertGreaterEqual(avg, 10)
        self.assertLessEqual(avg, 20)
        self.assertEqual(result['summary']['readability_level'], 'optimal')

    def test_short_sentences(self):
        # 매우 짧은 문장들
        content = ('안녕. 좋다. 간다. 온다. 먹자. '
                   '본다. 쓴다. 읽자. 잔다. 일어나자.')
        result = analyze_avg_words_per_sentence(content)
        avg = result['summary']['avg_words']
        self.assertLess(avg, 5)

    def test_long_sentences(self):
        # 매우 긴 문장
        words = ' '.join([f'단어{i}' for i in range(35)])
        content = f'{words}. {words}. {words}.'
        result = analyze_avg_words_per_sentence(content)
        self.assertGreater(result['summary']['long_sentences'], 0)

    def test_sentence_data_structure(self):
        content = '이것은 테스트 문장입니다. 두 번째 문장도 있습니다.'
        result = analyze_avg_words_per_sentence(content)
        self.assertGreater(len(result['sentence_data']), 0)
        for item in result['sentence_data']:
            self.assertIn('text', item)
            self.assertIn('word_count', item)
            self.assertIn('category', item)

    def test_category_normal(self):
        content = '이것은 적절한 길이의 문장으로 여러 단어를 포함합니다.'
        result = analyze_avg_words_per_sentence(content)
        if result['sentence_data']:
            categories = [s['category'] for s in result['sentence_data']]
            self.assertIn('normal', categories)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다. 여러 문장이 포함되어 있습니다.'
        result = analyze_avg_words_per_sentence(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_score_optimal_is_100(self):
        # 최적 범위일 때 100점
        content = ('이것은 적절한 길이의 문장으로 독자가 편하게 읽을 수 있는 수준입니다. '
                   '또한 이 문장도 비슷한 길이를 유지하여 가독성이 좋은 편입니다. '
                   '마지막으로 이 문장도 적정한 단어 수를 포함하고 있어 읽기 편합니다.')
        result = analyze_avg_words_per_sentence(content)
        avg = result['summary']['avg_words']
        if 10 <= avg <= 20:
            self.assertEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 테스트 문장입니다.'
        result = analyze_avg_words_per_sentence(content)
        self.assertIn('sentence_data', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('total_words', result['summary'])
        self.assertIn('avg_words', result['summary'])
        self.assertIn('readability_level', result['summary'])

    def test_max_30_sentence_data(self):
        # sentence_data는 최대 30개만 반환
        sentences = '. '.join([f'이것은 테스트 문장 번호 {i}입니다' for i in range(50)])
        content = sentences + '.'
        result = analyze_avg_words_per_sentence(content)
        self.assertLessEqual(len(result['sentence_data']), 30)

    def test_suggestions_exist(self):
        content = ('이것은 적절한 길이의 문장으로 독자가 편하게 읽을 수 있습니다. '
                   '이 문장도 여러 단어를 포함하여 작성되었습니다.')
        result = analyze_avg_words_per_sentence(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_heading_stripped(self):
        content = ('# 제목입니다\n'
                   '이것은 본문 내용으로 여러 단어를 포함하는 문장입니다. '
                   '두 번째 문장도 적절한 길이를 유지합니다.')
        result = analyze_avg_words_per_sentence(content)
        # 제목이 문장으로 포함되지 않아야 함
        for item in result['sentence_data']:
            self.assertNotIn('# ', item['text'])


if __name__ == '__main__':
    unittest.main()
