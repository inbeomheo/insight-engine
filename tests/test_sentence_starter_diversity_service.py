"""Sentence Starter Diversity 서비스 테스트."""
import unittest
from services.sentence_starter_diversity_service import analyze_sentence_starter_diversity


class TestSentenceStarterDiversity(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_sentence_starter_diversity('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = analyze_sentence_starter_diversity(None)
        self.assertEqual(result['score'], 0.0)

    def test_diverse_starters(self):
        content = ('프로젝트를 시작합니다. 팀원들이 모였습니다. '
                   '계획을 세웁니다. 실행이 중요합니다. '
                   '결과를 확인합니다. 성과가 좋습니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertGreaterEqual(result['summary']['diversity_ratio'], 60.0)

    def test_repetitive_starters(self):
        content = ('이것은 첫 번째입니다. 이것은 두 번째입니다. '
                   '이것은 세 번째입니다. 이것은 네 번째입니다. '
                   '이것은 다섯 번째입니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertLessEqual(result['summary']['diversity_ratio'], 30.0)

    def test_consecutive_repeats(self):
        content = ('우리는 계획합니다. 우리는 실행합니다. '
                   '팀이 협력합니다. 팀이 성장합니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertGreater(result['summary']['consecutive_repeats'], 0)

    def test_starter_data_structure(self):
        content = '안녕하세요. 반갑습니다. 좋은 하루 되세요.'
        result = analyze_sentence_starter_diversity(content)
        for item in result['starter_data']:
            self.assertIn('starter', item)
            self.assertIn('count', item)
            self.assertIn('ratio', item)

    def test_level_diverse(self):
        content = ('하늘이 맑습니다. 바람이 시원합니다. '
                   '꽃이 피었습니다. 새가 노래합니다. '
                   '강이 흐릅니다. 산이 보입니다. '
                   '구름이 떠갑니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertEqual(result['summary']['level'], 'diverse')

    def test_level_repetitive(self):
        content = ('그는 출근합니다. 그는 일합니다. 그는 퇴근합니다. '
                   '그는 저녁을 먹습니다. 그는 잠을 잡니다. '
                   '그는 다시 일어납니다. 그는 운동합니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertIn(result['summary']['level'], ('repetitive', 'very_repetitive'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_sentence_starter_diversity(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 테스트 문장입니다.'
        result = analyze_sentence_starter_diversity(content)
        self.assertIn('starter_data', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('unique_starters', result['summary'])
        self.assertIn('diversity_ratio', result['summary'])
        self.assertIn('consecutive_repeats', result['summary'])

    def test_suggestions_for_repetitive(self):
        content = ('이것은 반복입니다. 이것은 또 반복입니다. '
                   '이것은 계속 반복입니다. 이것은 여전히 반복입니다.')
        result = analyze_sentence_starter_diversity(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_max_15_starter_data(self):
        starters = [f'{chr(0xAC00 + i)}가 좋습니다.' for i in range(20)]
        content = ' '.join(starters)
        result = analyze_sentence_starter_diversity(content)
        self.assertLessEqual(len(result['starter_data']), 15)


if __name__ == '__main__':
    unittest.main()
