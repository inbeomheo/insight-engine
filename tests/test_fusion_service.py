"""퓨전 오케스트레이터 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestFusionService(unittest.TestCase):

    @patch('services.core.fusion_service.ai_service')
    @patch('services.core.fusion_service.web_research_service')
    @patch('services.core.fusion_service.content_service')
    def test_generate_fusion_full(self, mock_cs, mock_wr, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = ['댓글1', '댓글2']

        mock_ai.create_content.return_value = {
            'title': '퓨전 제목',
            'content': '# 퓨전 본문\n내용',
            'html': '<h1>퓨전 본문</h1>',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300}
        }
        mock_wr.research_topic.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com', 'summary': '요약1'}
        ]

        from services.core.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={'length': 'long'},
            enable_web_research=True,
            enable_deep_comments=True
        )
        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('fusion_meta', result)
        self.assertIn('videos_analyzed', result['fusion_meta'])

    @patch('services.core.fusion_service.ai_service')
    @patch('services.core.fusion_service.content_service')
    def test_generate_fusion_without_optional(self, mock_cs, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = []
        mock_ai.create_content.return_value = {
            'title': '제목', 'content': '내용', 'html': '<p>내용</p>',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
        }

        from services.core.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={},
            enable_web_research=False,
            enable_deep_comments=False
        )
        self.assertIn('title', result)

    def test_generate_fusion_too_few_urls(self):
        from services.core.fusion_service import generate_fusion
        with self.assertRaises(ValueError):
            generate_fusion(
                urls=['https://youtube.com/watch?v=vid1'],
                style_id='blog_seo', model='m', modifiers={},
                enable_web_research=False, enable_deep_comments=False
            )

    def test_comment_analysis_content_fallback_in_context(self):
        from prompts.fusion.fusion_prompt import build_fusion_context

        context = build_fusion_context(
            video_summaries=[{'title': '영상1', 'summary': '요약1'}],
            comment_analysis={
                'content': '댓글에서 반복 질문과 반박이 많음',
                'insights': [],
                'questions': [],
                'fact_checks': [],
                'sentiments': [],
            },
            web_sources=None,
        )

        self.assertIn('종합 댓글 분석', context)
        self.assertIn('댓글에서 반복 질문과 반박이 많음', context)


if __name__ == '__main__':
    unittest.main()
