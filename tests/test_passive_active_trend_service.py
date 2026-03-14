"""Passive-to-Active Ratio Trend 서비스 테스트."""
import unittest
from services.analysis.passive_active_trend_service import analyze_passive_active_trend


class TestPassiveActiveTrend(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_passive_active_trend('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_sections'], 0)

    def test_none_content(self):
        result = analyze_passive_active_trend(None)
        self.assertEqual(result['score'], 100.0)

    def test_all_active(self):
        content = ('# 서론\n나는 코드를 작성합니다. 팀이 리뷰합니다.\n'
                   '# 본론\n개발자가 테스트합니다. 매니저가 승인합니다.')
        result = analyze_passive_active_trend(content)
        self.assertLessEqual(result['summary']['overall_passive_ratio'], 20.0)

    def test_mixed_passive_active(self):
        content = ('# 서론\n프로젝트가 시작되었습니다. 팀이 구성됩니다.\n'
                   '# 본론\n개발자가 코드를 작성합니다. 테스터가 확인합니다.')
        result = analyze_passive_active_trend(content)
        self.assertGreater(result['summary']['overall_passive_ratio'], 0.0)

    def test_section_data_structure(self):
        content = ('# 파트1\n내용이 작성되었습니다. 결과가 나옵니다.\n'
                   '# 파트2\n분석이 진행됩니다. 보고서를 작성합니다.')
        result = analyze_passive_active_trend(content)
        for s in result['section_data']:
            self.assertIn('title', s)
            self.assertIn('sentences', s)
            self.assertIn('passive', s)
            self.assertIn('active', s)
            self.assertIn('passive_ratio', s)

    def test_hotspot_detection(self):
        content = ('# 능동 섹션\n팀이 작업합니다. 개발자가 코딩합니다.\n'
                   '# 피동 섹션\n결과가 도출되었습니다. 보고서가 작성되었습니다. '
                   '결정이 내려졌습니다. 계획이 수립되었습니다.')
        result = analyze_passive_active_trend(content)
        self.assertTrue(len(result['summary']['hotspot_section']) > 0)

    def test_trend_stable(self):
        sec = '팀이 작업합니다. 결과를 확인합니다.'
        content = f'# A\n{sec}\n# B\n{sec}\n# C\n{sec}'
        result = analyze_passive_active_trend(content)
        self.assertIn(result['summary']['trend'], ('stable', 'single'))

    def test_single_section(self):
        content = '헤딩 없는 텍스트입니다. 여러 문장이 있습니다.'
        result = analyze_passive_active_trend(content)
        self.assertEqual(result['summary']['trend'], 'single')

    def test_overall_passive_ratio(self):
        content = ('# 서론\n계획이 수립되었습니다. 목표가 설정되었습니다.\n'
                   '# 본론\n팀이 실행합니다.')
        result = analyze_passive_active_trend(content)
        self.assertGreater(result['summary']['overall_passive_ratio'], 0.0)

    def test_score_range(self):
        content = '# 제목\n내용입니다.'
        result = analyze_passive_active_trend(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '# 제목\n구조 확인입니다.'
        result = analyze_passive_active_trend(content)
        self.assertIn('section_data', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sections', result['summary'])
        self.assertIn('overall_passive_ratio', result['summary'])
        self.assertIn('trend', result['summary'])
        self.assertIn('hotspot_section', result['summary'])

    def test_suggestions_exist(self):
        content = ('# 서론\n결과가 도출되었습니다. 보고서가 작성되었습니다.\n'
                   '# 본론\n팀이 작업합니다.')
        result = analyze_passive_active_trend(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_intro_section(self):
        content = ('서론 부분입니다. 헤딩 전에 옵니다.\n'
                   '# 본문\n본문 내용입니다.')
        result = analyze_passive_active_trend(content)
        titles = [s['title'] for s in result['section_data']]
        self.assertIn('(서론)', titles)


if __name__ == '__main__':
    unittest.main()
