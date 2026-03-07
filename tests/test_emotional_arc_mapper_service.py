"""Emotional Arc Mapper 서비스 테스트."""
import unittest
from services.emotional_arc_mapper_service import map_emotional_arc


class TestEmotionalArcMapper(unittest.TestCase):

    def test_empty_content(self):
        result = map_emotional_arc('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['total_sections'], 0)

    def test_none_content(self):
        result = map_emotional_arc(None)
        self.assertEqual(result['score'], 50.0)

    def test_positive_content(self):
        content = """# 좋은 소식
훌륭한 결과입니다. 뛰어난 성과를 달성했습니다. 효과적인 방법입니다."""
        result = map_emotional_arc(content)
        self.assertEqual(result['summary']['overall_tone'], 'positive')

    def test_negative_content(self):
        content = """# 문제 분석
위험한 상황입니다. 실패 사례가 많습니다. 취약한 부분이 있습니다. 오류가 발생합니다."""
        result = map_emotional_arc(content)
        self.assertEqual(result['summary']['overall_tone'], 'negative')

    def test_neutral_content(self):
        content = '일반적인 설명입니다. 정보를 전달합니다. 내용을 기술합니다.'
        result = map_emotional_arc(content)
        self.assertEqual(result['summary']['overall_tone'], 'neutral')

    def test_multi_section_arc(self):
        content = """# 문제
위험하고 어려운 상황입니다. 실패가 반복됩니다.

# 해결
좋은 방법을 찾았습니다. 뛰어난 성과가 나왔습니다. 효과적입니다."""
        result = map_emotional_arc(content)
        self.assertEqual(result['summary']['total_sections'], 2)
        self.assertEqual(len(result['arc']), 2)

    def test_arc_structure(self):
        content = """# 섹션
좋은 내용입니다."""
        result = map_emotional_arc(content)
        if result['arc']:
            a = result['arc'][0]
            self.assertIn('section', a)
            self.assertIn('title', a)
            self.assertIn('sentiment', a)
            self.assertIn('tone', a)

    def test_arc_pattern_detection(self):
        content = """# 문제 제기
위험하고 나쁜 상황입니다. 문제가 심각합니다.

# 전환
조금 나아졌습니다.

# 해결
좋은 결과입니다. 훌륭한 성과를 달성했습니다. 효과적이고 안전합니다."""
        result = map_emotional_arc(content)
        self.assertIn(result['summary']['arc_pattern'],
                      ('ascending', 'v_shape', 'fluctuating', 'dramatic'))

    def test_flat_pattern(self):
        content = '일반 내용입니다. 보통 설명입니다. 평범한 글입니다.'
        result = map_emotional_arc(content)
        self.assertEqual(result['summary']['arc_pattern'], 'flat')

    def test_score_range(self):
        content = '테스트 콘텐츠입니다.'
        result = map_emotional_arc(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '간단한 글입니다.'
        result = map_emotional_arc(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다.'
        result = map_emotional_arc(content)
        self.assertIn('arc', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('overall_tone', result['summary'])
        self.assertIn('arc_pattern', result['summary'])


if __name__ == '__main__':
    unittest.main()
