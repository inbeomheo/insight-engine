"""Passive Construction Ratio 서비스 테스트."""
import unittest
from services.analysis.passive_construction_ratio_service import analyze_passive_ratio


class TestPassiveConstructionRatio(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_passive_ratio('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['passive_count'], 0)

    def test_none_content(self):
        result = analyze_passive_ratio(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_passive(self):
        content = ('나는 매일 운동을 합니다. 그는 책을 읽습니다. '
                   '우리는 함께 공부합니다. 선생님이 수업을 진행합니다. '
                   '학생들이 질문을 합니다.')
        result = analyze_passive_ratio(content)
        self.assertEqual(result['summary']['passive_count'], 0)
        self.assertEqual(result['summary']['level'], 'low')

    def test_korean_passive_dwe(self):
        # ~되다 피동 감지
        content = ('결정이 내려졌습니다. 보고서가 작성되었습니다. '
                   '계획이 수립되고 있습니다. 회의가 진행됩니다.')
        result = analyze_passive_ratio(content)
        self.assertGreater(result['summary']['passive_count'], 0)

    def test_korean_passive_bat(self):
        # ~받다 피동 감지
        content = ('그는 칭찬을 받았습니다. 학생이 상을 받고 있습니다. '
                   '직원들이 교육을 받는 중입니다.')
        result = analyze_passive_ratio(content)
        self.assertGreater(result['summary']['passive_count'], 0)

    def test_korean_passive_dang(self):
        # ~당하다 피동 감지
        content = ('그는 사기를 당했습니다. 피해자가 폭행을 당하는 사건이 발생했습니다. '
                   '회사가 해킹을 당한 것으로 밝혀졌습니다.')
        result = analyze_passive_ratio(content)
        self.assertGreater(result['summary']['passive_count'], 0)

    def test_english_passive(self):
        content = ('The report was written by the team. '
                   'The decision was made yesterday. '
                   'Errors were found in the system.')
        result = analyze_passive_ratio(content)
        self.assertGreater(result['summary']['passive_count'], 0)

    def test_mixed_active_passive(self):
        content = ('나는 보고서를 작성합니다. 보고서가 검토되었습니다. '
                   '팀장이 피드백을 줍니다. 수정이 완료됩니다. '
                   '최종본을 제출합니다. 결과가 발표되었습니다. '
                   '고객이 만족합니다. 프로젝트가 종료됩니다. '
                   '새 과제를 시작합니다. 예산이 확정되었습니다.')
        result = analyze_passive_ratio(content)
        ratio = result['summary']['passive_ratio']
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 100.0)

    def test_level_low(self):
        # 대부분 능동문
        content = ('나는 코드를 작성합니다. 팀이 리뷰합니다. '
                   '개발자가 테스트합니다. 매니저가 승인합니다. '
                   '기획자가 요구사항을 정리합니다. 디자이너가 UI를 설계합니다. '
                   '결과가 배포되었습니다.')
        result = analyze_passive_ratio(content)
        self.assertEqual(result['summary']['level'], 'low')

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다. 여러 문장이 포함되어 있습니다.'
        result = analyze_passive_ratio(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 테스트 문장입니다.'
        result = analyze_passive_ratio(content)
        self.assertIn('passive_sentences', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('passive_count', result['summary'])
        self.assertIn('passive_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_passive_sentences_list(self):
        content = ('계획이 수립되었습니다. 보고서가 작성되었습니다. '
                   '결과가 발표되었습니다.')
        result = analyze_passive_ratio(content)
        for item in result['passive_sentences']:
            self.assertIn('text', item)

    def test_suggestions_for_high_passive(self):
        # 모든 문장이 피동
        content = ('계획이 수립되었습니다. 보고서가 작성되었습니다. '
                   '결과가 발표되었습니다. 문제가 해결되었습니다. '
                   '시스템이 업데이트되었습니다.')
        result = analyze_passive_ratio(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
