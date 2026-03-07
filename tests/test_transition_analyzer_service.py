"""transition_analyzer_service 단위 테스트"""
import unittest

from services.transition_analyzer_service import (
    analyze_transitions,
    suggest_transitions,
    get_transition_categories,
)


class TestAnalyzeTransitions(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_transitions('')
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['score'], 0)

    def test_none_content(self):
        result = analyze_transitions(None)
        self.assertEqual(result['summary']['total'], 0)

    def test_single_paragraph(self):
        result = analyze_transitions('단일 문단입니다. 연결어 분석 불필요.')
        self.assertEqual(result['score'], 100)

    def test_detects_addition(self):
        content = '첫 번째 내용입니다.\n또한 두 번째 내용도 있습니다.'
        result = analyze_transitions(content)
        self.assertGreater(result['summary']['total'], 0)
        categories = result['summary']['categories']
        self.assertIn('addition', categories)

    def test_detects_contrast(self):
        content = '파이썬은 쉬운 언어입니다.\n그러나 모든 상황에 적합하지는 않습니다.'
        result = analyze_transitions(content)
        categories = result['summary']['categories']
        self.assertIn('contrast', categories)

    def test_detects_cause(self):
        content = '코드 품질이 중요합니다.\n따라서 테스트를 작성해야 합니다.'
        result = analyze_transitions(content)
        categories = result['summary']['categories']
        self.assertIn('cause', categories)

    def test_detects_example(self):
        content = '다양한 언어가 있습니다.\n예를 들어 파이썬과 자바가 있습니다.'
        result = analyze_transitions(content)
        categories = result['summary']['categories']
        self.assertIn('example', categories)

    def test_detects_conclusion(self):
        content = '여러 내용을 다루었습니다.\n결론적으로 이 방법이 최선입니다.'
        result = analyze_transitions(content)
        categories = result['summary']['categories']
        self.assertIn('conclusion', categories)

    def test_paragraph_analysis(self):
        content = '첫 문단입니다.\n또한 두 번째입니다.\n세 번째 문단입니다.'
        result = analyze_transitions(content)
        self.assertEqual(len(result['paragraph_analysis']), 3)
        self.assertTrue(result['paragraph_analysis'][1]['has_transition'])
        self.assertFalse(result['paragraph_analysis'][2]['has_transition'])

    def test_score_bounded(self):
        content = '문단 하나.\n문단 둘.\n문단 셋.'
        result = analyze_transitions(content)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_multiple_categories_score_bonus(self):
        content = '첫 문단입니다.\n또한 추가 내용.\n그러나 반대 의견도 있습니다.\n따라서 종합하면 이렇습니다.'
        result = analyze_transitions(content)
        # 3개 카테고리 사용 시 높은 점수
        self.assertGreater(result['score'], 60)

    def test_density_calculation(self):
        content = '첫 문단입니다.\n또한 두 번째.\n그러나 셋째.'
        result = analyze_transitions(content)
        self.assertGreater(result['summary']['density'], 0)


class TestSuggestTransitions(unittest.TestCase):

    def test_empty_content(self):
        result = suggest_transitions('')
        self.assertEqual(result['recommendations'], [])

    def test_suggestions_for_missing(self):
        content = '첫 문단입니다.\n두 번째 문단입니다.\n세 번째 문단입니다.'
        result = suggest_transitions(content)
        # 두 번째, 세 번째 문단에 연결어 없으므로 추천
        self.assertGreater(len(result['recommendations']), 0)

    def test_no_suggestion_for_first_paragraph(self):
        content = '첫 문단입니다.\n두 번째 문단.'
        result = suggest_transitions(content)
        # 첫 문단은 추천에 포함되지 않음
        para_indices = [r['paragraph'] for r in result['recommendations']]
        self.assertNotIn(0, para_indices)

    def test_general_tips(self):
        result = suggest_transitions('테스트 콘텐츠')
        self.assertGreater(len(result['general_tips']), 0)

    def test_context_preview(self):
        content = '첫 문단입니다.\n이것은 연결어 없는 두 번째 문단인데 내용이 길어서 미리보기가 잘립니다.'
        result = suggest_transitions(content)
        if result['recommendations']:
            self.assertIn('context', result['recommendations'][0])


class TestGetTransitionCategories(unittest.TestCase):

    def test_returns_categories(self):
        cats = get_transition_categories()
        self.assertGreater(len(cats), 0)
        self.assertTrue(all('id' in c and 'label' in c for c in cats))

    def test_has_examples(self):
        cats = get_transition_categories()
        for cat in cats:
            self.assertGreater(len(cat['examples']), 0)

    def test_known_categories(self):
        cats = get_transition_categories()
        ids = [c['id'] for c in cats]
        self.assertIn('addition', ids)
        self.assertIn('contrast', ids)
        self.assertIn('cause', ids)


if __name__ == '__main__':
    unittest.main()
