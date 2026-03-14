"""social_proof_service 단위 테스트"""
import unittest

from services.media.social_proof_service import (
    extract_snippets,
    _make_snippet,
    _select_best,
)


class TestExtractSnippets(unittest.TestCase):

    def test_empty_content(self):
        result = extract_snippets('')
        self.assertEqual(result['total'], 0)
        self.assertIsNone(result['best_snippet'])

    def test_none_content(self):
        result = extract_snippets(None)
        self.assertEqual(result['total'], 0)

    def test_extracts_statistics(self):
        content = '매출이 전년 대비 45% 증가했습니다. 사용자 100만명을 돌파했습니다.'
        result = extract_snippets(content)
        self.assertGreater(result['total'], 0)
        stat_snippets = [s for s in result['snippets'] if s['type'] == 'statistic']
        self.assertGreater(len(stat_snippets), 0)

    def test_extracts_quotes(self):
        content = '전문가는 "AI가 미래를 바꿀 것이다"라고 말했습니다.'
        result = extract_snippets(content)
        quote_snippets = [s for s in result['snippets'] if s['type'] == 'quote']
        self.assertGreater(len(quote_snippets), 0)

    def test_extracts_insights(self):
        content = '이 연구의 핵심 결론은 데이터 기반 의사결정이 성과를 향상시킨다는 것입니다.'
        result = extract_snippets(content)
        insight_snippets = [s for s in result['snippets'] if s['type'] == 'insight']
        self.assertGreater(len(insight_snippets), 0)

    def test_max_count(self):
        content = ('매출 10% 증가. ' * 20) + ('핵심 전략입니다. ' * 20)
        result = extract_snippets(content, max_count=5)
        self.assertLessEqual(result['total'], 5)

    def test_best_snippet_selected(self):
        content = '매출이 50% 증가했습니다. 핵심 전략은 데이터 활용입니다.'
        result = extract_snippets(content)
        if result['total'] > 0:
            self.assertIsNotNone(result['best_snippet'])
            self.assertIsInstance(result['best_snippet'], str)

    def test_snippet_structure(self):
        content = '사용자 만족도가 85%에 달합니다.'
        result = extract_snippets(content)
        for s in result['snippets']:
            self.assertIn('type', s)
            self.assertIn('text', s)
            self.assertIn('char_count', s)
            self.assertIn('social_ready', s)
            self.assertIn('suggested_platform', s)


class TestMakeSnippet(unittest.TestCase):

    def test_short_snippet_twitter(self):
        snippet = _make_snippet('짧은 스니펫', 'statistic')
        self.assertTrue(snippet['social_ready'])
        self.assertEqual(snippet['suggested_platform'], 'Twitter/X')

    def test_long_snippet(self):
        long_text = '매우 긴 콘텐츠입니다 이것은 테스트용 텍스트 ' * 50
        snippet = _make_snippet(long_text, 'insight')
        self.assertFalse(snippet['social_ready'])
        self.assertIn('Blog', snippet['suggested_platform'])

    def test_medium_snippet_linkedin(self):
        text = '이것은 중간 길이의 콘텐츠 텍스트로서 소셜 미디어에 공유하기 적합한 분량입니다. ' * 8
        snippet = _make_snippet(text, 'quote')
        self.assertIn('LinkedIn', snippet['suggested_platform'])


class TestSelectBest(unittest.TestCase):

    def test_prefers_statistic(self):
        snippets = [
            {'type': 'insight', 'text': '인사이트', 'char_count': 10, 'social_ready': True},
            {'type': 'statistic', 'text': '통계', 'char_count': 10, 'social_ready': True},
        ]
        best = _select_best(snippets)
        self.assertEqual(best, '통계')

    def test_empty_list(self):
        self.assertIsNone(_select_best([]))

    def test_prefers_social_ready(self):
        snippets = [
            {'type': 'statistic', 'text': '긴 통계' * 100, 'char_count': 500, 'social_ready': False},
            {'type': 'insight', 'text': '짧은 인사이트', 'char_count': 20, 'social_ready': True},
        ]
        best = _select_best(snippets)
        self.assertEqual(best, '짧은 인사이트')


if __name__ == '__main__':
    unittest.main()
