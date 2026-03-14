"""Tone Consistency Checker 서비스 테스트."""
import unittest
from services.analysis.tone_consistency_service import check_tone_consistency


class TestToneConsistencyChecker(unittest.TestCase):

    def test_empty_content(self):
        result = check_tone_consistency('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = check_tone_consistency(None)
        self.assertEqual(result['score'], 100.0)

    def test_consistent_formal_korean(self):
        content = '테스트가 중요합니다. 품질을 보장합니다. 성능이 향상됩니다.'
        result = check_tone_consistency(content)
        self.assertEqual(result['summary']['dominant_tone'], 'formal')
        self.assertEqual(len(result['inconsistencies']), 0)

    def test_consistent_polite_korean(self):
        content = '이것은 좋아요. 정말 멋있네요. 한번 해보세요.'
        result = check_tone_consistency(content)
        self.assertEqual(result['summary']['dominant_tone'], 'polite')

    def test_mixed_formal_casual_korean(self):
        content = '테스트가 중요합니다. 이건 좋아. 품질을 보장합니다. 해봐.'
        result = check_tone_consistency(content)
        self.assertGreater(len(result['inconsistencies']), 0)

    def test_consistent_formal_english(self):
        content = 'Furthermore, this is important. Moreover, it has value. Nevertheless, we proceed.'
        result = check_tone_consistency(content)
        self.assertEqual(result['summary']['dominant_tone'], 'formal')

    def test_mixed_formal_casual_english(self):
        content = 'Furthermore this is important. This is pretty much awesome stuff!!'
        result = check_tone_consistency(content)
        self.assertGreater(len(result['inconsistencies']), 0)

    def test_neutral_only(self):
        content = '날씨가 좋다. 하늘이 파랗다. 바람이 분다.'
        result = check_tone_consistency(content)
        # neutral만 있으면 일관적
        self.assertEqual(len(result['inconsistencies']), 0)

    def test_consistency_rate_high(self):
        content = '이것이 중요합니다. 저것도 필요합니다. 모두 있습니다.'
        result = check_tone_consistency(content)
        self.assertGreaterEqual(result['summary']['consistency_rate'], 80.0)

    def test_tone_distribution(self):
        content = '중요합니다. 좋아요. 해봐.'
        result = check_tone_consistency(content)
        dist = result['summary']['tone_distribution']
        self.assertIsInstance(dist, dict)
        self.assertGreater(len(dist), 0)

    def test_suggestions_consistent(self):
        content = '모두 중요합니다. 기능이 좋습니다. 성능이 뛰어납니다.'
        result = check_tone_consistency(content)
        self.assertTrue(any('일관' in s for s in result['suggestions']))

    def test_suggestions_inconsistent(self):
        content = '이것이 중요합니다. 이건 좋아. 해봐. 결과가 나옵니다.'
        result = check_tone_consistency(content)
        if result['inconsistencies']:
            self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다. 확인합니다.'
        result = check_tone_consistency(content)
        self.assertIn('tone_analysis', result)
        self.assertIn('inconsistencies', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('dominant_tone', result['summary'])
        self.assertIn('consistency_rate', result['summary'])
        self.assertIn('tone_distribution', result['summary'])


if __name__ == '__main__':
    unittest.main()
