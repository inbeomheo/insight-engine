"""Simple Alternative Finder 서비스 단위 테스트"""
import unittest
from services.simple_alternative_service import find_simple_alternatives


class TestSimpleAlternativeService(unittest.TestCase):

    def test_empty_content(self):
        result = find_simple_alternatives('')
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['score'], 100.0)
        result_none = find_simple_alternatives(None)
        self.assertEqual(result_none['findings'], [])

    def test_no_complex_words(self):
        content = '오늘 날씨가 좋다. 기분이 좋은 하루다.'
        result = find_simple_alternatives(content)
        self.assertEqual(result['summary']['total_complex'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_korean_complex_detection(self):
        content = '상기 문서를 검토하다. 차후 이행하다.'
        result = find_simple_alternatives(content)
        ko = [f for f in result['findings'] if f['language'] == 'korean']
        self.assertGreaterEqual(len(ko), 2)
        words = [f['word'] for f in ko]
        self.assertIn('검토하다', words)

    def test_english_complex_detection(self):
        content = 'We should utilize this tool and facilitate the process.'
        result = find_simple_alternatives(content)
        en = [f for f in result['findings'] if f['language'] == 'english']
        self.assertGreaterEqual(len(en), 2)

    def test_alternative_provided(self):
        content = '금번 회의에서 결정하겠습니다.'
        result = find_simple_alternatives(content)
        if result['findings']:
            f = result['findings'][0]
            self.assertTrue(len(f['alternative']) > 0)

    def test_count_accuracy(self):
        content = '활용하다 방법을 활용하다 형태로 활용하다.'
        result = find_simple_alternatives(content)
        hw = [f for f in result['findings'] if f['word'] == '활용하다']
        self.assertEqual(len(hw), 1)
        self.assertEqual(hw[0]['count'], 3)

    def test_score_range(self):
        content = '간단한 글입니다.'
        r1 = find_simple_alternatives(content)
        self.assertGreaterEqual(r1['score'], 0)
        self.assertLessEqual(r1['score'], 100)

    def test_score_decreases_with_complex(self):
        simple = '간단한 글입니다.'
        complex_text = '상기 사항을 검토하다. 차후 이행하다. 제반 사항을 숙지하다. 소정의 절차를 수행하다.'
        r_simple = find_simple_alternatives(simple)
        r_complex = find_simple_alternatives(complex_text)
        self.assertGreaterEqual(r_simple['score'], r_complex['score'])

    def test_suggestions_for_complex(self):
        content = '상기 문서를 검토하다. 차후 이행하다. 제반 사항을 숙지하다.'
        result = find_simple_alternatives(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_mixed_language(self):
        content = '이 시스템을 utilize하여 facilitate하는 방법을 검토하다.'
        result = find_simple_alternatives(content)
        languages = {f['language'] for f in result['findings']}
        self.assertTrue(len(languages) >= 1)

    def test_summary_structure(self):
        result = find_simple_alternatives('활용하다.')
        self.assertIn('total_complex', result['summary'])
        self.assertIn('korean_complex', result['summary'])
        self.assertIn('english_complex', result['summary'])

    def test_return_structure(self):
        result = find_simple_alternatives('테스트 문장.')
        self.assertIn('findings', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)


if __name__ == '__main__':
    unittest.main()
