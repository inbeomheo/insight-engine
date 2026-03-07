"""Audience-Fit Framing Analyzer 서비스 테스트."""
import unittest
from services.audience_fit_framing_service import analyze_audience_fit_framing


class TestAudienceFitFraming(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_audience_fit_framing('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_audience_fit_framing(None)
        self.assertEqual(result['score'], 50.0)

    def test_no_framing(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 맛있는 점심을 먹었습니다.'
        result = analyze_audience_fit_framing(content)
        self.assertEqual(result['summary']['level'], 'missing')

    def test_audience_specified(self):
        content = ('이 글은 초보자를 위한 가이드입니다. '
                   '프로그래밍을 처음 시작하는 분에게 적합합니다.')
        result = analyze_audience_fit_framing(content)
        self.assertTrue(result['summary']['has_audience'])

    def test_context_specified(self):
        content = ('이 방법은 소규모 팀에서 사용하기에 적합한 경우에 유효합니다. '
                   '활용 사례를 살펴보겠습니다.')
        result = analyze_audience_fit_framing(content)
        self.assertTrue(result['summary']['has_context'])

    def test_not_for_specified(self):
        content = ('이 도구는 대규모 프로젝트에는 적합하지 않습니다. '
                   '실시간 처리가 필요한 경우에는 추천하지 않습니다.')
        result = analyze_audience_fit_framing(content)
        self.assertTrue(result['summary']['has_not_for'])

    def test_comprehensive_framing(self):
        content = ('이 글은 개발자를 대상으로 작성되었습니다. '
                   '이런 경우에 유용합니다: 빠른 프로토타이핑이 필요할 때. '
                   '대규모 엔터프라이즈에는 적합하지 않습니다.')
        result = analyze_audience_fit_framing(content)
        self.assertIn(result['summary']['level'], ('comprehensive', 'good'))

    def test_early_audience(self):
        content = ('본 가이드는 초보 개발자를 위한 가이드입니다. '
                   + '다양한 내용을 포함합니다. ' * 20)
        result = analyze_audience_fit_framing(content)
        self.assertTrue(result['summary']['audience_early'])

    def test_english_audience(self):
        content = ('This guide is for beginners who want to learn Python. '
                   'It works best when you need quick prototyping. '
                   'Not suitable for enterprise-scale applications.')
        result = analyze_audience_fit_framing(content)
        self.assertTrue(result['summary']['has_audience'])

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_audience_fit_framing(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_audience_fit_framing(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('audience_matches', result)
        self.assertIn('suggestions', result)
        self.assertIn('has_audience', result['summary'])
        self.assertIn('has_context', result['summary'])
        self.assertIn('has_not_for', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '대상 없이 작성된 문서입니다.'
        result = analyze_audience_fit_framing(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
