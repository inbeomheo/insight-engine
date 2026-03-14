"""Methodology Transparency Checker 서비스 테스트."""
import unittest
from services.analysis.methodology_transparency_service import check_methodology_transparency


class TestMethodologyTransparency(unittest.TestCase):

    def test_empty_content(self):
        result = check_methodology_transparency('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_methodology_transparency(None)
        self.assertEqual(result['score'], 50.0)

    def test_no_methodology(self):
        content = '이 제품은 좋습니다. 추천합니다.'
        result = check_methodology_transparency(content)
        self.assertEqual(result['summary']['level'], 'opaque')

    def test_data_source(self):
        content = '데이터 출처는 공공 데이터 포털입니다. 데이터 수집은 2024년에 진행했습니다.'
        result = check_methodology_transparency(content)
        self.assertIn('data_source', result['summary']['found_list'])

    def test_sample_info(self):
        content = '표본 크기는 500명이며, 응답자 320명의 데이터를 분석했습니다.'
        result = check_methodology_transparency(content)
        self.assertIn('sample_info', result['summary']['found_list'])

    def test_process_description(self):
        content = '다음 과정을 거쳐 분석했습니다. 분석 과정은 3단계로 구성됩니다.'
        result = check_methodology_transparency(content)
        self.assertIn('process_description', result['summary']['found_list'])

    def test_limitations(self):
        content = '이 분석의 한계는 표본이 한국에 한정된다는 점입니다.'
        result = check_methodology_transparency(content)
        self.assertIn('limitations', result['summary']['found_list'])

    def test_reproducibility(self):
        content = '코드 공개: GitHub에서 사용한 스크립트를 확인할 수 있습니다.'
        result = check_methodology_transparency(content)
        self.assertIn('reproducibility', result['summary']['found_list'])

    def test_time_context(self):
        content = '2024년 12월 기준으로 조사 기간은 3개월입니다.'
        result = check_methodology_transparency(content)
        self.assertIn('time_context', result['summary']['found_list'])

    def test_transparent_level(self):
        content = ('데이터 출처: 통계청. '
                   '표본 크기 1000명. '
                   '분석 과정은 3단계입니다. '
                   '이 분석의 한계가 있습니다. '
                   '코드 공개되어 있습니다. '
                   '2024년 6월 기준입니다.')
        result = check_methodology_transparency(content)
        self.assertIn(result['summary']['level'], ('transparent', 'good'))

    def test_english_content(self):
        content = ('Data source: public API. '
                   'Sample size N=500. '
                   'Our methodology includes three steps. '
                   'Limitations include regional bias.')
        result = check_methodology_transparency(content)
        self.assertGreater(result['summary']['categories_found'], 2)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_methodology_transparency(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_methodology_transparency(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('transparency_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('categories_found', result['summary'])
        self.assertIn('found_list', result['summary'])
        self.assertIn('missing_list', result['summary'])
        self.assertIn('transparency_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_opaque(self):
        content = '결론적으로 A가 B보다 좋습니다.'
        result = check_methodology_transparency(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
