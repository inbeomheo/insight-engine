"""Evaluation Criteria Disclosure Checker 서비스 테스트."""
import unittest
from services.evaluation_criteria_disclosure_service import check_evaluation_criteria_disclosure


class TestEvaluationCriteriaDisclosure(unittest.TestCase):

    def test_empty_content(self):
        result = check_evaluation_criteria_disclosure('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_evaluation_criteria_disclosure(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_review_content(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = check_evaluation_criteria_disclosure(content)
        self.assertFalse(result['summary']['is_review_content'])

    def test_review_without_criteria(self):
        content = ('최고의 노트북 랭킹 비교 리뷰입니다. '
                   '이 제품은 정말 좋습니다. 강력 추천합니다. '
                   '다른 제품보다 훨씬 낫습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertTrue(result['summary']['is_review_content'])
        self.assertGreater(len(result['summary']['criteria_missing']), 0)

    def test_review_with_criteria(self):
        content = ('노트북 벤치마크 비교 테스트 리뷰입니다. '
                   '평가 기준: 성능, 배터리, 디자인. '
                   '테스트 방법: 동일 조건에서 3회 반복 측정. '
                   '2024년 3월 기준. '
                   '10대를 테스트했습니다. '
                   '한계: 실사용 환경과 다를 수 있습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertTrue(result['summary']['is_review_content'])
        self.assertGreater(len(result['summary']['criteria_found']), 3)

    def test_evaluation_criteria_found(self):
        content = ('제품 비교 리뷰입니다. 랭킹을 매겼습니다. '
                   '평가 기준은 가격, 성능, 디자인입니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('evaluation_criteria', result['summary']['criteria_found'])

    def test_test_method_found(self):
        content = ('이 벤치마크 리뷰의 테스트 방법은 다음과 같습니다. '
                   '동일한 테스트 환경에서 측정했습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('test_method', result['summary']['criteria_found'])

    def test_sample_size_found(self):
        content = ('제품 비교 리뷰를 진행합니다. 평가 결과입니다. '
                   '5개를 테스트하여 비교했습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('sample_size', result['summary']['criteria_found'])

    def test_test_date_found(self):
        content = ('랭킹 비교 리뷰입니다. '
                   '2024년 6월 기준일로 작성했습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('test_date', result['summary']['criteria_found'])

    def test_limitations_found(self):
        content = ('제품 비교 리뷰입니다. 평가를 진행합니다. '
                   '한계: 실험실 환경에서만 테스트했습니다. '
                   '유의사항을 참고하세요.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('limitations', result['summary']['criteria_found'])

    def test_english_review(self):
        content = ('Best laptop comparison review and benchmark results. '
                   'Evaluation criteria include performance and battery. '
                   'Test method: standardized benchmarks. '
                   'Tested on 2024-03-15.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertTrue(result['summary']['is_review_content'])
        self.assertGreater(len(result['summary']['criteria_found']), 0)

    def test_score_range(self):
        content = '일반적인 리뷰 콘텐츠입니다.'
        result = check_evaluation_criteria_disclosure(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 비교 리뷰 테스트입니다.'
        result = check_evaluation_criteria_disclosure(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('criteria_details', result)
        self.assertIn('missing_criteria', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_review_content', result['summary'])
        self.assertIn('criteria_found', result['summary'])
        self.assertIn('criteria_missing', result['summary'])
        self.assertIn('completeness_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_missing(self):
        content = ('최고의 노트북 랭킹 비교 리뷰입니다. '
                   '이 제품이 제일 좋습니다.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_completeness_ratio(self):
        content = ('벤치마크 비교 리뷰입니다. '
                   '평가 기준: 성능 점수. '
                   '테스트 환경: Windows 11.')
        result = check_evaluation_criteria_disclosure(content)
        self.assertGreater(result['summary']['completeness_ratio'], 0.0)


if __name__ == '__main__':
    unittest.main()
