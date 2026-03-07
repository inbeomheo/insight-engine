"""Temporal Reference Checker 서비스 테스트."""
import unittest
from services.temporal_reference_checker_service import check_temporal_references


class TestTemporalReferenceChecker(unittest.TestCase):

    def test_empty_content(self):
        result = check_temporal_references('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = check_temporal_references(None)
        self.assertEqual(result['score'], 100.0)

    def test_consistent_past(self):
        content = ('프로젝트를 완료했습니다. 팀원들이 협력했습니다. '
                   '결과가 좋았습니다. 목표를 달성했습니다.')
        result = check_temporal_references(content)
        dist = result['summary']['tense_distribution']
        self.assertGreater(dist.get('past', 0), 0)

    def test_consistent_present(self):
        content = ('프로젝트를 진행합니다. 팀원들이 협력합니다. '
                   '결과가 좋습니다. 목표를 달성합니다.')
        result = check_temporal_references(content)
        dist = result['summary']['tense_distribution']
        self.assertGreater(dist.get('present', 0), 0)

    def test_mixed_tense(self):
        content = ('어제 프로젝트를 시작했습니다. 현재 진행합니다. '
                   '내일 완료할 것입니다. 지난주에 계획했습니다.')
        result = check_temporal_references(content)
        dist = result['summary']['tense_distribution']
        tense_types = sum(1 for k, v in dist.items() if k != 'neutral' and v > 0)
        self.assertGreaterEqual(tense_types, 2)

    def test_vague_time_korean(self):
        content = '최근 기술이 발전했습니다. 요즘 많이 사용됩니다. 곧 변화가 있을 것입니다.'
        result = check_temporal_references(content)
        self.assertGreater(result['summary']['vague_count'], 0)

    def test_vague_time_english(self):
        content = 'Recently, the technology has improved. Soon it will change everything.'
        result = check_temporal_references(content)
        self.assertGreater(result['summary']['vague_count'], 0)

    def test_consistency_score(self):
        content = ('계획을 세웠습니다. 실행했습니다. 결과를 확인했습니다. '
                   '보고서를 작성했습니다.')
        result = check_temporal_references(content)
        self.assertGreaterEqual(result['summary']['consistency'], 0.0)
        self.assertLessEqual(result['summary']['consistency'], 100.0)

    def test_level_consistent(self):
        content = ('결과를 확인했습니다. 데이터를 분석했습니다. '
                   '보고서를 작성했습니다. 발표를 진행했습니다.')
        result = check_temporal_references(content)
        self.assertEqual(result['summary']['level'], 'consistent')

    def test_tense_data_structure(self):
        content = '프로젝트를 진행합니다. 결과가 좋습니다.'
        result = check_temporal_references(content)
        for td in result['tense_data']:
            self.assertIn('text', td)
            self.assertIn('tense', td)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_temporal_references(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 문장입니다.'
        result = check_temporal_references(content)
        self.assertIn('tense_data', result)
        self.assertIn('vague_references', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('tense_distribution', result['summary'])
        self.assertIn('vague_count', result['summary'])
        self.assertIn('consistency', result['summary'])

    def test_suggestions_exist(self):
        content = '프로젝트를 진행합니다. 결과가 좋았습니다.'
        result = check_temporal_references(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_future_tense(self):
        content = ('새 기능을 추가할 것입니다. 성능을 개선하겠습니다. '
                   '사용자 경험을 높일 예정입니다.')
        result = check_temporal_references(content)
        dist = result['summary']['tense_distribution']
        self.assertGreater(dist.get('future', 0), 0)

    def test_max_30_tense_data(self):
        sentences = '. '.join([f'이것은 테스트 문장 번호 {i}입니다' for i in range(40)])
        content = sentences + '.'
        result = check_temporal_references(content)
        self.assertLessEqual(len(result['tense_data']), 30)


if __name__ == '__main__':
    unittest.main()
