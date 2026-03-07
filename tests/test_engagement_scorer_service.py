"""engagement_scorer_service 단위 테스트"""
import unittest

from services.engagement_scorer_service import (
    score_engagement,
)


class TestScoreEngagement(unittest.TestCase):

    def test_empty_content(self):
        result = score_engagement('')
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['grade'], 'F')

    def test_none_content(self):
        result = score_engagement(None)
        self.assertEqual(result['grade'], 'F')

    def test_basic_content(self):
        result = score_engagement('파이썬 프로그래밍 입문 가이드입니다.')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D', 'F'))

    def test_questions_boost(self):
        no_q = score_engagement('파이썬은 좋은 언어입니다.')
        with_q = score_engagement('파이썬은 좋은 언어입니다. 여러분은 어떻게 생각하시나요?')
        self.assertGreaterEqual(with_q['score'], no_q['score'])

    def test_cta_detected(self):
        result = score_engagement('지금 바로 시작해보세요! 구독하고 확인하세요.')
        self.assertGreater(result['breakdown']['cta']['score'], 0)

    def test_emotional_detected(self):
        result = score_engagement('놀라운 결과입니다. 감동적인 이야기입니다. 최고의 경험이었습니다.')
        self.assertGreater(result['breakdown']['emotional']['score'], 0)

    def test_structure_bonus(self):
        structured = '## 소개\n\n첫 문단.\n\n## 본론\n\n둘째 문단.\n\n## 결론\n\n셋째 문단.'
        result = score_engagement(structured)
        self.assertGreater(result['breakdown']['structure']['score'], 0)

    def test_visual_elements(self):
        result = score_engagement('- 항목 1\n- 항목 2\n- 항목 3\n\n1. 순서 1\n2. 순서 2')
        self.assertGreater(result['breakdown']['visuals']['score'], 0)

    def test_specificity_with_numbers(self):
        result = score_engagement('전년 대비 30% 성장했으며 100만 사용자를 달성했습니다.')
        self.assertGreater(result['breakdown']['specificity']['score'], 0)

    def test_strengths_and_weaknesses(self):
        result = score_engagement('간단한 텍스트.')
        self.assertIsInstance(result['strengths'], list)
        self.assertIsInstance(result['weaknesses'], list)

    def test_suggestions_exist(self):
        result = score_engagement('짧은 글.')
        self.assertGreater(len(result['suggestions']), 0)

    def test_high_engagement_content(self):
        content = """## 놀라운 파이썬 팁 5가지

여러분은 파이썬을 얼마나 잘 알고 있나요?

1. 리스트 컴프리헨션으로 코드를 50% 줄이세요
2. 데코레이터로 반복 코드를 제거하세요
3. f-string으로 가독성을 높이세요

실제 경험에서 이 팁들은 30% 생산성 향상을 가져왔습니다.

여러분의 경험을 댓글로 공유해주세요! 구독도 부탁드립니다."""
        result = score_engagement(content)
        self.assertGreaterEqual(result['score'], 40)
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D'))


if __name__ == '__main__':
    unittest.main()
