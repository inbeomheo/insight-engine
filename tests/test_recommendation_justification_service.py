"""Recommendation Justification Analyzer 서비스 테스트."""
import unittest
from services.quality.recommendation_justification_service import analyze_recommendation_justification


class TestRecommendationJustification(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_recommendation_justification('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['is_recommendation_content'])

    def test_none_content(self):
        result = analyze_recommendation_justification(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_recommendation(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = analyze_recommendation_justification(content)
        self.assertEqual(result['summary']['justification_level'], 'none')

    def test_recommendation_without_justification(self):
        content = ('최고의 노트북 추천 TOP 5 랭킹입니다. '
                   '1번 제품입니다. 2번 제품입니다. 3번 제품입니다.')
        result = analyze_recommendation_justification(content)
        self.assertTrue(result['summary']['is_recommendation_content'])
        self.assertIn(result['summary']['justification_level'], ('missing', 'partial'))

    def test_with_why(self):
        content = ('최고의 에디터 추천 리뷰 비교입니다. '
                   '이 제품을 추천하는 이유는 뛰어난 성능 때문입니다. '
                   '또 다른 장점은 가격이 합리적이기 때문입니다.')
        result = analyze_recommendation_justification(content)
        self.assertTrue(result['summary']['has_why'])

    def test_with_best_for(self):
        content = ('최고의 프로그래밍 언어 추천 비교입니다. '
                   '초보자에게 추천합니다. '
                   '이런 분에게 좋습니다.')
        result = analyze_recommendation_justification(content)
        self.assertTrue(result['summary']['has_best_for'])

    def test_with_comparison(self):
        content = ('최고의 프레임워크 추천 리뷰입니다. '
                   'React보다 나은 대안입니다. '
                   '다른 제품 대비 뛰어난 성능입니다.')
        result = analyze_recommendation_justification(content)
        self.assertTrue(result['summary']['has_comparison'])

    def test_thorough_justification(self):
        content = ('최고의 도구 추천 리뷰 비교입니다. '
                   '이 도구를 추천하는 이유는 안정성 때문입니다. '
                   '성능이 뛰어나기 때문에 선택했습니다. '
                   '초보자에게 적합한 도구입니다. '
                   '전문가에게도 추천합니다. '
                   '다른 대안 대비 성능이 우수합니다.')
        result = analyze_recommendation_justification(content)
        self.assertIn(result['summary']['justification_level'], ('thorough', 'adequate'))

    def test_english_content(self):
        content = ('Best laptops review comparison ranking. '
                   'We recommend this because of its performance. '
                   'The reason we chose it is the excellent build quality. '
                   'Best for students and professionals. '
                   'Better than alternatives in battery life.')
        result = analyze_recommendation_justification(content)
        self.assertTrue(result['summary']['is_recommendation_content'])
        self.assertTrue(result['summary']['has_why'])

    def test_score_range(self):
        content = '일반적인 추천 콘텐츠입니다.'
        result = analyze_recommendation_justification(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 추천 리뷰 테스트입니다.'
        result = analyze_recommendation_justification(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('missing_why', result)
        self.assertIn('missing_best_for', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_recommendation_content', result['summary'])
        self.assertIn('has_why', result['summary'])
        self.assertIn('has_best_for', result['summary'])
        self.assertIn('has_comparison', result['summary'])
        self.assertIn('justification_level', result['summary'])

    def test_suggestions_exist(self):
        content = ('최고의 제품 추천 랭킹입니다. '
                   '이 제품은 좋습니다.')
        result = analyze_recommendation_justification(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
