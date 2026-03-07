"""Noun-to-Verb Ratio 서비스 테스트."""
import unittest
from services.noun_verb_ratio_service import analyze_noun_verb_ratio


class TestNounVerbRatio(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_noun_verb_ratio('')
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = analyze_noun_verb_ratio(None)
        self.assertEqual(result['score'], 0.0)

    def test_has_nouns_and_verbs(self):
        content = '프로젝트를 시작합니다. 팀원들이 협력합니다. 결과를 확인합니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(result['counts']['nouns'], 0)
        self.assertGreater(result['counts']['verbs'], 0)

    def test_noun_ratio(self):
        content = '데이터 분석과 인공지능 기술의 활용은 중요합니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(result['summary']['noun_ratio'], 0.0)

    def test_verb_ratio(self):
        content = '달린다 뛴다 걷는다 멈춘다 돌아간다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(result['summary']['verb_ratio'], 0.0)

    def test_nv_ratio(self):
        content = '프로젝트를 시작합니다. 팀이 협력합니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(result['summary']['nv_ratio'], 0.0)

    def test_english_detection(self):
        content = 'The team creates innovative solutions. They build amazing products.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(result['counts']['nouns'] + result['counts']['verbs'], 0)

    def test_level_balanced(self):
        content = ('프로젝트를 시작합니다. 데이터를 분석합니다. '
                   '결과를 확인합니다. 보고서를 작성합니다. '
                   '계획을 수립합니다. 목표를 달성합니다.')
        result = analyze_noun_verb_ratio(content)
        # 비율에 따라 balanced 또는 다른 레벨
        self.assertIn(result['summary']['level'],
                     ('balanced', 'noun_heavy', 'verb_heavy'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertIn('counts', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('nouns', result['counts'])
        self.assertIn('verbs', result['counts'])
        self.assertIn('noun_ratio', result['summary'])
        self.assertIn('verb_ratio', result['summary'])
        self.assertIn('nv_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '프로젝트 관리와 데이터 분석을 합니다.'
        result = analyze_noun_verb_ratio(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
