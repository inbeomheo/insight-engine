"""퓨전 프롬프트 모듈 테스트"""
import unittest


class TestCommentAnalyzerPrompt(unittest.TestCase):

    def test_comment_analyzer_prompt_exists(self):
        from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT
        self.assertIsInstance(COMMENT_ANALYZER_PROMPT, str)
        self.assertIn('인사이트', COMMENT_ANALYZER_PROMPT)
        self.assertIn('질문', COMMENT_ANALYZER_PROMPT)
        self.assertIn('반론', COMMENT_ANALYZER_PROMPT)

    def test_comment_analyzer_prompt_has_output_format(self):
        from prompts.fusion.comment_analyzer import COMMENT_ANALYZER_PROMPT
        self.assertIn('JSON', COMMENT_ANALYZER_PROMPT)


class TestFusionPrompt(unittest.TestCase):

    def test_fusion_prompt_exists(self):
        from prompts.fusion.fusion_prompt import FUSION_PROMPT
        self.assertIsInstance(FUSION_PROMPT, str)
        self.assertIn('융합', FUSION_PROMPT)

    def test_build_fusion_context(self):
        from prompts.fusion.fusion_prompt import build_fusion_context
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V1', 'summary': 'S1'}],
            comment_analysis={'insights': ['I1'], 'questions': ['Q1'],
                              'fact_checks': [], 'sentiments': []},
            web_sources=[{'title': 'W1', 'summary': 'WS1', 'url': 'http://ex.com'}]
        )
        self.assertIn('V1', ctx)
        self.assertIn('I1', ctx)
        self.assertIn('W1', ctx)

    def test_build_fusion_context_empty_optional(self):
        from prompts.fusion.fusion_prompt import build_fusion_context
        ctx = build_fusion_context(
            video_summaries=[{'title': 'V1', 'summary': 'S1'}],
            comment_analysis=None,
            web_sources=None
        )
        self.assertIn('V1', ctx)
        self.assertNotIn('[댓글 분석]', ctx)


if __name__ == '__main__':
    unittest.main()
