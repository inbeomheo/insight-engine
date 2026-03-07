"""Sentence Length Rhythm Analyzer 서비스 테스트."""
import unittest
from services.sentence_length_rhythm_service import analyze_sentence_rhythm


class TestSentenceLengthRhythm(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_sentence_rhythm('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = analyze_sentence_rhythm(None)
        self.assertEqual(result['score'], 0.0)

    def test_varied_lengths(self):
        content = '짧다. 이것은 중간 길이의 문장입니다. 이 문장은 상당히 긴 편으로 다양한 내용을 포함하고 있어서 독자에게 풍부한 정보를 전달합니다.'
        result = analyze_sentence_rhythm(content)
        self.assertGreater(result['summary']['std_deviation'], 0)
        self.assertGreater(result['summary']['total_sentences'], 0)

    def test_monotonous_lengths(self):
        content = '비슷한 길이입니다. 거의 같은 길이요. 모두 유사한 정도.'
        result = analyze_sentence_rhythm(content)
        self.assertIn(result['summary']['rhythm_quality'], ('monotonous', 'moderate', 'insufficient'))

    def test_length_data_structure(self):
        content = '첫 문장입니다. 두 번째 문장은 조금 더 길게 작성합니다.'
        result = analyze_sentence_rhythm(content)
        if result['length_data']:
            d = result['length_data'][0]
            self.assertIn('index', d)
            self.assertIn('length', d)
            self.assertIn('category', d)
            self.assertIn('text', d)

    def test_category_assignment(self):
        content = '짧다. 이것은 중간 정도의 길이를 가진 문장입니다. 이 문장은 매우 길어서 긴 문장 카테고리에 해당할 수 있도록 의도적으로 많은 단어를 포함하여 작성하였습니다.'
        result = analyze_sentence_rhythm(content)
        categories = [d['category'] for d in result['length_data']]
        self.assertIn('short', categories)

    def test_avg_length(self):
        content = '10자 문장임. 20자 정도 되는 문장입니다.'
        result = analyze_sentence_rhythm(content)
        self.assertGreater(result['summary']['avg_length'], 0.0)

    def test_rhythm_analysis(self):
        content = '짧은 문장. 조금 더 긴 문장입니다. 아주 짧다. 이것은 상당히 긴 문장으로 다양한 내용을 담고 있습니다.'
        result = analyze_sentence_rhythm(content)
        self.assertIn('category_distribution', result['rhythm_analysis'])
        self.assertIn('max_consecutive_same', result['rhythm_analysis'])

    def test_consecutive_same_detection(self):
        # 모두 중간 길이 → 연속 동일 카테고리
        content = '. '.join([f'중간 길이의 문장 번호 {i}입니다' for i in range(6)]) + '.'
        result = analyze_sentence_rhythm(content)
        self.assertGreaterEqual(result['rhythm_analysis']['max_consecutive_same'], 3)

    def test_max_50_entries(self):
        content = '. '.join([f'문장 {i}' for i in range(60)]) + '.'
        result = analyze_sentence_rhythm(content)
        self.assertLessEqual(len(result['length_data']), 50)

    def test_score_range(self):
        content = '테스트 콘텐츠입니다. 확인합니다.'
        result = analyze_sentence_rhythm(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '문장입니다. 글입니다. 말입니다.'
        result = analyze_sentence_rhythm(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다.'
        result = analyze_sentence_rhythm(content)
        self.assertIn('length_data', result)
        self.assertIn('rhythm_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('avg_length', result['summary'])
        self.assertIn('std_deviation', result['summary'])
        self.assertIn('rhythm_quality', result['summary'])


if __name__ == '__main__':
    unittest.main()
