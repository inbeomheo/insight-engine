"""llm_share_board_service 단위 테스트"""
import unittest

from services.llm_share_board_service import (
    compare_llm_share,
    ShareBoard,
    _count_mentions,
    _count_responses_with_mention,
    _calculate_score,
    _generate_summary,
)


class TestCountMentions(unittest.TestCase):
    """_count_mentions 함수 테스트"""

    def test_exact_match_korean(self):
        """한국어 브랜드 정확 매칭"""
        responses = ['삼성전자는 반도체 1위입니다.']
        self.assertEqual(_count_mentions('삼성전자', responses), 1)

    def test_exact_match_english(self):
        """영어 브랜드 대소문자 무시"""
        responses = ['OpenAI released GPT-5. openai is leading.']
        self.assertEqual(_count_mentions('OpenAI', responses), 2)

    def test_no_match(self):
        """매칭 없는 경우"""
        responses = ['구글이 AI 모델을 발표했습니다.']
        self.assertEqual(_count_mentions('네이버', responses), 0)

    def test_multiple_responses(self):
        """여러 응답에서 총 언급 수"""
        responses = [
            'Tesla가 새 모델을 출시했습니다.',
            'Tesla는 전기차 시장을 선도합니다. Tesla의 주가는 상승 중.',
            '현대차도 전기차를 만듭니다.',
        ]
        self.assertEqual(_count_mentions('Tesla', responses), 3)

    def test_empty_responses(self):
        """빈 응답 목록"""
        self.assertEqual(_count_mentions('브랜드', []), 0)


class TestCountResponsesWithMention(unittest.TestCase):
    """_count_responses_with_mention 함수 테스트"""

    def test_count_responses(self):
        """언급된 응답 개수 확인"""
        responses = [
            '삼성전자 반도체',
            '인텔 프로세서',
            '삼성전자 갤럭시',
        ]
        self.assertEqual(_count_responses_with_mention('삼성전자', responses), 2)

    def test_no_responses_with_mention(self):
        """언급 없는 경우"""
        responses = ['A 기업', 'B 기업']
        self.assertEqual(_count_responses_with_mention('C 기업', responses), 0)


class TestCalculateScore(unittest.TestCase):
    """_calculate_score 함수 테스트"""

    def test_zero_responses(self):
        """응답이 없으면 0점"""
        self.assertEqual(_calculate_score(0, 0, 0), 0.0)

    def test_full_coverage(self):
        """모든 응답에 1회씩 언급 → 응답 비율 60 + 밀도 (1/3*40)"""
        score = _calculate_score(5, 5, 5)
        # response_ratio=1.0 → 60, density=min(1,3)/3=0.333 → 13.3
        self.assertAlmostEqual(score, 73.3, places=1)

    def test_partial_coverage(self):
        """일부 응답에만 언급"""
        score = _calculate_score(2, 2, 10)
        # response_ratio=0.2 → 12, density=min(0.2,3)/3=0.067 → 2.7
        self.assertAlmostEqual(score, 14.7, places=1)

    def test_high_density(self):
        """응답당 3회 이상 → 밀도 캡"""
        score = _calculate_score(30, 5, 5)
        # response_ratio=1.0 → 60, density=min(6,3)/3=1.0 → 40
        self.assertEqual(score, 100.0)


class TestGenerateSummary(unittest.TestCase):
    """_generate_summary 함수 테스트"""

    def test_brand_leading(self):
        """브랜드가 경쟁사보다 앞서는 경우"""
        summary = _generate_summary('MyBrand', 80.0, {'Competitor': 50.0})
        self.assertIn('우위', summary)
        self.assertIn('MyBrand', summary)

    def test_brand_behind(self):
        """브랜드가 뒤처진 경우"""
        summary = _generate_summary('MyBrand', 30.0, {'Competitor': 70.0})
        self.assertIn('뒤처져', summary)

    def test_no_competitors(self):
        """경쟁사 없는 경우"""
        summary = _generate_summary('MyBrand', 60.0, {})
        self.assertIn('MyBrand', summary)

    def test_all_zero(self):
        """모두 점수 0"""
        summary = _generate_summary('MyBrand', 0.0, {'Comp': 0.0})
        self.assertIn('언급되지 않았습니다', summary)

    def test_brand_zero_competitor_high(self):
        """브랜드 0점, 경쟁사 높은 점수"""
        summary = _generate_summary('MyBrand', 0.0, {'Comp': 80.0})
        self.assertIn('시급', summary)


class TestCompareLlmShare(unittest.TestCase):
    """compare_llm_share 통합 테스트"""

    def test_returns_share_board(self):
        """반환 타입이 ShareBoard인지 확인"""
        result = compare_llm_share('TestBrand', ['Comp1'], ['TestBrand 언급'])
        self.assertIsInstance(result, ShareBoard)

    def test_basic_comparison(self):
        """기본 비교 동작"""
        responses = [
            'TestBrand는 좋은 제품입니다.',
            'Comp1이 시장을 선도합니다. Comp1의 기술력.',
            'TestBrand와 Comp1 모두 참여.',
        ]
        result = compare_llm_share('TestBrand', ['Comp1'], responses)
        self.assertEqual(result.brand, 'TestBrand')
        self.assertGreater(result.brand_score, 0)
        self.assertIn('Comp1', result.competitors)
        self.assertEqual(result.total_responses, 3)

    def test_empty_brand(self):
        """빈 브랜드명"""
        result = compare_llm_share('', ['Comp'], ['test'])
        self.assertEqual(result.brand, '')
        self.assertEqual(result.brand_score, 0.0)

    def test_none_responses(self):
        """responses가 None"""
        result = compare_llm_share('Brand', ['Comp'], None)
        self.assertEqual(result.total_responses, 0)
        self.assertEqual(result.brand_score, 0.0)

    def test_empty_responses(self):
        """빈 응답 목록"""
        result = compare_llm_share('Brand', ['Comp'], [])
        self.assertEqual(result.total_responses, 0)

    def test_no_competitors(self):
        """경쟁사 없는 경우"""
        result = compare_llm_share('Brand', [], ['Brand 소개'])
        self.assertEqual(result.competitors, {})
        self.assertGreater(result.brand_score, 0)

    def test_whitespace_brand(self):
        """공백만 있는 브랜드명"""
        result = compare_llm_share('  ', [], ['test'])
        self.assertEqual(result.brand, '')

    def test_blank_string_in_responses_filtered(self):
        """빈 문자열 응답 필터링"""
        result = compare_llm_share('Brand', [], ['Brand 좋아요', '', '  '])
        self.assertEqual(result.total_responses, 1)

    def test_analysis_summary_not_empty(self):
        """분석 요약이 항상 존재"""
        result = compare_llm_share('Brand', ['Comp'], ['Brand Comp 비교'])
        self.assertTrue(len(result.analysis_summary) > 0)

    def test_score_range(self):
        """점수가 0~100 범위"""
        responses = ['Brand ' * 50] * 10
        result = compare_llm_share('Brand', [], responses)
        self.assertGreaterEqual(result.brand_score, 0.0)
        self.assertLessEqual(result.brand_score, 100.0)

    def test_competitor_whitespace_filtered(self):
        """공백 경쟁사명 필터"""
        result = compare_llm_share('Brand', ['', '  ', 'Comp'], ['Brand Comp 비교'])
        self.assertNotIn('', result.competitors)
        self.assertIn('Comp', result.competitors)


if __name__ == '__main__':
    unittest.main()
