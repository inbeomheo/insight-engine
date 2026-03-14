"""Conclusion Strength Analyzer 서비스 테스트."""
import unittest
from services.analysis.conclusion_strength_service import analyze_conclusion_strength


class TestConclusionStrengthAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_conclusion_strength('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['strength_level'], 'none')

    def test_none_content(self):
        result = analyze_conclusion_strength(None)
        self.assertEqual(result['score'], 0.0)

    def test_strong_conclusion_korean(self):
        content = """# 본문
여기에 본문 내용이 있습니다. 많은 정보를 담고 있습니다.

# 결론
요약하면 이 글의 핵심은 품질입니다. 가장 중요한 것은 사용자 경험입니다.
앞으로 더 발전할 것입니다. 지금 바로 시작하세요."""
        result = analyze_conclusion_strength(content)
        self.assertEqual(result['elements']['conclusion_heading'], True)
        self.assertGreaterEqual(result['summary']['element_count'], 3)
        self.assertEqual(result['summary']['strength_level'], 'strong')

    def test_weak_conclusion(self):
        content = '짧은 글입니다. 더 이상 할 말이 없습니다.'
        result = analyze_conclusion_strength(content)
        self.assertIn(result['summary']['strength_level'], ('weak', 'none'))

    def test_conclusion_heading_detection(self):
        content = """# 서론
내용입니다.

# 마무리
마무리 내용입니다."""
        result = analyze_conclusion_strength(content)
        self.assertTrue(result['elements']['conclusion_heading'])

    def test_no_conclusion_heading(self):
        content = '본문만 있는 글입니다. 제목이 없습니다.'
        result = analyze_conclusion_strength(content)
        self.assertFalse(result['elements']['conclusion_heading'])

    def test_summary_signal(self):
        # 마지막 20%에 패턴이 있도록 충분한 텍스트 + 결론 헤딩 사용
        content = """# 본문
긴 본문 내용입니다. 여러 문단이 있습니다. 다양한 주제를 다룹니다.

# 결론
요약하면 이 글의 핵심 내용은 다음과 같습니다."""
        result = analyze_conclusion_strength(content)
        self.assertTrue(result['elements']['summary_statement'])

    def test_cta_signal(self):
        content = """# 본문
긴 본문 내용입니다. 여러 문단이 있습니다. 다양한 주제를 다룹니다.

# 결론
지금 바로 시도해 보세요. 새로운 경험이 될 것입니다."""
        result = analyze_conclusion_strength(content)
        self.assertTrue(result['elements']['call_to_action'])

    def test_forward_looking_signal(self):
        content = """# 본문
긴 본문 내용입니다. 여러 문단이 있습니다. 다양한 주제를 다룹니다.

# 결론
앞으로 더 많은 기능이 추가될 예정입니다."""
        result = analyze_conclusion_strength(content)
        self.assertTrue(result['elements']['forward_looking'])

    def test_reaffirmation_signal(self):
        content = """# 본문
긴 본문 내용입니다. 여러 문단이 있습니다. 다양한 주제를 다룹니다.

# 결론
가장 중요한 것은 꾸준한 노력입니다."""
        result = analyze_conclusion_strength(content)
        self.assertTrue(result['elements']['key_reaffirmation'])

    def test_english_conclusion(self):
        content = """# Introduction
Some content here.

# Conclusion
In summary, quality matters most. Try it today to get started.
Moving forward, we expect growth. Most importantly, user experience is key."""
        result = analyze_conclusion_strength(content)
        self.assertGreaterEqual(result['summary']['element_count'], 3)

    def test_score_range(self):
        content = '아무 결론 요소도 없는 평범한 글입니다.'
        result = analyze_conclusion_strength(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '간단한 글입니다.'
        result = analyze_conclusion_strength(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트 콘텐츠입니다.'
        result = analyze_conclusion_strength(content)
        self.assertIn('elements', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('element_count', result['summary'])
        self.assertIn('strength_level', result['summary'])


if __name__ == '__main__':
    unittest.main()
