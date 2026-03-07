"""Acronym Consistency Checker 서비스 테스트."""
import unittest
from services.acronym_consistency_checker_service import check_acronym_consistency


class TestAcronymConsistencyChecker(unittest.TestCase):

    def test_empty_content(self):
        result = check_acronym_consistency('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_acronyms'], 0)

    def test_none_content(self):
        result = check_acronym_consistency(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_acronyms(self):
        content = '이 글에는 약어가 전혀 없습니다. 모든 단어가 일반 텍스트입니다.'
        result = check_acronym_consistency(content)
        self.assertEqual(result['summary']['unique_acronyms'], 0)

    def test_defined_acronym(self):
        content = 'Natural Language Processing (NLP)는 중요합니다. NLP 기술이 발전하고 있습니다.'
        result = check_acronym_consistency(content)
        self.assertGreater(result['summary']['defined_count'], 0)

    def test_undefined_acronym(self):
        content = 'BERT 모델은 성능이 좋습니다. BERT를 사용하면 정확도가 높아집니다.'
        result = check_acronym_consistency(content)
        self.assertGreater(result['summary']['undefined_count'], 0)
        issues = [i for i in result['issues'] if i['type'] == 'undefined']
        self.assertGreater(len(issues), 0)

    def test_common_acronyms_excluded(self):
        content = 'API를 통해 HTTP 요청을 보냅니다. URL을 확인하세요.'
        result = check_acronym_consistency(content)
        # API, HTTP, URL은 흔한 약어로 제외
        self.assertEqual(result['summary']['unique_acronyms'], 0)

    def test_multiple_acronyms(self):
        content = ('Machine Learning (ML)과 Deep Learning (DL)은 관련이 있습니다. '
                   'ML과 DL 기술이 발전합니다. '
                   'GAN은 정의 없이 사용되었습니다.')
        result = check_acronym_consistency(content)
        self.assertGreaterEqual(result['summary']['unique_acronyms'], 3)
        self.assertGreaterEqual(result['summary']['defined_count'], 2)

    def test_consistency_level_excellent(self):
        content = ('Natural Language Processing (NLP)는 중요합니다. '
                   'Recurrent Neural Network (RNN)을 사용합니다. '
                   'NLP와 RNN이 결합됩니다.')
        result = check_acronym_consistency(content)
        self.assertEqual(result['summary']['consistency_level'], 'excellent')

    def test_consistency_level_poor(self):
        content = ('BERT 모델이 좋습니다. GPT도 사용합니다. '
                   'LSTM은 순환 신경망입니다. CNN은 합성곱 신경망입니다.')
        result = check_acronym_consistency(content)
        self.assertIn(result['summary']['consistency_level'], ('fair', 'poor'))

    def test_score_range(self):
        content = 'NLP 기술이 발전합니다.'
        result = check_acronym_consistency(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = 'Machine Learning (ML) 기술입니다.'
        result = check_acronym_consistency(content)
        self.assertIn('acronym_map', result)
        self.assertIn('issues', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_acronyms', result['summary'])
        self.assertIn('unique_acronyms', result['summary'])
        self.assertIn('defined_count', result['summary'])
        self.assertIn('undefined_count', result['summary'])
        self.assertIn('consistency_level', result['summary'])

    def test_acronym_map_structure(self):
        content = 'Natural Language Processing (NLP)을 사용합니다. NLP가 최고입니다.'
        result = check_acronym_consistency(content)
        for item in result['acronym_map']:
            self.assertIn('acronym', item)
            self.assertIn('full_name', item)
            self.assertIn('count', item)
            self.assertIn('defined', item)

    def test_suggestions_for_undefined(self):
        content = 'BERT와 GPT는 좋은 모델입니다.'
        result = check_acronym_consistency(content)
        has_define_suggestion = any('정의' in s or '풀네임' in s for s in result['suggestions'])
        self.assertTrue(has_define_suggestion)

    def test_max_20_acronym_map(self):
        acronyms = ' '.join([f'ACR{i}' for i in range(25)])
        content = f'다양한 약어: {acronyms}'
        result = check_acronym_consistency(content)
        self.assertLessEqual(len(result['acronym_map']), 20)


if __name__ == '__main__':
    unittest.main()
