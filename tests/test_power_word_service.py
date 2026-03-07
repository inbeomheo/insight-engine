"""power_word_service 단위 테스트"""
import unittest

from services.power_word_service import (
    analyze_power_words,
    suggest_power_words,
    get_power_word_categories,
)


class TestAnalyzePowerWords(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_power_words('')
        self.assertEqual(result['found'], [])
        self.assertEqual(result['score'], 0)

    def test_none_content(self):
        result = analyze_power_words(None)
        self.assertEqual(result['summary']['total_found'], 0)

    def test_no_power_words(self):
        result = analyze_power_words('일반적인 내용의 문장입니다.')
        # 파워워드 없을 수 있음
        self.assertIsInstance(result['found'], list)

    def test_urgency_detected(self):
        result = analyze_power_words('지금 바로 시작하세요. 마감이 임박했습니다.')
        categories = result['summary']['categories']
        self.assertIn('urgency', categories)

    def test_emotion_detected(self):
        result = analyze_power_words('감동적인 순간이었습니다. 행복한 결말이 기다리고 있습니다.')
        categories = result['summary']['categories']
        self.assertIn('emotion', categories)

    def test_trust_detected(self):
        result = analyze_power_words('검증된 데이터에 기반한 연구 결과입니다.')
        categories = result['summary']['categories']
        self.assertIn('trust', categories)

    def test_density_calculation(self):
        content = '무료 할인 혜택을 지금 바로 받으세요. 이 기회를 놓치지 마세요.'
        result = analyze_power_words(content)
        self.assertGreater(result['summary']['density'], 0)

    def test_score_bounded(self):
        result = analyze_power_words('테스트 콘텐츠입니다.')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_suggestions_exist(self):
        result = analyze_power_words('일반적인 텍스트로 파워워드가 적은 콘텐츠입니다.')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_multiple_categories(self):
        content = '지금 시작하세요. 검증된 방법으로 성공을 달성하세요. 놀라운 결과가 기다립니다.'
        result = analyze_power_words(content)
        self.assertGreaterEqual(len(result['summary']['categories']), 2)


class TestSuggestPowerWords(unittest.TestCase):

    def test_default_goal(self):
        result = suggest_power_words('테스트 콘텐츠')
        self.assertEqual(result['goal'], 'engagement')
        self.assertGreater(len(result['words']), 0)

    def test_conversion_goal(self):
        result = suggest_power_words('테스트', 'conversion')
        self.assertEqual(result['goal'], 'conversion')
        cats = [c['id'] for c in result['recommended_categories']]
        self.assertIn('urgency', cats)

    def test_invalid_goal_defaults(self):
        result = suggest_power_words('테스트', 'invalid')
        self.assertEqual(result['goal'], 'engagement')

    def test_excludes_used_words(self):
        # 이미 '지금'이 콘텐츠에 있으면 추천에서 제외
        result = suggest_power_words('지금 시작하는 방법', 'conversion')
        self.assertNotIn('지금', result['words'])


class TestGetCategories(unittest.TestCase):

    def test_returns_categories(self):
        cats = get_power_word_categories()
        self.assertGreater(len(cats), 0)
        self.assertTrue(all('id' in c and 'label' in c for c in cats))

    def test_has_examples(self):
        cats = get_power_word_categories()
        for cat in cats:
            self.assertGreater(len(cat['examples']), 0)


if __name__ == '__main__':
    unittest.main()
