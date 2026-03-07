"""Actionability Gap Detector 서비스 테스트."""
import unittest
from services.actionability_gap_service import detect_actionability_gaps


class TestActionabilityGapDetector(unittest.TestCase):
    """detect_actionability_gaps 함수 테스트."""

    def test_empty_content(self):
        result = detect_actionability_gaps('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_advice'], 0)
        self.assertEqual(result['section_analysis'], [])

    def test_none_content(self):
        result = detect_actionability_gaps(None)
        self.assertEqual(result['score'], 100.0)

    def test_whitespace_content(self):
        result = detect_actionability_gaps('   \n\n  ')
        self.assertEqual(result['score'], 100.0)

    def test_no_advice_no_actions(self):
        content = '오늘은 날씨가 좋습니다. 공원에서 산책을 즐겼습니다.'
        result = detect_actionability_gaps(content)
        self.assertEqual(result['summary']['total_advice'], 0)
        self.assertEqual(result['summary']['total_actions'], 0)

    def test_advice_with_actions_korean(self):
        content = """## 설정 가이드
테스트 작성이 중요합니다.
먼저 프레임워크를 설치하세요.
다음으로 설정 파일을 생성하세요.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(result['summary']['total_advice'], 0)
        self.assertGreater(result['summary']['total_actions'], 0)
        self.assertFalse(any(s['has_gap'] for s in result['section_analysis']))

    def test_advice_without_actions_korean(self):
        content = """## 코드 품질
코드 품질 관리가 중요합니다. 테스트를 작성해야 합니다.
리팩토링을 고려해야 합니다. 코드 리뷰가 필요합니다.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(result['summary']['total_advice'], 0)
        gap_sections = [s for s in result['section_analysis'] if s['has_gap']]
        self.assertGreater(len(gap_sections), 0)

    def test_advice_with_actions_english(self):
        content = """## Setup Guide
You should install the framework.
First, run the install command.
Then, configure the settings.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(result['summary']['total_advice'], 0)
        self.assertGreater(result['summary']['total_actions'], 0)

    def test_advice_without_actions_english(self):
        content = """## Best Practices
You should follow best practices.
It is important to write tests.
You must consider performance.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(result['summary']['total_advice'], 0)
        gap_sections = [s for s in result['section_analysis'] if s['has_gap']]
        self.assertGreater(len(gap_sections), 0)

    def test_multiple_sections_mixed(self):
        content = """## 소개
테스트가 중요합니다.

## 설치 방법
먼저 npm을 설치하세요.
다음으로 프로젝트를 생성하세요.

## 주의사항
성능 최적화를 고려해야 합니다.
보안을 확인해야 합니다.
"""
        result = detect_actionability_gaps(content)
        analysis = result['section_analysis']
        self.assertGreater(len(analysis), 1)
        self.assertGreater(result['summary']['gap_sections'], 0)

    def test_score_high_with_actions(self):
        content = """## 가이드
테스트 작성이 중요합니다.
먼저 Jest를 설치하세요.
다음으로 테스트 파일을 생성하세요.
마지막으로 npm test를 실행하세요.
"""
        result = detect_actionability_gaps(content)
        self.assertGreaterEqual(result['score'], 50.0)

    def test_score_low_without_actions(self):
        content = """## 원칙
코드 품질이 중요합니다.
유지보수가 필요합니다.
테스트를 해야 합니다.
리팩토링을 권장합니다.
문서화를 고려해야 합니다.
"""
        result = detect_actionability_gaps(content)
        gap_sections = [s for s in result['section_analysis'] if s['has_gap']]
        self.assertGreater(len(gap_sections), 0)

    def test_suggestions_present_for_gaps(self):
        content = """## 보안
보안 강화가 필요합니다.
인증을 해야 합니다.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_empty_for_no_advice(self):
        content = '단순한 설명 텍스트입니다. 특별한 내용은 없습니다.'
        result = detect_actionability_gaps(content)
        self.assertEqual(len(result['suggestions']), 0)

    def test_step_patterns_detected(self):
        content = """## 절차
Step 1: 환경 설정. Step 2: 코드 작성. Step 3: 테스트.
"""
        result = detect_actionability_gaps(content)
        self.assertGreater(result['summary']['total_actions'], 0)

    def test_return_structure(self):
        content = '코드 품질이 중요합니다. 먼저 테스트를 작성하세요.'
        result = detect_actionability_gaps(content)
        self.assertIn('section_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_advice', result['summary'])
        self.assertIn('total_actions', result['summary'])
        self.assertIn('actionability_rate', result['summary'])
        self.assertIn('gap_sections', result['summary'])


if __name__ == '__main__':
    unittest.main()
