"""Trade-off Coverage Analyzer 서비스 테스트."""
import unittest
from services.tradeoff_coverage_analyzer_service import analyze_tradeoff_coverage


class TestTradeoffCoverage(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_tradeoff_coverage('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['is_recommendation_content'])

    def test_none_content(self):
        result = analyze_tradeoff_coverage(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_review_content(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 자연이 아름답습니다.'
        result = analyze_tradeoff_coverage(content)
        self.assertEqual(result['summary']['level'], 'none')

    def test_one_sided_positive(self):
        content = ('최고의 노트북 추천 TOP 5입니다. '
                   '이 제품은 최고의 성능을 자랑합니다. '
                   '뛰어난 디자인과 우수한 품질입니다. '
                   '탁월한 배터리와 훌륭한 화면입니다. '
                   '강력한 프로세서로 완벽합니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertTrue(result['summary']['is_recommendation_content'])
        self.assertIn(result['summary']['level'], ('one_sided', 'heavily_one_sided'))
        self.assertLess(result['score'], 70.0)

    def test_balanced_review(self):
        content = ('최고의 노트북 추천 비교 리뷰입니다. '
                   '장점은 뛰어난 성능과 우수한 디자인입니다. '
                   '단점은 무거운 무게와 부족한 배터리입니다. '
                   '그러나 가격 대비 훌륭합니다. '
                   '한계로는 확장성이 제한적입니다. '
                   '주의사항으로 발열이 있습니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertGreater(result['summary']['negative_count'], 0)
        self.assertGreater(result['summary']['positive_count'], 0)

    def test_has_contrast_section(self):
        content = ('추천 제품 비교입니다. '
                   '장점: 가볍고 편리합니다. '
                   '단점: 비싸고 내구성이 부족합니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertTrue(result['summary']['has_contrast'])

    def test_target_limits(self):
        content = ('최고의 코딩 에디터 추천입니다. '
                   'VS Code는 우수한 확장성을 가집니다. '
                   '초보자에게는 적합하지 않을 수 있습니다. '
                   '단점으로 메모리 사용량이 높습니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertTrue(result['summary']['has_target_limits'])

    def test_english_review(self):
        content = ('Best laptops review and comparison. '
                   'This product has excellent performance. '
                   'However, the battery life is a major drawback. '
                   'The limitation is the heavy weight.')
        result = analyze_tradeoff_coverage(content)
        self.assertTrue(result['summary']['is_recommendation_content'])
        self.assertGreater(result['summary']['negative_count'], 0)

    def test_score_range(self):
        content = '일반적인 추천 콘텐츠입니다.'
        result = analyze_tradeoff_coverage(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인용 추천 리뷰입니다.'
        result = analyze_tradeoff_coverage(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('positive_expressions', result)
        self.assertIn('negative_expressions', result)
        self.assertIn('one_sided_sections', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_recommendation_content', result['summary'])
        self.assertIn('positive_count', result['summary'])
        self.assertIn('negative_count', result['summary'])
        self.assertIn('balance_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_one_sided(self):
        content = ('최고의 제품 추천입니다. '
                   '뛰어난 성능과 우수한 품질입니다. '
                   '탁월하고 훌륭합니다. 강력 추천합니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_one_sided_sections_detection(self):
        content = ('# 추천 제품 A 리뷰\n'
                   '우수한 성능입니다. 뛰어난 디자인입니다. '
                   '최고의 품질입니다. 탁월한 내구성입니다. '
                   '편리한 사용성입니다.\n'
                   '# 결론\n'
                   '모두 좋습니다.')
        result = analyze_tradeoff_coverage(content)
        self.assertGreater(len(result['one_sided_sections']), 0)


if __name__ == '__main__':
    unittest.main()
