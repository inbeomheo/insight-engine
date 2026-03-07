"""Chapter Breakpoint Detector 서비스 테스트."""
import unittest
from services.chapter_breakpoint_service import detect_chapter_breakpoints


class TestChapterBreakpointDetector(unittest.TestCase):
    """detect_chapter_breakpoints 함수 테스트."""

    def test_empty_content(self):
        result = detect_chapter_breakpoints('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_sections'], 0)

    def test_none_content(self):
        result = detect_chapter_breakpoints(None)
        self.assertEqual(result['score'], 100.0)

    def test_short_content(self):
        content = """## 소개
짧은 소개글입니다.

## 결론
짧은 결론입니다.
"""
        result = detect_chapter_breakpoints(content)
        self.assertEqual(result['summary']['suggested_breaks'], 0)

    def test_very_long_section(self):
        long_text = '가나다라마바사 ' * 250  # 2000자+
        content = f"""## 매우 긴 섹션
{long_text}
"""
        result = detect_chapter_breakpoints(content)
        self.assertGreater(result['summary']['long_sections'], 0)
        self.assertGreater(result['summary']['suggested_breaks'], 0)

    def test_long_section_with_transitions(self):
        text_parts = ['내용입니다. ' * 50]  # 약 350자
        text_parts.append('한편 다른 관점에서 보면 중요합니다. ' * 20)
        text_parts.append('그러나 반대 의견도 있습니다. ' * 20)
        text_parts.append('또한 추가적인 관점도 있습니다. ' * 20)
        content = f"""## 복잡한 섹션
{''.join(text_parts)}
"""
        result = detect_chapter_breakpoints(content)
        self.assertGreater(result['summary']['suggested_breaks'], 0)

    def test_multiple_transitions_korean(self):
        content = """## 분석
첫 번째 관점입니다. 한편 두 번째 관점도 있습니다.
그러나 세 번째 관점은 다릅니다. 또한 네 번째도 있습니다.
""" * 5
        result = detect_chapter_breakpoints(content)
        analysis = result['section_analysis']
        has_transitions = any(a['transition_count'] > 0 for a in analysis)
        self.assertTrue(has_transitions)

    def test_multiple_transitions_english(self):
        content = """## Analysis
First point here. However there is another view.
On the other hand we must consider this. Furthermore another aspect exists.
Moving on to the next topic. Additionally we should note this.
""" * 3
        result = detect_chapter_breakpoints(content)
        analysis = result['section_analysis']
        has_transitions = any(a['transition_count'] > 0 for a in analysis)
        self.assertTrue(has_transitions)

    def test_well_structured_no_breaks(self):
        content = """## 소개
짧은 소개글입니다. 간결하게 설명합니다.

## 본론
핵심 내용을 다룹니다. 중요한 포인트입니다.

## 결론
마무리 글입니다. 요약합니다.
"""
        result = detect_chapter_breakpoints(content)
        self.assertEqual(result['summary']['suggested_breaks'], 0)
        self.assertGreaterEqual(result['score'], 80.0)

    def test_score_decreases_with_breaks(self):
        long_text = '가나다라마바사 ' * 250
        content = f"""## 섹션 1
{long_text}

## 섹션 2
{long_text}
"""
        result = detect_chapter_breakpoints(content)
        self.assertLess(result['score'], 100.0)

    def test_avg_section_length(self):
        content = """## 섹션 A
짧은 내용입니다.

## 섹션 B
또 다른 짧은 내용입니다.
"""
        result = detect_chapter_breakpoints(content)
        self.assertGreater(result['summary']['avg_section_length'], 0)

    def test_suggestions_for_long_sections(self):
        long_text = '설명 텍스트입니다. ' * 200
        content = f"""## 긴 섹션
{long_text}
"""
        result = detect_chapter_breakpoints(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_good_structure(self):
        content = """## 소개
간결한 소개.

## 결론
간결한 결론.
"""
        result = detect_chapter_breakpoints(content)
        if result['suggestions']:
            self.assertTrue(any('적절' in s or '없습니다' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = """## 테스트
테스트 내용입니다.
"""
        result = detect_chapter_breakpoints(content)
        self.assertIn('breakpoints', result)
        self.assertIn('section_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sections', result['summary'])
        self.assertIn('long_sections', result['summary'])
        self.assertIn('suggested_breaks', result['summary'])
        self.assertIn('avg_section_length', result['summary'])

    def test_section_analysis_fields(self):
        content = """## 헤딩
본문 텍스트입니다.
"""
        result = detect_chapter_breakpoints(content)
        if result['section_analysis']:
            sa = result['section_analysis'][0]
            self.assertIn('heading', sa)
            self.assertIn('level', sa)
            self.assertIn('char_count', sa)
            self.assertIn('transition_count', sa)
            self.assertIn('needs_break', sa)

    def test_no_heading_content(self):
        content = '헤딩 없는 긴 텍스트입니다. ' * 100
        result = detect_chapter_breakpoints(content)
        self.assertGreater(result['summary']['total_sections'], 0)


if __name__ == '__main__':
    unittest.main()
