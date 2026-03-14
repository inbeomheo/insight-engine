"""Community Evidence Coverage Analyzer 서비스 테스트."""
import unittest
from services.quality.community_evidence_service import analyze_community_evidence


class TestCommunityEvidence(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_community_evidence('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_community_evidence(None)
        self.assertEqual(result['score'], 50.0)

    def test_no_community_sources(self):
        content = '일반적인 기술 문서입니다. 공식 문서를 참조하세요.'
        result = analyze_community_evidence(content)
        self.assertEqual(len(result['summary']['sources_found']), 0)

    def test_reddit_source(self):
        content = 'Reddit의 r/programming 서브레딧에서 이 도구에 대한 토론이 활발합니다.'
        result = analyze_community_evidence(content)
        self.assertIn('reddit', result['summary']['sources_found'])

    def test_forum_source(self):
        content = '클리앙 커뮤니티의 게시판에서 다양한 의견을 수집했습니다.'
        result = analyze_community_evidence(content)
        self.assertIn('forum', result['summary']['sources_found'])

    def test_review_source(self):
        content = '실제 사용자 리뷰에 따르면 만족도가 높습니다. 구매 후기도 긍정적입니다.'
        result = analyze_community_evidence(content)
        self.assertIn('review', result['summary']['sources_found'])

    def test_qna_source(self):
        content = 'Stack Overflow에서 이 문제에 대한 답변을 찾았습니다. Quora에서도 유사한 질문이 있습니다.'
        result = analyze_community_evidence(content)
        self.assertIn('qna', result['summary']['sources_found'])

    def test_social_source(self):
        content = '트위터에서 많은 반응이 있었고 유튜브 댓글에서도 긍정적인 피드백을 받았습니다.'
        result = analyze_community_evidence(content)
        self.assertIn('social', result['summary']['sources_found'])

    def test_multiple_sources(self):
        content = ('Reddit r/python에서 토론이 활발합니다. '
                   'Stack Overflow에서도 관련 Q&A가 많습니다. '
                   '실제 사용자 리뷰에서도 긍정적 평가입니다. '
                   '트위터에서 큰 반향을 일으켰습니다. '
                   '사용자들에 따르면 매우 유용합니다.')
        result = analyze_community_evidence(content)
        self.assertGreater(len(result['summary']['sources_found']), 2)
        self.assertIn(result['summary']['level'], ('rich', 'good'))

    def test_community_citation(self):
        content = ('사용자들에 따르면 이 제품은 우수합니다. '
                   '실제 사용자 피드백을 바탕으로 분석했습니다.')
        result = analyze_community_evidence(content)
        self.assertGreater(result['summary']['citation_count'], 0)

    def test_community_url(self):
        content = '자세한 토론은 https://www.reddit.com/r/programming/post123 에서 확인하세요.'
        result = analyze_community_evidence(content)
        self.assertGreater(result['summary']['community_url_count'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_community_evidence(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_community_evidence(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('community_signals', result)
        self.assertIn('suggestions', result)
        self.assertIn('sources_found', result['summary'])
        self.assertIn('sources_missing', result['summary'])
        self.assertIn('citation_count', result['summary'])
        self.assertIn('coverage_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '출처 없는 일반적인 기술 문서입니다.'
        result = analyze_community_evidence(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
