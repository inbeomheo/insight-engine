"""정서적 미충족 분석 서비스 테스트"""
import unittest
from services.emotional_unmet_service import (
    analyze_needs, identify_gaps, suggest_improvements,
    EmotionalNeed, UnmetAnalysis
)


class TestEmotionalUnmetService(unittest.TestCase):

    def test_analyze_needs_with_keywords(self):
        content = '우리 팀은 함께 성장하며 목표를 달성합니다.'
        analysis = analyze_needs(content)
        self.assertIsInstance(analysis, UnmetAnalysis)
        self.assertEqual(len(analysis.needs), 5)

    def test_analyze_needs_belonging_addressed(self):
        content = '함께 커뮤니티를 만들어갑시다.'
        analysis = analyze_needs(content)
        belonging = [n for n in analysis.needs if n.need_type == 'belonging'][0]
        self.assertTrue(belonging.addressed)

    def test_analyze_needs_unmet(self):
        content = '평범한 텍스트입니다.'
        analysis = analyze_needs(content)
        self.assertGreater(analysis.unmet_count, 0)

    def test_identify_gaps(self):
        needs = [
            EmotionalNeed('belonging', 0.5, True),
            EmotionalNeed('achievement', 0.0, False),
            EmotionalNeed('security', 0.3, True),
        ]
        analysis = UnmetAnalysis('', needs, 1, [])
        gaps = identify_gaps(analysis)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].need_type, 'achievement')

    def test_suggest_improvements_for_unmet(self):
        needs = [
            EmotionalNeed('belonging', 0.0, False),
            EmotionalNeed('growth', 0.0, False),
        ]
        analysis = UnmetAnalysis('', needs, 2, [])
        suggestions = suggest_improvements(analysis)
        self.assertEqual(len(suggestions), 2)

    def test_suggest_improvements_no_gaps(self):
        needs = [EmotionalNeed('belonging', 1.0, True)]
        analysis = UnmetAnalysis('', needs, 0, [])
        suggestions = suggest_improvements(analysis)
        self.assertEqual(len(suggestions), 0)

    def test_analyze_needs_all_addressed(self):
        content = '함께 성취하며 안전하게 발전하고 학습하며 인정받는 팀'
        analysis = analyze_needs(content)
        addressed = [n for n in analysis.needs if n.addressed]
        self.assertEqual(len(addressed), 5)

    def test_analyze_needs_intensity_range(self):
        analysis = analyze_needs('팀과 함께 목표를 달성합니다.')
        for need in analysis.needs:
            self.assertGreaterEqual(need.intensity, 0.0)
            self.assertLessEqual(need.intensity, 1.0)

    def test_analyze_needs_empty_content(self):
        analysis = analyze_needs('')
        self.assertEqual(analysis.unmet_count, 5)

    def test_suggest_improvements_contains_tips(self):
        needs = [EmotionalNeed('security', 0.0, False)]
        analysis = UnmetAnalysis('', needs, 1, [])
        suggestions = suggest_improvements(analysis)
        self.assertTrue(any('안전' in s or '신뢰' in s for s in suggestions))


if __name__ == '__main__':
    unittest.main()
