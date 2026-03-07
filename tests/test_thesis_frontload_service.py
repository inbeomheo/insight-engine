"""Thesis Frontload Checker 서비스 테스트."""
import unittest
from services.thesis_frontload_service import check_thesis_frontload


class TestThesisFrontloadChecker(unittest.TestCase):
    """check_thesis_frontload 함수 테스트."""

    def test_empty_content(self):
        result = check_thesis_frontload('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_thesis'], 0)
        self.assertEqual(result['thesis_sentences'], [])

    def test_none_content(self):
        result = check_thesis_frontload(None)
        self.assertEqual(result['score'], 100.0)

    def test_whitespace_content(self):
        result = check_thesis_frontload('   \n\n  ')
        self.assertEqual(result['score'], 100.0)

    def test_thesis_in_front_korean(self):
        # 핵심 주장이 첫 20%에 위치
        sentences = ['핵심은 테스트 자동화입니다.']
        padding = ['추가 설명 문장입니다.'] * 10
        content = ' '.join(sentences + padding)
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['total_thesis'], 0)
        self.assertGreater(result['position_analysis']['frontloaded'], 0)
        self.assertGreaterEqual(result['score'], 50.0)

    def test_thesis_in_back_korean(self):
        # 핵심 주장이 뒷부분에 위치
        padding = ['추가 설명 문장입니다.'] * 10
        thesis = ['결론적으로 테스트가 필수입니다.']
        content = ' '.join(padding + thesis)
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['total_thesis'], 0)
        self.assertGreater(result['position_analysis']['back_loaded'], 0)

    def test_thesis_in_front_english(self):
        sentences = ['The key takeaway is automation matters.']
        padding = ['This is additional explanation.'] * 10
        content = ' '.join(sentences + padding)
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['total_thesis'], 0)
        self.assertGreater(result['position_analysis']['frontloaded'], 0)

    def test_thesis_in_back_english(self):
        padding = ['This is additional explanation.'] * 10
        thesis = ['In conclusion testing is essential.']
        content = ' '.join(padding + thesis)
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['total_thesis'], 0)
        self.assertGreater(result['position_analysis']['back_loaded'], 0)

    def test_no_thesis_detected(self):
        content = '오늘 날씨가 좋습니다. 산책을 다녀왔습니다. 공원이 아름다웠습니다.'
        result = check_thesis_frontload(content)
        self.assertEqual(result['summary']['total_thesis'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_multiple_thesis_signals(self):
        content = """핵심은 품질 관리입니다.
이 글의 결론적으로 테스트가 중요합니다.
추가 설명이 이어집니다.
더 많은 설명이 있습니다.
또 다른 설명입니다.
계속 이어지는 문장입니다.
가장 중요한 것은 자동화입니다.
"""
        result = check_thesis_frontload(content)
        self.assertGreaterEqual(result['summary']['total_thesis'], 2)

    def test_tl_dr_detection(self):
        content = """TL;DR: 자동화가 핵심입니다.
이 글에서는 자동화를 다룹니다.
추가 내용이 있습니다.
더 많은 내용이 있습니다.
계속 이어집니다.
"""
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['total_thesis'], 0)

    def test_frontload_rate_calculation(self):
        # 모든 주장이 앞에 있으면 100%
        content = """핵심은 자동화입니다.
요약하면 효율성이 중요합니다.
추가 설명 문장입니다.
더 많은 설명 문장입니다.
또 다른 설명 문장입니다.
이어지는 설명입니다.
계속되는 내용입니다.
마무리 문장입니다.
최종 문장입니다.
끝 문장입니다.
"""
        result = check_thesis_frontload(content)
        self.assertGreater(result['summary']['frontload_rate'], 0)

    def test_suggestions_for_back_loaded(self):
        padding = ['추가 설명 문장입니다.'] * 10
        thesis = ['결론적으로 테스트가 필수입니다.']
        content = ' '.join(padding + thesis)
        result = check_thesis_frontload(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_for_no_thesis(self):
        content = '단순한 설명입니다. 특별한 주장은 없습니다. 평범한 내용입니다.'
        result = check_thesis_frontload(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '핵심은 테스트입니다. 추가 설명이 있습니다.'
        result = check_thesis_frontload(content)
        self.assertIn('thesis_sentences', result)
        self.assertIn('position_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('frontloaded', result['position_analysis'])
        self.assertIn('mid_section', result['position_analysis'])
        self.assertIn('back_loaded', result['position_analysis'])
        self.assertIn('total_thesis', result['summary'])
        self.assertIn('frontload_rate', result['summary'])

    def test_thesis_sentence_truncation(self):
        # 150자 초과 문장은 잘림
        long_text = '핵심은 ' + '가' * 200 + '입니다.'
        padding = ['추가 설명입니다.'] * 5
        content = long_text + ' ' + ' '.join(padding)
        result = check_thesis_frontload(content)
        if result['thesis_sentences']:
            self.assertLessEqual(len(result['thesis_sentences'][0]['text']), 150)


if __name__ == '__main__':
    unittest.main()
