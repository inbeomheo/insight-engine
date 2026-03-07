"""Data Visualization Opportunity 서비스 테스트."""
import unittest
from services.data_visualization_opportunity_service import find_visualization_opportunities


class TestDataVisualizationOpportunity(unittest.TestCase):

    def test_empty_content(self):
        result = find_visualization_opportunities('')
        self.assertEqual(result['summary']['total_opportunities'], 0)

    def test_none_content(self):
        result = find_visualization_opportunities(None)
        self.assertEqual(result['summary']['total_opportunities'], 0)

    def test_no_data(self):
        content = '이 글에는 숫자나 데이터가 없습니다. 순수 텍스트입니다.'
        result = find_visualization_opportunities(content)
        self.assertEqual(result['summary']['total_opportunities'], 0)

    def test_comparison_data(self):
        content = '매출이 30% 증가했고 비용은 15% 감소했습니다.'
        result = find_visualization_opportunities(content)
        self.assertGreater(result['summary']['total_opportunities'], 0)

    def test_trend_data(self):
        content = '전년 대비 매출이 20% 성장하는 추세입니다.'
        result = find_visualization_opportunities(content)
        types = result['summary']['chart_types']
        self.assertIn('trend', types)

    def test_proportion_data(self):
        content = '시장 점유율은 A사 35%, B사 28%, C사 22%입니다.'
        result = find_visualization_opportunities(content)
        types = result['summary']['chart_types']
        self.assertIn('proportion', types)

    def test_ranking_data(self):
        content = '사용자 만족도 1위는 A제품입니다. 2위는 B제품, 3위는 C제품입니다.'
        result = find_visualization_opportunities(content)
        types = result['summary']['chart_types']
        self.assertIn('ranking', types)

    def test_number_density(self):
        content = '매출 100억원, 영업이익 20억원, 순이익 15억원을 기록했습니다.'
        result = find_visualization_opportunities(content)
        self.assertGreater(result['summary']['number_density'], 0.0)

    def test_multiple_opportunities(self):
        content = ('매출이 30% 증가하고 비용은 15% 감소했습니다. '
                   '전년 대비 20% 성장 추세입니다. '
                   '시장 점유율 1위는 A사입니다.')
        result = find_visualization_opportunities(content)
        self.assertGreaterEqual(result['summary']['total_opportunities'], 2)

    def test_level_rich(self):
        content = ('매출 100억원 대비 비용 50억원입니다. '
                   '전년 대비 30% 성장 추세입니다. '
                   '시장 점유율 1위 A사 40%, 2위 B사 30%입니다. '
                   '고객 만족도는 85%에서 92%로 증가했습니다. '
                   '직원 수는 200명에서 300명으로 늘었습니다.')
        result = find_visualization_opportunities(content)
        self.assertIn(result['summary']['level'], ('rich', 'moderate'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = find_visualization_opportunities(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '매출이 20% 증가했습니다.'
        result = find_visualization_opportunities(content)
        self.assertIn('opportunities', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_opportunities', result['summary'])
        self.assertIn('chart_types', result['summary'])
        self.assertIn('number_density', result['summary'])

    def test_opportunity_structure(self):
        content = '매출 30% 대비 비용 15% 감소했습니다.'
        result = find_visualization_opportunities(content)
        for opp in result['opportunities']:
            self.assertIn('type', opp)
            self.assertIn('chart', opp)
            self.assertIn('reason', opp)

    def test_suggestions_exist(self):
        content = '매출이 20% 증가했습니다.'
        result = find_visualization_opportunities(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_max_20_opportunities(self):
        lines = [f'항목{i}는 {i*5}% 대비 {i*3}%로 감소했습니다.' for i in range(25)]
        content = ' '.join(lines)
        result = find_visualization_opportunities(content)
        self.assertLessEqual(len(result['opportunities']), 20)


if __name__ == '__main__':
    unittest.main()
