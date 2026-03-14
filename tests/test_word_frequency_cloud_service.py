"""Word Frequency Cloud Generator 서비스 테스트."""
import unittest
from services.media.word_frequency_cloud_service import generate_word_frequency


class TestWordFrequencyCloud(unittest.TestCase):

    def test_empty_content(self):
        result = generate_word_frequency('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_words'], 0)

    def test_none_content(self):
        result = generate_word_frequency(None)
        self.assertEqual(result['score'], 0.0)

    def test_korean_text(self):
        content = '인공지능 기술이 발전하고 있습니다. 인공지능 활용 사례가 늘고 있습니다. 데이터 분석이 중요합니다.'
        result = generate_word_frequency(content)
        self.assertGreater(len(result['word_cloud']), 0)
        self.assertEqual(result['summary']['dominant_language'], 'ko')

    def test_english_text(self):
        content = 'Artificial intelligence technology advances rapidly. Machine learning models improve accuracy. Deep learning enables complex tasks.'
        result = generate_word_frequency(content)
        self.assertGreater(len(result['word_cloud']), 0)
        self.assertEqual(result['summary']['dominant_language'], 'en')

    def test_word_cloud_structure(self):
        content = '테스트 데이터를 분석합니다. 테스트 결과를 확인합니다. 테스트 품질을 보장합니다.'
        result = generate_word_frequency(content)
        if result['word_cloud']:
            entry = result['word_cloud'][0]
            self.assertIn('word', entry)
            self.assertIn('count', entry)
            self.assertIn('frequency', entry)
            self.assertIn('weight', entry)

    def test_stopwords_filtered(self):
        content = '그리고 하지만 그러나 따라서 또는 그래서 있는 없는 하는 되는'
        result = generate_word_frequency(content)
        # 불용어만 있으면 결과 단어가 적어야 함
        self.assertEqual(len(result['word_cloud']), 0)

    def test_top_n_limit(self):
        words = [f'단어{i}는 중요합니다' for i in range(50)]
        content = '. '.join(words)
        result = generate_word_frequency(content, top_n=10)
        self.assertLessEqual(len(result['word_cloud']), 10)

    def test_frequency_calculation(self):
        content = '품질 품질 품질 성능 성능 비용'
        result = generate_word_frequency(content)
        if result['word_cloud']:
            top = result['word_cloud'][0]
            self.assertEqual(top['word'], '품질')
            self.assertEqual(top['count'], 3)

    def test_diversity_ratio(self):
        content = '서로 다른 단어를 사용한 문장입니다. 각각 고유한 표현을 포함합니다.'
        result = generate_word_frequency(content)
        self.assertGreater(result['summary']['diversity_ratio'], 0.0)

    def test_heading_excluded(self):
        content = '## 제목입니다\n\n본문 내용이 여기에 있습니다. 자세한 설명을 합니다.'
        result = generate_word_frequency(content)
        # 헤딩 마크업(##)이 단어로 카운트되지 않아야 함
        words = [w['word'] for w in result['word_cloud']]
        self.assertNotIn('##', words)

    def test_score_range(self):
        content = '테스트 콘텐츠를 작성합니다. 품질을 확인합니다.'
        result = generate_word_frequency(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '반복 반복 반복 반복 반복 반복 반복 반복 반복 반복'
        result = generate_word_frequency(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '구조 확인용 텍스트입니다.'
        result = generate_word_frequency(content)
        self.assertIn('word_cloud', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_words', result['summary'])
        self.assertIn('unique_words', result['summary'])
        self.assertIn('diversity_ratio', result['summary'])


if __name__ == '__main__':
    unittest.main()
