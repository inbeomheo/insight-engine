"""prompts/fusion — 댓글 분석 + 다중 소스 융합 프롬프트 + 컨텍스트 빌더"""
import unittest

from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT
from prompts.fusion.fusion_prompt import FUSION_PROMPT, build_fusion_context


class TestCommentAnalyzerPrompt(unittest.TestCase):

    def test_describes_four_categories(self):
        for cat in ('insights', 'questions', 'fact_checks', 'sentiments'):
            with self.subTest(cat=cat):
                self.assertIn(cat, COMMENT_ANALYZER_PROMPT)

    def test_describes_korean_category_labels(self):
        for label in ('인사이트', '질문', '반론', '감상'):
            with self.subTest(label=label):
                self.assertIn(label, COMMENT_ANALYZER_PROMPT)

    def test_json_only_output_instruction(self):
        self.assertIn('JSON', COMMENT_ANALYZER_PROMPT)
        self.assertTrue(
            '다른 텍스트' in COMMENT_ANALYZER_PROMPT
            or 'JSON만 출력' in COMMENT_ANALYZER_PROMPT,
        )

    def test_spam_exclusion(self):
        """스팸/욕설/광고 제외 규칙"""
        for word in ('스팸', '욕설', '광고'):
            with self.subTest(word=word):
                self.assertIn(word, COMMENT_ANALYZER_PROMPT)


class TestFusionPrompt(unittest.TestCase):

    def test_describes_multi_source_fusion(self):
        # 다중 소스 키워드
        for kw in ('영상', '댓글', '외부'):
            self.assertIn(kw, FUSION_PROMPT)

    def test_inline_fact_check_format(self):
        """팩트체크 인라인 표시 형식 지시"""
        self.assertIn('팩트체크', FUSION_PROMPT)

    def test_faq_section_described(self):
        self.assertIn('FAQ', FUSION_PROMPT.upper().replace('자주 묻는 질문', 'FAQ'))

    def test_source_citation_format(self):
        """[출처: ...] 형식 명시"""
        self.assertIn('출처', FUSION_PROMPT)

    def test_no_creation_rule(self):
        """소스에 없는 정보 창작 금지"""
        self.assertIn('창작', FUSION_PROMPT)


class TestBuildFusionContext(unittest.TestCase):

    def test_videos_only(self):
        ctx = build_fusion_context(
            video_summaries=[
                {'title': '영상 A', 'summary': '요약 A'},
                {'title': '영상 B', 'summary': '요약 B'},
            ],
        )
        self.assertIn('[영상 요약]', ctx)
        self.assertIn('영상 A', ctx)
        self.assertIn('영상 B', ctx)
        self.assertIn('요약 A', ctx)
        # 댓글/외부 섹션은 없음
        self.assertNotIn('[댓글 분석]', ctx)
        self.assertNotIn('[외부 소스]', ctx)

    def test_with_comment_analysis_all_buckets(self):
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V', 'summary': 'S'}],
            comment_analysis={
                'insights': ['인사이트1'],
                'questions': ['질문1'],
                'fact_checks': ['지적1'],
                'sentiments': ['감상1'],
            },
        )
        self.assertIn('[댓글 분석]', ctx)
        for item in ('인사이트1', '질문1', '지적1', '감상1'):
            self.assertIn(item, ctx)

    def test_empty_comment_buckets_skipped(self):
        """비어있는 카테고리는 헤더가 출력되지 않음"""
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V', 'summary': 'S'}],
            comment_analysis={
                'insights': ['ins'],
                'questions': [],
                'fact_checks': [],
                'sentiments': [],
            },
        )
        # 인사이트 헤더는 있지만 다른 빈 헤더는 없음
        self.assertIn('인사이트', ctx)
        self.assertNotIn('FAQ 섹션용', ctx)
        self.assertNotIn('인라인 표시', ctx)

    def test_with_web_sources(self):
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V', 'summary': 'S'}],
            web_sources=[
                {'title': '기사 A', 'summary': '기사 요약', 'url': 'https://x.com/a'},
            ],
        )
        self.assertIn('[외부 소스]', ctx)
        self.assertIn('기사 A', ctx)
        self.assertIn('https://x.com/a', ctx)

    def test_full_combined(self):
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V', 'summary': 'S'}],
            comment_analysis={'insights': ['i'], 'questions': [], 'fact_checks': [], 'sentiments': []},
            web_sources=[{'title': 'W', 'summary': 'WS', 'url': 'https://x'}],
        )
        # 3개 섹션 모두 존재
        self.assertIn('[영상 요약]', ctx)
        self.assertIn('[댓글 분석]', ctx)
        self.assertIn('[외부 소스]', ctx)


if __name__ == '__main__':
    unittest.main()
