"""Sentence Ending Variety 서비스 테스트."""
import unittest
from services.sentence_ending_variety_service import analyze_sentence_ending_variety


class TestSentenceEndingVariety(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_sentence_ending_variety('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = analyze_sentence_ending_variety(None)
        self.assertEqual(result['score'], 100.0)

    def test_varied_endings(self):
        content = '이것은 중요합니다. 왜 그럴까요? 정말 좋습니다! 확인해 보세요.'
        result = analyze_sentence_ending_variety(content)
        self.assertGreater(result['summary']['unique_endings'], 1)

    def test_monotonous_endings(self):
        content = '테스트합니다. 확인합니다. 진행합니다. 완료합니다. 종료합니다.'
        result = analyze_sentence_ending_variety(content)
        self.assertEqual(result['summary']['dominant_ending'], '합니다')

    def test_ending_distribution(self):
        content = '중요합니다. 좋습니다. 그렇습니다? 맞습니다!'
        result = analyze_sentence_ending_variety(content)
        dist = result['ending_distribution']
        self.assertIsInstance(dist, dict)
        self.assertGreater(len(dist), 0)

    def test_english_endings(self):
        content = 'This is important. Is it good? Yes it is!'
        result = analyze_sentence_ending_variety(content)
        self.assertGreater(result['summary']['unique_endings'], 1)

    def test_dominant_ending_ratio(self):
        content = '테스트를 진행합니다. 품질을 확인합니다. 결과를 보장합니다. 성능을 측정합니다. 기능을 검증합니다. 이것은 다릅니다.'
        result = analyze_sentence_ending_variety(content)
        self.assertGreater(result['ending_distribution'].get('합니다', 0), 3)

    def test_ending_data_structure(self):
        content = '첫 문장입니다. 두 번째입니다.'
        result = analyze_sentence_ending_variety(content)
        if result['ending_data']:
            d = result['ending_data'][0]
            self.assertIn('text', d)
            self.assertIn('ending', d)

    def test_max_30_entries(self):
        content = '. '.join([f'문장 {i}입니다' for i in range(40)]) + '.'
        result = analyze_sentence_ending_variety(content)
        self.assertLessEqual(len(result['ending_data']), 30)

    def test_score_monotonous(self):
        content = '진행합니다. 확인합니다. 완료합니다. 시작합니다. 종료합니다. 처리합니다.'
        result = analyze_sentence_ending_variety(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '테스트를 진행합니다. 품질을 확인합니다. 결과를 보장합니다. 성능을 측정합니다. 기능을 검증합니다.'
        result = analyze_sentence_ending_variety(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다.'
        result = analyze_sentence_ending_variety(content)
        self.assertIn('ending_data', result)
        self.assertIn('ending_distribution', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('variety_rate', result['summary'])
        self.assertIn('dominant_ending', result['summary'])


if __name__ == '__main__':
    unittest.main()
