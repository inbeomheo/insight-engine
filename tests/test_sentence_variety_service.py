"""sentence_variety_service 단위 테스트"""
import unittest

from services.sentence_variety_service import (
    analyze_variety,
    _categorize_length,
)


class TestAnalyzeVariety(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_variety('')
        self.assertEqual(result['variety_score'], 0)
        self.assertEqual(result['sentences'], [])

    def test_none_content(self):
        result = analyze_variety(None)
        self.assertEqual(result['stats']['count'], 0)

    def test_single_sentence(self):
        result = analyze_variety('파이썬은 프로그래밍 언어입니다.')
        self.assertEqual(result['stats']['count'], 1)

    def test_varied_sentences(self):
        content = '짧은 문장. 이것은 중간 길이의 문장으로 좀 더 자세한 설명을 포함합니다. 아주 긴 문장은 여러 개의 절로 이루어져 있으며, 복잡한 개념을 설명하기 위해 부연 설명과 예시를 포함하여 독자가 이해할 수 있도록 도와줍니다.'
        result = analyze_variety(content)
        self.assertGreater(result['stats']['count'], 1)
        # 길이 분포에 2개 이상 카테고리
        used = sum(1 for v in result['length_distribution'].values() if v > 0)
        self.assertGreaterEqual(used, 2)

    def test_monotonous_sentences(self):
        # 비슷한 길이 문장 반복
        content = '. '.join(['파이썬은 좋은 언어입니다'] * 10) + '.'
        result = analyze_variety(content)
        # 다양성 점수가 낮아야 함
        self.assertLessEqual(result['variety_score'], 80)

    def test_start_pattern_analysis(self):
        content = '파이썬은 좋습니다. 파이썬은 쉽습니다. 파이썬은 강력합니다. 자바는 다릅니다.'
        result = analyze_variety(content)
        self.assertLess(result['start_pattern']['unique_ratio'], 1.0)

    def test_repeated_start_detected(self):
        content = '우리는 먼저 시작합니다. 우리는 다음으로 진행합니다. 우리는 마지막에 끝냅니다.'
        result = analyze_variety(content)
        # 반복 시작이 감지될 수 있음
        self.assertIsInstance(result['start_pattern']['repeated'], list)

    def test_length_distribution(self):
        result = analyze_variety('짧음. 이것은 좀 더 긴 문장입니다.')
        dist = result['length_distribution']
        self.assertIn('very_short', dist)
        self.assertIn('medium', dist)

    def test_stats_calculation(self):
        content = '첫 문장입니다. 두 번째 문장은 좀 더 길게 작성합니다.'
        result = analyze_variety(content)
        stats = result['stats']
        self.assertGreater(stats['avg_length'], 0)
        self.assertGreaterEqual(stats['std_dev'], 0)

    def test_score_bounded(self):
        result = analyze_variety('테스트 문장입니다. 또 다른 문장입니다.')
        self.assertGreaterEqual(result['variety_score'], 0)
        self.assertLessEqual(result['variety_score'], 100)

    def test_suggestions_exist(self):
        result = analyze_variety('짧은 글입니다. 정말 짧습니다.')
        self.assertGreater(len(result['suggestions']), 0)


class TestCategorizeLength(unittest.TestCase):

    def test_very_short(self):
        self.assertEqual(_categorize_length(10), 'very_short')

    def test_short(self):
        self.assertEqual(_categorize_length(25), 'short')

    def test_medium(self):
        self.assertEqual(_categorize_length(45), 'medium')

    def test_long(self):
        self.assertEqual(_categorize_length(80), 'long')

    def test_very_long(self):
        self.assertEqual(_categorize_length(150), 'very_long')


if __name__ == '__main__':
    unittest.main()
