"""Statistics Coverage Analyzer 서비스 단위 테스트"""
import unittest
from services.statistics_coverage_service import analyze_statistics_coverage


class TestStatisticsCoverageService(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠 입력"""
        result = analyze_statistics_coverage('')
        self.assertEqual(result['statistics'], [])
        self.assertEqual(result['summary']['total_stats'], 0)
        self.assertEqual(result['score'], 0.0)
        result_none = analyze_statistics_coverage(None)
        self.assertEqual(result_none['statistics'], [])

    def test_no_statistics(self):
        """수치가 없는 콘텐츠"""
        content = '## 소개\n이것은 일반적인 설명 글입니다.\n좋은 결과를 기대합니다.'
        result = analyze_statistics_coverage(content)
        self.assertEqual(result['summary']['total_stats'], 0)
        self.assertTrue(any('수치 근거' in s for s in result['suggestions']))

    def test_percentage_detection(self):
        """퍼센트 패턴 감지"""
        content = '## 결과\n성능이 80% 향상되었습니다.'
        result = analyze_statistics_coverage(content)
        pct = [s for s in result['statistics'] if s['type'] == 'percentage']
        self.assertGreater(len(pct), 0)

    def test_currency_detection(self):
        """금액 패턴 감지"""
        content = '## 비용\n총 비용은 500만원입니다. 또한 $1000 추가됩니다.'
        result = analyze_statistics_coverage(content)
        curr = [s for s in result['statistics'] if s['type'] == 'currency']
        self.assertGreaterEqual(len(curr), 1)

    def test_year_detection(self):
        """연도 패턴 감지"""
        content = '## 역사\n2020년에 시작되었고 2023년에 완성되었습니다.'
        result = analyze_statistics_coverage(content)
        years = [s for s in result['statistics'] if s['type'] == 'year']
        self.assertGreaterEqual(len(years), 2)

    def test_quantity_detection(self):
        """수량 패턴 감지"""
        content = '## 규모\n직원 500명이 참여하고 100건의 프로젝트를 완료했습니다.'
        result = analyze_statistics_coverage(content)
        qty = [s for s in result['statistics'] if s['type'] == 'quantity']
        self.assertGreaterEqual(len(qty), 2)

    def test_section_coverage(self):
        """섹션별 커버리지 분석"""
        content = (
            '## 성과\n매출이 50% 증가했습니다.\n\n'
            '## 과제\n아직 해결해야 할 문제가 있습니다.\n\n'
            '## 전망\n2025년까지 100명 채용 목표입니다.\n'
        )
        result = analyze_statistics_coverage(content)
        self.assertEqual(result['summary']['total_sections'], 3)
        self.assertEqual(result['summary']['sections_with_stats'], 2)
        # "과제" 섹션은 수치 없음
        weak = [sc for sc in result['section_coverage'] if not sc['has_stats']]
        self.assertGreater(len(weak), 0)

    def test_weak_sections(self):
        """수치 없는 섹션 제안"""
        content = '## 소개\n일반적인 설명입니다.\n\n## 데이터\n성장률 30%.'
        result = analyze_statistics_coverage(content)
        self.assertTrue(any('수치가 없는 섹션' in s for s in result['suggestions']))

    def test_score_range(self):
        """점수가 0-100 범위"""
        content = '## 테스트\n50% 성장.'
        result = analyze_statistics_coverage(content)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_coverage_rate(self):
        """커버리지 비율 정확성"""
        content = (
            '## A\n숫자 100개.\n\n'
            '## B\n숫자 200명.\n\n'
            '## C\n숫자 없음.\n'
        )
        result = analyze_statistics_coverage(content)
        # 3섹션 중 2섹션 = 66.7%
        self.assertAlmostEqual(result['summary']['coverage_rate'], 66.7, places=1)

    def test_suggestions(self):
        """제안이 비어있지 않음"""
        content = '## 설명\n일반 텍스트입니다.'
        result = analyze_statistics_coverage(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        """반환값 구조 검증"""
        result = analyze_statistics_coverage('## A\n50% 증가.')
        self.assertIn('statistics', result)
        self.assertIn('section_coverage', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_stats', result['summary'])
        self.assertIn('sections_with_stats', result['summary'])
        self.assertIn('total_sections', result['summary'])
        self.assertIn('coverage_rate', result['summary'])

    def test_multiplier_detection(self):
        """배수 패턴 감지"""
        content = '## 성과\n성능이 3배 향상되었습니다.'
        result = analyze_statistics_coverage(content)
        mult = [s for s in result['statistics'] if s['type'] == 'multiplier']
        self.assertGreater(len(mult), 0)


if __name__ == '__main__':
    unittest.main()
